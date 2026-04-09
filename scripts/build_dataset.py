"""
build_dataset.py

Smart dataset builder. Generates synthetic FHIR R4 patient data using Synthea
in batches, extracts ground truth after each batch, and keeps running until
exactly 200 usable patients are confirmed in data/ground_truth/.

A patient is considered usable if:
  - active_medication_count >= 1        (something to evaluate recall against)
  - 10 <= history_span_years <= 30      (10-30 year medication histories per study design)

Patients that do not meet these criteria are moved to data/discarded/ so the
main data directories contain only usable patients. The discarded files are
kept rather than deleted in case they are needed for inspection later.

On first run this script also scans the existing data/ground_truth/ and
data/raw/ directories and moves any already-unusable files to discarded/
before starting new generation.

Usage:
    python scripts/build_dataset.py

Requirements:
    - Java 11 or higher installed and on PATH
    - Synthea jar downloaded (run scripts/setup_synthea.sh first)
    - src/ground_truth.py present (used as a module internally)

Output:
    data/raw/               usable FHIR bundles only
    data/ground_truth/      usable ground truth JSONs only
    data/discarded/raw/     discarded FHIR bundles
    data/discarded/ground_truth/   discarded ground truth JSONs
    logs/build_dataset.log  full run log
"""

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JAR_PATH = REPO_ROOT / "synthea" / "synthea-with-dependencies.jar"

RAW_DIR = REPO_ROOT / "data" / "raw"
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"
DISCARDED_RAW_DIR = REPO_ROOT / "data" / "discarded" / "raw"
DISCARDED_GT_DIR = REPO_ROOT / "data" / "discarded" / "ground_truth"
SYNTHEA_OUTPUT_DIR = REPO_ROOT / "synthea" / "output" / "fhir"
LOG_DIR = REPO_ROOT / "logs"
LOG_FILE = LOG_DIR / "build_dataset.log"

TARGET_USABLE = 200
BATCH_SIZE = 60

# Discard criteria
MIN_ACTIVE_MEDS = 1
MIN_HISTORY_YEARS = 10
MAX_HISTORY_YEARS = 30

# Age-range batches spanning 40-75 to cover the target population.
# The -m module filter flag is not used: in this version of Synthea it matches
# 0 modules (the actual filenames differ from the condition names), causing
# Synthea to run with 0 disease modules and produce patients with no medications.
# Age-range targeting achieves diverse profiles without breaking module loading.
# The script cycles through these batches repeatedly until TARGET_USABLE is met.
BATCHES = [
    {"age_range": "40-55", "label": "early middle-age (40-55)"},
    {"age_range": "50-65", "label": "mid middle-age (50-65)"},
    {"age_range": "55-70", "label": "late middle-age to early elderly (55-70)"},
    {"age_range": "60-75", "label": "early elderly (60-75)"},
    {"age_range": "45-65", "label": "broad middle-age (45-65)"},
]


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("build_dataset")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s  %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def ensure_dirs():
    for d in [RAW_DIR, GROUND_TRUTH_DIR, DISCARDED_RAW_DIR, DISCARDED_GT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def is_patient_bundle(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            bundle = json.load(f)
        return any(
            e.get("resource", {}).get("resourceType") == "Patient"
            for e in bundle.get("entry", [])
        )
    except Exception:
        return False


def is_usable(ground_truth):
    active = ground_truth.get("active_medication_count", 0)
    span = ground_truth.get("history_span_years")
    return (
        active >= MIN_ACTIVE_MEDS
        and span is not None
        and MIN_HISTORY_YEARS <= span <= MAX_HISTORY_YEARS
    )


def discard_patient(patient_id, logger, reason):
    """
    Move a patient's raw bundle and ground truth file to the discarded directories.
    Matches by patient_id embedded in the ground truth filename since raw bundle
    filenames contain the same UUID.
    """
    gt_file = GROUND_TRUTH_DIR / f"{patient_id}.json"
    if gt_file.exists():
        shutil.move(str(gt_file), DISCARDED_GT_DIR / gt_file.name)

    raw_matches = list(RAW_DIR.glob(f"*{patient_id}*.json"))
    for raw_file in raw_matches:
        shutil.move(str(raw_file), DISCARDED_RAW_DIR / raw_file.name)

    logger.debug(f"Discarded {patient_id}: {reason}")


def audit_existing_data(logger):
    """
    Scan existing data/ground_truth/ files and move any that fail the usability
    criteria to discarded/. This runs once at the start of the script so the
    main directories are clean before new generation begins.
    """
    gt_files = list(GROUND_TRUTH_DIR.glob("*.json"))
    if not gt_files:
        logger.info("No existing ground truth files found. Starting fresh.")
        return 0

    logger.info(f"Auditing {len(gt_files)} existing ground truth file(s)...")

    usable_count = 0
    discarded_count = 0

    for f in gt_files:
        try:
            gt = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Could not read {f.name}: {e}. Moving to discarded.")
            shutil.move(str(f), DISCARDED_GT_DIR / f.name)
            discarded_count += 1
            continue

        if is_usable(gt):
            usable_count += 1
        else:
            active = gt.get("active_medication_count", 0)
            span = gt.get("history_span_years")
            reasons = []
            if active < MIN_ACTIVE_MEDS:
                reasons.append(f"active={active} (min {MIN_ACTIVE_MEDS})")
            if span is None or span < MIN_HISTORY_YEARS:
                reasons.append(f"history={span}yr (min {MIN_HISTORY_YEARS}yr)")
            elif span > MAX_HISTORY_YEARS:
                reasons.append(f"history={span}yr (max {MAX_HISTORY_YEARS}yr)")
            reason = ", ".join(reasons) if reasons else "unknown"

            discard_patient(gt["patient_id"], logger, reason)
            discarded_count += 1

    logger.info(
        f"Audit complete. Usable: {usable_count}  Discarded: {discarded_count}"
    )
    return usable_count


def count_usable():
    """
    Count currently usable patients by reading data/ground_truth/.
    """
    count = 0
    for f in GROUND_TRUTH_DIR.glob("*.json"):
        try:
            gt = json.loads(f.read_text(encoding="utf-8"))
            if is_usable(gt):
                count += 1
        except Exception:
            pass
    return count


def run_synthea(batch, count, logger):
    age_range = batch["age_range"]
    label = batch["label"]

    logger.info(f"Generating {count} patient(s): {label} (age {age_range})")

    cmd = [
        "java", "-jar", str(JAR_PATH),
        "-p", str(count),
        "-a", age_range,
        "--exporter.fhir.export=true",
        "--exporter.years_of_history=30",
        f"--exporter.baseDirectory={REPO_ROOT / 'synthea' / 'output'}",
        "Massachusetts",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Synthea failed: {result.stderr}")
        return False

    return True


def collect_new_bundles(logger):
    """
    Copy patient bundles from Synthea output to data/raw/, skipping any
    that are already present. Returns the list of newly copied file paths.
    """
    if not SYNTHEA_OUTPUT_DIR.exists():
        return []

    all_files = list(SYNTHEA_OUTPUT_DIR.glob("*.json"))
    patient_files = [f for f in all_files if is_patient_bundle(f)]
    skipped_meta = len(all_files) - len(patient_files)

    newly_copied = []
    for f in patient_files:
        already_in_raw = (RAW_DIR / f.name).exists()
        already_discarded = (DISCARDED_RAW_DIR / f.name).exists()
        if not already_in_raw and not already_discarded:
            shutil.copy(f, RAW_DIR / f.name)
            newly_copied.append(RAW_DIR / f.name)

    logger.info(
        f"Collected {len(newly_copied)} new bundle(s). "
        f"Skipped {skipped_meta} metadata file(s)."
    )
    return newly_copied


def extract_ground_truth_for_files(new_files, logger, slots_remaining):
    """
    Run ground truth extraction on a list of newly copied raw bundle files.
    Imports and calls the extraction logic from src/ground_truth.py directly.
    Accepts at most slots_remaining usable patients to prevent overshoot.
    Returns the number of usable patients extracted from this batch.
    """
    sys.path.insert(0, str(REPO_ROOT / "src"))
    import ground_truth as gt_module

    gt_logger = logging.getLogger("ground_truth")
    if not gt_logger.handlers:
        gt_logger.setLevel(logging.WARNING)
        gt_logger.addHandler(logging.NullHandler())

    batch_usable = 0
    batch_discarded = 0

    for filepath in new_files:
        ground_truth = gt_module.process_patient(filepath, gt_logger)
        if ground_truth is None:
            logger.warning(f"Extraction failed for {filepath.name}, skipping.")
            continue

        if is_usable(ground_truth) and batch_usable < slots_remaining:
            gt_module.write_ground_truth(ground_truth, gt_logger)
            batch_usable += 1
            logger.debug(
                f"Usable: {ground_truth['patient_name']} "
                f"active={ground_truth['active_medication_count']} "
                f"history={ground_truth['history_span_years']}yr"
            )
        else:
            if is_usable(ground_truth):
                reason = "target already reached"
            else:
                active = ground_truth["active_medication_count"]
                span = ground_truth.get("history_span_years")
                reasons = []
                if active < MIN_ACTIVE_MEDS:
                    reasons.append(f"active={active}")
                if span is None or span < MIN_HISTORY_YEARS:
                    reasons.append(f"history={span}yr (min {MIN_HISTORY_YEARS}yr)")
                elif span > MAX_HISTORY_YEARS:
                    reasons.append(f"history={span}yr (max {MAX_HISTORY_YEARS}yr)")
                reason = ", ".join(reasons) if reasons else "unknown"

            raw_match = list(RAW_DIR.glob(f"*{ground_truth['patient_id']}*.json"))
            for raw_file in raw_match:
                shutil.move(str(raw_file), DISCARDED_RAW_DIR / raw_file.name)

            logger.debug(f"Discarded: {ground_truth['patient_name']} ({reason})")
            batch_discarded += 1

    return batch_usable, batch_discarded


def check_java():
    result = subprocess.run(["java", "-version"], capture_output=True)
    if result.returncode != 0:
        print("Java is not installed or not on PATH.")
        sys.exit(1)


def check_jar():
    if not JAR_PATH.exists():
        print(f"Synthea jar not found at {JAR_PATH}")
        print("Run scripts/setup_synthea.sh first.")
        sys.exit(1)


def print_final_summary(logger, total_generated, total_discarded, rounds):
    usable = count_usable()
    logger.info("")
    logger.info("BUILD COMPLETE")
    logger.info(f"Rounds of generation:        {rounds}")
    logger.info(f"Total patients generated:    {total_generated}")
    logger.info(f"Total discarded:             {total_discarded}")
    logger.info(f"Usable patients confirmed:   {usable}")
    logger.info(f"Target was:                  {TARGET_USABLE}")
    logger.info(f"Usable data in:              data/raw/ and data/ground_truth/")
    logger.info(f"Discarded data in:           data/discarded/")
    logger.info(f"Full log:                    {LOG_FILE}")


def main():
    logger = setup_logging()
    ensure_dirs()

    check_java()
    check_jar()

    logger.info("Dataset builder starting.")
    logger.info(f"Target: {TARGET_USABLE} usable patients")
    logger.info(f"Usability criteria: active_meds >= {MIN_ACTIVE_MEDS}, history {MIN_HISTORY_YEARS}-{MAX_HISTORY_YEARS} years")
    logger.info("")

    # Step 1 - audit and clean existing data
    current_usable = audit_existing_data(logger)
    logger.info(f"Starting usable count: {current_usable} / {TARGET_USABLE}")
    logger.info("")

    if current_usable >= TARGET_USABLE:
        logger.info("Target already met. No generation needed.")
        print_final_summary(logger, 0, 0, 0)
        return

    total_generated = 0
    total_discarded = 0
    rounds = 0
    batch_index = 0

    while current_usable < TARGET_USABLE:
        still_needed = TARGET_USABLE - current_usable
        rounds += 1
        batch = BATCHES[batch_index % len(BATCHES)]
        batch_index += 1

        generate_count = min(BATCH_SIZE, int(still_needed * 1.6) + 10)

        logger.info(
            f"Round {rounds}: need {still_needed} more, "
            f"generating {generate_count} patients."
        )

        success = run_synthea(batch, generate_count, logger)
        if not success:
            logger.error("Synthea failed. Aborting.")
            sys.exit(1)

        new_files = collect_new_bundles(logger)
        total_generated += len(new_files)

        # Clear Synthea output directory so it does not accumulate across rounds.
        if SYNTHEA_OUTPUT_DIR.exists():
            shutil.rmtree(SYNTHEA_OUTPUT_DIR)
            SYNTHEA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug("Cleared Synthea output directory for next round.")

        if not new_files:
            logger.warning("No new files collected this round. Continuing.")
            continue

        batch_usable, batch_discarded = extract_ground_truth_for_files(new_files, logger, still_needed)
        total_discarded += batch_discarded
        current_usable += batch_usable

        logger.info(
            f"Round {rounds} done. "
            f"Batch usable: {batch_usable}  Batch discarded: {batch_discarded}  "
            f"Total usable: {current_usable} / {TARGET_USABLE}"
        )
        logger.info("")

    print_final_summary(logger, total_generated, total_discarded, rounds)

if __name__ == "__main__":
    main()