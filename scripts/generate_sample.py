"""
generate_sample.py

Generates a small varied batch of synthetic FHIR R4 patients using Synthea.
Run this before the full 200-patient generation to inspect the output format
and verify the pipeline works end to end.

Usage:
    python scripts/generate_sample.py

Requirements:
    - Java 11 or higher installed and on PATH
    - Synthea jar downloaded (run scripts/setup_synthea.sh first)

Output:
    FHIR R4 JSON bundles are written to data/raw/
    Only patient bundles are copied. Hospital and practitioner metadata files
    that Synthea generates alongside patient data are ignored.
"""

import json
import subprocess
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JAR_PATH = REPO_ROOT / "synthea" / "synthea-with-dependencies.jar"
OUTPUT_DIR = REPO_ROOT / "data" / "raw"
SYNTHEA_OUTPUT_DIR = REPO_ROOT / "synthea" / "output" / "fhir"


def is_patient_bundle(filepath):
    """
    Returns True if the JSON file is a patient FHIR bundle.
    Synthea also outputs hospitalInformation and practitionerInformation files
    which we do not need. Those files do not contain a Patient resource.
    """
    try:
        with open(filepath) as f:
            bundle = json.load(f)
        entries = bundle.get("entry", [])
        return any(e.get("resource", {}).get("resourceType") == "Patient" for e in entries)
    except (json.JSONDecodeError, KeyError):
        return False


def check_java():
    result = subprocess.run(["java", "-version"], capture_output=True)
    if result.returncode != 0:
        print("Java is not installed or not on PATH.")
        print("Install Java 11 or higher and try again.")
        sys.exit(1)


def check_jar():
    if not JAR_PATH.exists():
        print(f"Synthea jar not found at {JAR_PATH}")
        print("Run scripts/setup_synthea.sh first.")
        sys.exit(1)


def run_synthea(count, age_range, label, module=None):
    print(f"Generating {count} patient(s): {label}")

    cmd = [
        "java", "-jar", str(JAR_PATH),
        f"-p", str(count),
        f"-a", age_range,
        "--exporter.fhir.export=true",
        f"--exporter.baseDirectory={REPO_ROOT / 'synthea' / 'output'}",
        "Massachusetts",
    ]

    if module:
        cmd += ["-m", module]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Synthea failed for batch: {label}")
        print(result.stderr)
        sys.exit(1)


def collect_output():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_files = list(SYNTHEA_OUTPUT_DIR.glob("*.json"))
    patient_files = [f for f in all_files if is_patient_bundle(f)]
    skipped = len(all_files) - len(patient_files)

    if not patient_files:
        print("No patient FHIR bundles found in Synthea output directory.")
        sys.exit(1)

    copied = 0
    for f in patient_files:
        dest = OUTPUT_DIR / f.name
        if not dest.exists():
            shutil.copy(f, dest)
            copied += 1

    print(f"Skipped {skipped} non-patient file(s) (hospital/practitioner metadata).")
    print(f"Copied {copied} new patient bundle(s) to {OUTPUT_DIR}")
    print(f"Total patient files in data/raw: {len(list(OUTPUT_DIR.glob('*.json')))}")


def main():
    check_java()
    check_jar()

    # Varied batches to get a mix of ages, history lengths, and complexity.
    # Adjust counts here if you want more or fewer patients per group.
    batches = [
        {"count": 2, "age_range": "65-75", "label": "older patients, longer history"},
        {"count": 2, "age_range": "50-60", "label": "middle-aged, medium history"},
        {"count": 2, "age_range": "40-50", "label": "younger, shorter history"},
        {"count": 2, "age_range": "60-70", "label": "diabetes-seeded, higher medication complexity", "module": "diabetes"},
    ]

    for batch in batches:
        run_synthea(
            count=batch["count"],
            age_range=batch["age_range"],
            label=batch["label"],
            module=batch.get("module"),
        )

    collect_output()
    print("Sample generation complete. Inspect data/raw/ before proceeding.")


if __name__ == "__main__":
    main()