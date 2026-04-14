"""
serialisers.py

Four serialisation strategies that convert a FHIR R4 patient bundle into a
formatted string for input to a language model.

Each function is independent and can be called directly:

    import json
    from src.serialisers import serialise_b

    bundle = json.loads(open("data/raw/some_patient.json").read())
    print(serialise_b(bundle))

Strategies:
    A  MedicationRequest resources as clean JSON (raw FHIR, no transformation)
    B  Flat markdown table (all statuses, one row per MedicationRequest)
    C  Clinical narrative (active medications first, then history)
    D  Chronological timeline (oldest to newest, all statuses interleaved)

All four strategies include a patient header and expose all MedicationRequest
statuses. The model must determine which medications are currently active.
"""

import json
from datetime import datetime
from typing import Optional

from fhir_utils import RXNORM_SYSTEM, build_medication_index, enrich_med_requests


# Shared helpers

def _get_resources(bundle: dict, resource_type: str) -> list:
    return [
        e["resource"]
        for e in bundle.get("entry", [])
        if e.get("resource", {}).get("resourceType") == resource_type
    ]


def _patient_header(bundle: dict) -> str:
    patients = _get_resources(bundle, "Patient")
    if not patients:
        return "Patient: unknown"

    p = patients[0]
    name_entry = p.get("name", [{}])[0]
    given = name_entry.get("given", ["unknown"])[0]
    family = name_entry.get("family", "unknown")
    name = f"{given} {family}"

    birth_date = p.get("birthDate", "")
    age = ""
    if birth_date:
        try:
            age = str(datetime.now().year - int(birth_date[:4]))
        except ValueError:
            pass

    gender = p.get("gender", "unknown")

    parts = [f"Patient: {name}"]
    if age:
        parts.append(f"Age: {age}")
    parts.append(f"Gender: {gender}")
    return " | ".join(parts)


def _med_name(mr: dict) -> str:
    concept = mr.get("medicationCodeableConcept", {})
    name = concept.get("text")
    if name:
        return name
    codings = concept.get("coding", [])
    if codings:
        return codings[0].get("display") or codings[0].get("code") or "unknown"
    return "unknown"


def _rxnorm_code(mr: dict) -> Optional[str]:
    codings = mr.get("medicationCodeableConcept", {}).get("coding", [])
    for c in codings:
        if c.get("system") == RXNORM_SYSTEM:
            return c.get("code")
    if codings:
        return codings[0].get("code")
    return None


def _format_date(authored_on: Optional[str]) -> str:
    if not authored_on:
        return "-"
    return authored_on[:10]


def _parse_dosage(mr: dict) -> tuple:
    """Return (dose_str, frequency_str). Either may be None if not recorded."""
    instructions = mr.get("dosageInstruction", [])
    if not instructions:
        return None, None

    dosage = instructions[0]

    dose_str = None
    for dar in dosage.get("doseAndRate", []):
        dq = dar.get("doseQuantity", {})
        if dq.get("value") is not None:
            unit = dq.get("unit", "")
            dose_str = f"{dq['value']} {unit}".strip()
            break

    freq_str = None
    repeat = dosage.get("timing", {}).get("repeat", {})
    if repeat:
        freq = repeat.get("frequency")
        period = repeat.get("period")
        period_unit = repeat.get("periodUnit")
        if freq is not None and period is not None and period_unit is not None:
            unit_map = {
                "s": "second", "min": "minute", "h": "hour",
                "d": "day", "wk": "week", "mo": "month", "a": "year",
            }
            label = unit_map.get(period_unit, period_unit)
            period_str = str(int(period)) if period == int(period) else str(period)
            freq_str = f"{freq} time(s) per {period_str} {label}"

    return dose_str, freq_str


# Strategy A — MedicationRequests as clean JSON

MAX_MEDS_STRATEGY_A = 100

def serialise_a(bundle: dict) -> str:
    """
    Strategy A: raw FHIR JSON.

    Extracts all MedicationRequest resources and serialises them as indented
    JSON. Reference-only fields (subject, encounter, requester, meta, id) are
    stripped so the model sees only clinically relevant fields. The FHIR
    structure and field names are otherwise unchanged — this is the
    no-transformation baseline.

    Cap: inputs are limited to MAX_MEDS_STRATEGY_A entries. Synthea generates
    one MedicationRequest per refill, so patients with 10-30 year histories
    can accumulate 500-900+ entries for just a handful of drugs. Without a cap,
    these patients produce 600KB+ prompts that exceed LLM context limits and
    cause inference timeouts. Active medications are always included first;
    remaining slots are filled with the most recent historical entries sorted
    by authoredOn descending.
    """
    header = _patient_header(bundle)
    med_requests = enrich_med_requests(
        _get_resources(bundle, "MedicationRequest"),
        build_medication_index(bundle),
    )

    keep_fields = {
        "resourceType", "status", "authoredOn",
        "medicationCodeableConcept", "dosageInstruction",
    }
    cleaned = [
        {k: v for k, v in mr.items() if k in keep_fields}
        for mr in med_requests
    ]

    # Apply cap: active meds always kept, remainder filled by most recent first
    if len(cleaned) > MAX_MEDS_STRATEGY_A:
        active = [m for m in cleaned if m.get("status") == "active"]
        historical = [m for m in cleaned if m.get("status") != "active"]
        historical.sort(key=lambda m: m.get("authoredOn", ""), reverse=True)
        remaining_slots = MAX_MEDS_STRATEGY_A - len(active)
        cleaned = active + historical[:remaining_slots]

    body = json.dumps(cleaned, indent=2, ensure_ascii=False)
    return f"{header}\n\n{body}"


# Strategy B — Flat markdown table

def serialise_b(bundle: dict) -> str:
    """
    Strategy B: flat markdown table.

    One row per MedicationRequest sorted by prescribed date. Columns:
    Medication, RxNorm, Status, Prescribed, Dose, Frequency. All statuses are
    included. Missing dose or frequency values are shown as a dash.
    """
    header = _patient_header(bundle)
    med_requests = enrich_med_requests(
        _get_resources(bundle, "MedicationRequest"),
        build_medication_index(bundle),
    )

    rows = []
    for mr in med_requests:
        name = _med_name(mr)
        rxnorm = _rxnorm_code(mr) or "-"
        status = mr.get("status", "-")
        prescribed = _format_date(mr.get("authoredOn"))
        dose, freq = _parse_dosage(mr)
        rows.append((name, rxnorm, status, prescribed, dose or "-", freq or "-"))

    rows.sort(key=lambda r: r[3])

    table_lines = [
        "| Medication | RxNorm | Status | Prescribed | Dose | Frequency |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, rxnorm, status, prescribed, dose, freq in rows:
        table_lines.append(
            f"| {name} | {rxnorm} | {status} | {prescribed} | {dose} | {freq} |"
        )

    return f"{header}\n\n" + "\n".join(table_lines)


# Strategy C — Clinical narrative

def serialise_c(bundle: dict) -> str:
    """
    Strategy C: clinical narrative.

    Each MedicationRequest becomes a plain English sentence. Active medications
    are listed first under a clear heading, followed by historical medications
    sorted by date. Missing dosage is noted inline as 'dosage not recorded'.
    """
    header = _patient_header(bundle)
    med_requests = enrich_med_requests(
        _get_resources(bundle, "MedicationRequest"),
        build_medication_index(bundle),
    )

    active = [mr for mr in med_requests if mr.get("status") == "active"]
    historical = [mr for mr in med_requests if mr.get("status") != "active"]

    def med_sentence(mr: dict) -> str:
        name = _med_name(mr)
        rxnorm = _rxnorm_code(mr)
        status = mr.get("status", "unknown")
        prescribed = _format_date(mr.get("authoredOn"))
        dose, freq = _parse_dosage(mr)

        code_part = f" (RxNorm: {rxnorm})" if rxnorm else ""
        date_part = f", prescribed on {prescribed}" if prescribed != "-" else ""
        status_part = f", status: {status}"

        if dose and freq:
            dosage_part = f" Dose: {dose}, frequency: {freq}."
        elif dose:
            dosage_part = f" Dose: {dose}."
        elif freq:
            dosage_part = f" Frequency: {freq}."
        else:
            dosage_part = " Dosage not recorded."

        return f"{name}{code_part}{date_part}{status_part}.{dosage_part}"

    lines = [header, ""]

    if active:
        lines.append("Currently active medications:")
        for mr in sorted(active, key=lambda x: x.get("authoredOn") or ""):
            lines.append(f"  - {med_sentence(mr)}")
    else:
        lines.append("Currently active medications: none recorded.")

    lines.append("")

    if historical:
        lines.append("Medication history (no longer active):")
        for mr in sorted(historical, key=lambda x: x.get("authoredOn") or ""):
            lines.append(f"  - {med_sentence(mr)}")
    else:
        lines.append("Medication history: none recorded.")

    return "\n".join(lines)


# Strategy D — Chronological timeline

def serialise_d(bundle: dict) -> str:
    """
    Strategy D: chronological timeline, oldest to newest.

    All MedicationRequests are sorted strictly by authoredOn date regardless of
    status and presented as a flat timeline. The model must reason across the
    full history to determine what is currently active. This is the most
    demanding strategy for temporal reasoning.
    """
    header = _patient_header(bundle)
    med_requests = enrich_med_requests(
        _get_resources(bundle, "MedicationRequest"),
        build_medication_index(bundle),
    )

    sorted_mrs = sorted(med_requests, key=lambda mr: mr.get("authoredOn") or "")

    lines = [
        header,
        "",
        "Chronological medication history (oldest to newest):",
        "",
    ]

    for mr in sorted_mrs:
        name = _med_name(mr)
        rxnorm = _rxnorm_code(mr)
        status = mr.get("status", "unknown")
        date = _format_date(mr.get("authoredOn"))
        dose, freq = _parse_dosage(mr)

        code_part = f" (RxNorm: {rxnorm})" if rxnorm else ""

        if dose and freq:
            dosage_part = f"{dose}, {freq}"
        elif dose:
            dosage_part = dose
        elif freq:
            dosage_part = freq
        else:
            dosage_part = "-"

        lines.append(f"{date} | {status:<12} | {name}{code_part} | {dosage_part}")

    return "\n".join(lines)
