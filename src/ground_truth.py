"""
ground_truth.py

Extracts the ground truth medication list from each Synthea FHIR R4 patient bundle
in data/raw/ and writes one structured JSON file per patient to data/ground_truth/.

What counts as ground truth:
    Only MedicationRequest resources with status == "active" are included.
    Completed, stopped, cancelled, and entered-in-error resources are excluded.
    This mirrors what a clinician would expect to see on a current medication list.

What is extracted per medication:
    - medication_name      : human-readable name from medicationCodeableConcept.text
    - rxnorm_code          : RxNorm code from medicationCodeableConcept.coding
    - authored_on          : date the prescription was written (ISO 8601)
    - dosage_text          : free-text dosage instruction if present, else null
    - frequency            : structured frequency (e.g. "4 times per day") if present, else null
    - dose_quantity        : structured dose value and unit if present, else null
    - has_structured_dosage: boolean, False means dosage is missing from the source data

What is recorded per patient:
    - patient_id           : FHIR Patient resource id (UUID)
    - patient_name         : given + family name
    - birth_date           : from Patient resource
    - gender               : from Patient resource
    - history_span_years   : years between earliest and latest MedicationRequest
    - total_medication_requests : all MedicationRequest resources regardless of status
    - active_medication_count   : count of active medications only
    - medications          : list of active medication records (see above)
    - warnings             : list of any non-fatal issues found during extraction

Output:
    data/ground_truth/<patient_id>.json    one file per patient

Logs:
    logs/ground_truth.log    full run log with per-patient detail and summary

Usage:
    python src/ground_truth.py

    Run from the repo root. Requires data/raw/ to be populated.
    Run scripts/generate_dataset.py first if data/raw/ is empty.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"
LOG_DIR = REPO_ROOT / "logs"
LOG_FILE = LOG_DIR / "ground_truth.log"

from fhir_utils import RXNORM_SYSTEM, build_medication_index, enrich_med_requests

ACTIVE_STATUSES = {"active"}
ALL_STATUSES = {"active", "completed", "cancelled", "stopped", "entered-in-error", "on-hold", "draft", "unknown"}


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ground_truth")
    logger.setLevel(logging.DEBUG)

    # File handler - full detail
    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

    # Console handler - info and above only
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s  %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def load_bundle(filepath, logger):
    """
    Load and parse a FHIR bundle JSON file.
    Returns the parsed dict or None if the file cannot be parsed.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            bundle = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in {filepath.name}: {e}")
        return None
    except OSError as e:
        logger.error(f"Cannot read {filepath.name}: {e}")
        return None

    if bundle.get("resourceType") != "Bundle":
        logger.error(f"{filepath.name} is not a FHIR Bundle (resourceType={bundle.get('resourceType')})")
        return None

    return bundle


def get_resources(bundle, resource_type):
    """
    Extract all resources of a given resourceType from a FHIR Bundle.
    """
    return [
        entry["resource"]
        for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == resource_type
    ]


def extract_patient_demographics(bundle, logger, filename):
    """
    Extract basic patient demographics from the Patient resource.
    Synthea always includes exactly one Patient resource per bundle.
    Returns a dict of demographics or None if the Patient resource is missing.
    """
    patients = get_resources(bundle, "Patient")

    if not patients:
        logger.error(f"{filename}: no Patient resource found in bundle.")
        return None

    if len(patients) > 1:
        logger.warning(f"{filename}: {len(patients)} Patient resources found, using first one.")

    patient = patients[0]

    patient_id = patient.get("id", "unknown")

    # Name: Synthea always populates name[0].given[0] and name[0].family
    name_entry = patient.get("name", [{}])[0]
    given = name_entry.get("given", ["unknown"])[0]
    family = name_entry.get("family", "unknown")
    patient_name = f"{given} {family}"

    birth_date = patient.get("birthDate", None)
    gender = patient.get("gender", None)

    return {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "birth_date": birth_date,
        "gender": gender,
    }


def extract_rxnorm_code(medication_concept, logger, med_name, patient_id):
    """
    Extract the RxNorm code from medicationCodeableConcept.coding.
    Synthea always uses RxNorm for medication coding. If for any reason it is
    absent, we log a warning and return None rather than failing.
    """
    codings = medication_concept.get("coding", [])
    for coding in codings:
        if coding.get("system") == RXNORM_SYSTEM:
            return coding.get("code")

    # No RxNorm found, check if any coding exists at all
    if codings:
        fallback = codings[0]
        logger.warning(
            f"Patient {patient_id}: medication '{med_name}' has no RxNorm code. "
            f"Found system={fallback.get('system')} code={fallback.get('code')} instead."
        )
        return fallback.get("code")

    logger.warning(f"Patient {patient_id}: medication '{med_name}' has no coding at all.")
    return None


def parse_dosage_instruction(dosage_instructions, logger, med_name, patient_id):
    """
    Parse dosageInstruction from a MedicationRequest.

    Synthea populates dosageInstruction inconsistently:
    - Some medications have full structured dosage (timing + doseAndRate)
    - Some have only free text
    - Some (particularly long-standing active medications) have no dosageInstruction at all

    This is not an error. We record what is present and flag what is missing.
    Returns a dict with dosage_text, frequency, dose_quantity, has_structured_dosage.
    """
    if not dosage_instructions:
        return {
            "dosage_text": None,
            "frequency": None,
            "dose_quantity": None,
            "has_structured_dosage": False,
        }

    # Use the first dosage instruction (Synthea rarely has more than one)
    dosage = dosage_instructions[0]

    dosage_text = dosage.get("text", None)

    # Parse timing / frequency
    frequency = None
    timing = dosage.get("timing", {})
    repeat = timing.get("repeat", {})
    if repeat:
        freq = repeat.get("frequency")
        period = repeat.get("period")
        period_unit = repeat.get("periodUnit")
        if freq is not None and period is not None and period_unit is not None:
            unit_labels = {
                "s": "second", "min": "minute", "h": "hour",
                "d": "day", "wk": "week", "mo": "month", "a": "year"
            }
            unit_label = unit_labels.get(period_unit, period_unit)
            period_str = f"{int(period)} {unit_label}" if period == int(period) else f"{period} {unit_label}"
            frequency = f"{freq} time(s) per {period_str}"

    # Parse dose quantity
    dose_quantity = None
    dose_and_rate = dosage.get("doseAndRate", [])
    if dose_and_rate:
        dq = dose_and_rate[0].get("doseQuantity", {})
        if dq:
            value = dq.get("value")
            unit = dq.get("unit")
            if value is not None:
                dose_quantity = {"value": value, "unit": unit}

    has_structured = (frequency is not None) or (dose_quantity is not None)

    if not has_structured:
        logger.debug(
            f"Patient {patient_id}: '{med_name}' has dosageInstruction but no structured "
            f"timing or doseQuantity. Only free text available: '{dosage_text}'"
        )

    return {
        "dosage_text": dosage_text,
        "frequency": frequency,
        "dose_quantity": dose_quantity,
        "has_structured_dosage": has_structured,
    }


def extract_medications(bundle, patient_id, logger, filename):
    """
    Extract all MedicationRequest resources and return two things:
    - active_medications: list of dicts for active medications only (ground truth)
    - status_summary: count of all statuses seen across all MedicationRequests

    Only MedicationRequest resources with status == "active" go into the ground truth.
    All other statuses are counted for the summary log but not included in output.
    """
    all_med_requests = enrich_med_requests(
        get_resources(bundle, "MedicationRequest"),
        build_medication_index(bundle),
    )

    if not all_med_requests:
        logger.warning(f"{filename}: no MedicationRequest resources found. Patient may have no medication history.")
        return [], {}, []

    # Count all statuses for the log
    status_summary = {}
    for mr in all_med_requests:
        status = mr.get("status", "missing")
        status_summary[status] = status_summary.get(status, 0) + 1

        if status not in ALL_STATUSES and status != "missing":
            logger.warning(f"{filename}: unexpected MedicationRequest status '{status}' on resource {mr.get('id')}.")

    # Extract active medications only
    active_medications = []
    warnings = []

    for mr in all_med_requests:
        if mr.get("status") != "active":
            continue

        med_concept = mr.get("medicationCodeableConcept")
        if not med_concept:
            msg = f"Active MedicationRequest {mr.get('id')} has no resolvable medication concept (neither medicationCodeableConcept nor a resolvable medicationReference). Skipping."
            logger.warning(f"{filename}: {msg}")
            warnings.append(msg)
            continue

        med_name = med_concept.get("text") or med_concept.get("coding", [{}])[0].get("display", "unknown")
        rxnorm_code = extract_rxnorm_code(med_concept, logger, med_name, patient_id)
        authored_on = mr.get("authoredOn")
        dosage = parse_dosage_instruction(mr.get("dosageInstruction", []), logger, med_name, patient_id)

        if not dosage["has_structured_dosage"]:
            msg = f"'{med_name}' has no structured dosage in source data (dose accuracy evaluation will mark as unknown)."
            logger.debug(f"Patient {patient_id}: {msg}")
            warnings.append(msg)

        active_medications.append({
            "medication_name": med_name,
            "rxnorm_code": rxnorm_code,
            "authored_on": authored_on,
            "dosage_text": dosage["dosage_text"],
            "frequency": dosage["frequency"],
            "dose_quantity": dosage["dose_quantity"],
            "has_structured_dosage": dosage["has_structured_dosage"],
        })

    return active_medications, status_summary, warnings


def compute_history_span(bundle):
    """
    Compute the span in years between the earliest and latest MedicationRequest.
    Returns None if there are fewer than two dated records.
    """
    all_med_requests = get_resources(bundle, "MedicationRequest")
    dates = []
    for mr in all_med_requests:
        authored = mr.get("authoredOn")
        if authored:
            try:
                dates.append(authored[:10])  # take YYYY-MM-DD portion only
            except Exception:
                pass

    if len(dates) < 2:
        return None

    dates.sort()
    earliest = int(dates[0][:4])
    latest = int(dates[-1][:4])
    return latest - earliest


def process_patient(filepath, logger):
    """
    Full extraction pipeline for a single patient bundle.
    Returns the ground truth dict to be written to file, or None on failure.
    """
    filename = filepath.name
    logger.debug(f"Processing {filename}")

    bundle = load_bundle(filepath, logger)
    if bundle is None:
        return None

    demographics = extract_patient_demographics(bundle, logger, filename)
    if demographics is None:
        return None

    patient_id = demographics["patient_id"]

    result = extract_medications(bundle, patient_id, logger, filename)
    if len(result) == 3:
        active_medications, status_summary, warnings = result
    else:
        logger.error(f"{filename}: unexpected return from extract_medications.")
        return None

    history_span = compute_history_span(bundle)
    total_requests = sum(status_summary.values())

    ground_truth = {
        "patient_id": patient_id,
        "patient_name": demographics["patient_name"],
        "birth_date": demographics["birth_date"],
        "gender": demographics["gender"],
        "history_span_years": history_span,
        "total_medication_requests": total_requests,
        "status_summary": status_summary,
        "active_medication_count": len(active_medications),
        "medications": active_medications,
        "warnings": warnings,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_file": filename,
    }

    logger.info(
        f"{demographics['patient_name']:<35} "
        f"total_requests={total_requests:<4} "
        f"active={len(active_medications):<3} "
        f"history={str(history_span) + 'yr' if history_span else 'n/a':<6} "
        f"warnings={len(warnings)}"
    )

    return ground_truth


def write_ground_truth(ground_truth, logger):
    """
    Write the ground truth dict for a patient to data/ground_truth/<patient_id>.json.
    """
    patient_id = ground_truth["patient_id"]
    out_path = GROUND_TRUTH_DIR / f"{patient_id}.json"

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Failed to write ground truth for {patient_id}: {e}")
        return False

    logger.debug(f"Written: {out_path.name}")
    return True


def run_summary(results, logger, total_files):
    """
    Print and log a summary of the full extraction run.
    """
    successes = [r for r in results if r is not None]
    failures = total_files - len(successes)

    if not successes:
        logger.error("No patients were successfully processed. Check logs above.")
        return

    total_active = sum(r["active_medication_count"] for r in successes)
    total_requests = sum(r["total_medication_requests"] for r in successes)
    patients_with_warnings = sum(1 for r in successes if r["warnings"])
    patients_no_dosage = sum(
        1 for r in successes
        if any(not m["has_structured_dosage"] for m in r["medications"])
    )
    history_spans = [r["history_span_years"] for r in successes if r["history_span_years"] is not None]
    active_counts = [r["active_medication_count"] for r in successes]

    logger.info("")
    logger.info("EXTRACTION SUMMARY")
    logger.info(f"Patient files found:              {total_files}")
    logger.info(f"Successfully processed:           {len(successes)}")
    logger.info(f"Failed:                           {failures}")
    logger.info(f"")
    logger.info(f"Total MedicationRequest resources: {total_requests}")
    logger.info(f"Total active medications:          {total_active}")
    logger.info(f"Avg active meds per patient:       {total_active / len(successes):.1f}")
    logger.info(f"Min active meds (any patient):     {min(active_counts)}")
    logger.info(f"Max active meds (any patient):     {max(active_counts)}")
    logger.info(f"")
    if history_spans:
        logger.info(f"Avg history span:                  {sum(history_spans)/len(history_spans):.1f} years")
        logger.info(f"Min history span:                  {min(history_spans)} years")
        logger.info(f"Max history span:                  {max(history_spans)} years")
    logger.info(f"")
    logger.info(f"Patients with any warning:         {patients_with_warnings}")
    logger.info(f"Patients with missing dosage:      {patients_no_dosage}")
    logger.info(f"  (these will have dose_accuracy marked as unknown in evaluation)")
    logger.info(f"Ground truth files written to: {GROUND_TRUTH_DIR}")
    logger.info(f"Full log written to:           {LOG_FILE}")


def main():
    logger = setup_logging()

    logger.info("Ground truth extraction starting.")
    logger.info(f"Reading patient bundles from: {RAW_DIR}")
    logger.info(f"Writing ground truth to:      {GROUND_TRUTH_DIR}")
    logger.info("")

    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.json")):
        logger.error(f"No JSON files found in {RAW_DIR}.")
        logger.error("Run scripts/generate_dataset.py first.")
        sys.exit(1)

    patient_files = sorted(RAW_DIR.glob("*.json"))
    logger.info(f"Found {len(patient_files)} patient file(s). Starting extraction...")
    logger.info("")
    logger.info(
        f"{'Patient':<35} {'total_req':<12} {'active':<8} {'history':<9} warnings"
    )
    logger.info("-" * 70)

    results = []
    for filepath in patient_files:
        ground_truth = process_patient(filepath, logger)
        results.append(ground_truth)
        if ground_truth is not None:
            write_ground_truth(ground_truth, logger)

    logger.info("")
    run_summary([r for r in results if r is not None], logger, len(patient_files))


if __name__ == "__main__":
    main()