"""
generate_previews.py

Generates input.txt and prompt.txt for all patients across all 4 serialisation
strategies, without calling any model. Use this to verify that serialisation
and prompt construction are correct before running full experiments.

Output is saved to:
    output/prompt_preview/strategy_<X>/<patient_id>/input.txt
    output/prompt_preview/strategy_<X>/<patient_id>/prompt.txt

Usage:
    # All strategies, all patients
    python src/generate_previews.py

    # Quick check: first 5 patients, strategy c only
    python src/generate_previews.py --strategy c --n 5

    # Regenerate (overwrite existing files)
    python src/generate_previews.py --overwrite
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from serialisers import serialise_a, serialise_b, serialise_c, serialise_d

RAW_DIR = REPO_ROOT / "data" / "raw"
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"
PREVIEW_DIR = REPO_ROOT / "output" / "prompt_preview"

STRATEGY_FUNCS: dict = {
    "a": serialise_a,
    "b": serialise_b,
    "c": serialise_c,
    "d": serialise_d,
}

ALL_STRATEGIES = ["a", "b", "c", "d"]
STRATEGIES_WITH_DASH = {"b", "c", "d"}

# Prompt template — kept in sync with run_experiments.py
PROMPT_BASE = """\
You are a clinical assistant performing medication reconciliation.

You will be given a patient's medication history. Your task is to identify all \
medications that are currently ACTIVE for this patient.

A medication is currently active if its status is "active". Medications with \
status "completed", "stopped", "cancelled", or "on-hold" are historical and \
must NOT be included in your answer.
{dash_note}
Return your answer as a JSON array of medication names exactly as they appear \
in the data. Return nothing else — no explanation, no prose, just the JSON array.

Example output format:
["Metformin 500 MG Oral Tablet", "Lisinopril 10 MG Oral Tablet"]

If there are no active medications, return an empty array: []

Patient data:
{patient_data}"""

DASH_NOTE = """
A dash (-) in the dose or frequency field means the dosage information was not \
recorded in the source data. It does not indicate the medication is inactive.
"""


def build_prompt(strategy_key: str, serialised_input: str) -> str:
    dash_note = DASH_NOTE if strategy_key in STRATEGIES_WITH_DASH else ""
    return PROMPT_BASE.format(dash_note=dash_note, patient_data=serialised_input)


def load_patients(n: int | None) -> list[tuple[str, dict]]:
    gt_files = sorted(GROUND_TRUTH_DIR.glob("*.json"))
    if n is not None:
        gt_files = gt_files[:n]

    patients = []
    for gt_file in gt_files:
        try:
            gt = json.loads(gt_file.read_text(encoding="utf-8"))
            patient_id = gt["patient_id"]
            source_file = gt.get("source_file")
            if not source_file:
                continue
            raw_path = RAW_DIR / source_file
            if not raw_path.exists():
                continue
            bundle = json.loads(raw_path.read_text(encoding="utf-8"))
            patients.append((patient_id, bundle))
        except Exception:
            continue

    return patients


def write_report(
    strategies: list[str],
    total_patients: int,
    written: int,
    skipped: int,
    failures: dict[str, list[tuple[str, str]]],
) -> None:
    """Write a markdown summary report to output/prompt_preview/report.md."""
    total_errors = sum(len(v) for v in failures.values())
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Prompt Preview Generation Report",
        "",
        f"Run: {run_time}",
        f"Strategies: {', '.join(f'strategy_{s}' for s in strategies)}",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"| --- | --- |",
        f"| Total patients | {total_patients} |",
        f"| Files written | {written} |",
        f"| Skipped (already existed) | {skipped} |",
        f"| Failures | {total_errors} |",
        "",
    ]

    if total_errors == 0:
        lines.append("All files generated successfully — no failures.")
    else:
        lines.append("## Failures")
        lines.append("")
        for strategy_key, failed in failures.items():
            if not failed:
                continue
            lines.append(f"### strategy_{strategy_key} ({len(failed)} failure(s))")
            lines.append("")
            for patient_id, error in failed:
                lines.append(f"- `{patient_id}`: {error}")
            lines.append("")

    report_path = PREVIEW_DIR / "report.md"
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report saved: {report_path}")


def generate_previews(
    strategies: list[str],
    patients: list[tuple[str, dict]],
    overwrite: bool,
) -> None:
    total = len(patients)
    skipped = 0
    written = 0
    failures: dict[str, list[tuple[str, str]]] = {s: [] for s in strategies}

    for strategy_key in strategies:
        serialise_fn = STRATEGY_FUNCS[strategy_key]
        for patient_id, bundle in patients:
            out_dir = PREVIEW_DIR / f"strategy_{strategy_key}" / patient_id
            input_path = out_dir / "input.txt"
            prompt_path = out_dir / "prompt.txt"

            if not overwrite and input_path.exists() and prompt_path.exists():
                skipped += 1
                continue

            try:
                serialised = serialise_fn(bundle)
                prompt = build_prompt(strategy_key, serialised)
                out_dir.mkdir(parents=True, exist_ok=True)
                input_path.write_text(serialised, encoding="utf-8")
                prompt_path.write_text(prompt, encoding="utf-8")
                written += 1
            except Exception as e:
                failures[strategy_key].append((patient_id, str(e)))
                print(f"ERROR  strategy_{strategy_key}/{patient_id}: {e}")

    total_errors = sum(len(v) for v in failures.values())
    print(
        f"Done. strategies={strategies} patients={total} "
        f"written={written} skipped={skipped} errors={total_errors}"
    )
    print(f"Output: {PREVIEW_DIR}")
    write_report(strategies, total, written, skipped, failures)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate input.txt and prompt.txt previews without calling any model.",
    )
    parser.add_argument(
        "--strategy",
        default="all",
        help="Strategy key (a, b, c, d) or 'all' (default: all)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Limit to first N patients (default: all)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files (default: skip if already present)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.strategy == "all":
        strategies = ALL_STRATEGIES
    elif args.strategy in ALL_STRATEGIES:
        strategies = [args.strategy]
    else:
        print(f"Unknown strategy: {args.strategy}. Choices: a, b, c, d, all")
        sys.exit(1)

    patients = load_patients(args.n)
    if not patients:
        print("No patients found. Check data/raw/ and data/ground_truth/.")
        sys.exit(1)

    print(f"Loaded {len(patients)} patient(s). Strategies: {strategies}")
    generate_previews(strategies, patients, args.overwrite)


if __name__ == "__main__":
    main()
