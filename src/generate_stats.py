"""
generate_stats.py

Computes per-patient and aggregate statistics for the FHIR medication
reconciliation dataset. Reads from:
  - data/raw/<source_file>              raw FHIR R4 bundles (medication stats)
  - data/ground_truth/<patient_id>.json only used as a manifest (patient IDs +
                                        source filenames); the data itself is NOT
                                        trusted here because it was generated
                                        before a fhir_utils fix
  - output/prompt_preview/strategy_*/   pre-generated input.txt / prompt.txt

Writes:
  - output/stats/per_patient/<patient_id>.json   one file per patient
  - output/stats/summary.json                    aggregate stats

Tokenization:
  Uses transformers.AutoTokenizer for exact per-model token counts.
  Gated models (LLaMA) require HF_TOKEN in .env. If a tokenizer fails to load
  the model is skipped and absent from token_counts fields.

Usage:
    python src/generate_stats.py [--ground-truth-dir ...] [--raw-dir ...]
                                 [--preview-dir ...] [--output-dir ...]
"""

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# Suppress noisy HuggingFace logs before importing transformers
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

try:
    from transformers import AutoTokenizer, logging as hf_logging
    hf_logging.set_verbosity_error()
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False

from fhir_utils import build_medication_index, enrich_med_requests

TOKENIZER_MAP: dict[str, str] = {
    "phi-3.5-mini":  "microsoft/Phi-3.5-mini-instruct",
    "mistral-7b":    "mistralai/Mistral-7B-v0.1",
    "llama-3.1-8b":  "meta-llama/Llama-3.1-8B",
    "biomistral":    "BioMistral/BioMistral-7B",
    "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct",
}

STRATEGIES = ["strategy_a", "strategy_b", "strategy_c", "strategy_d"]


def load_tokenizers(hf_token: Optional[str]) -> tuple[dict, list[str], list[str]]:
    """
    Attempt to load each model's tokenizer from HuggingFace.
    Returns (loaded_dict, loaded_names, skipped_names).
    """
    if not _TRANSFORMERS_AVAILABLE:
        print("Warning: transformers not installed. Token counts will be skipped.")
        return {}, [], list(TOKENIZER_MAP.keys())

    loaded: dict = {}
    skipped: list[str] = []

    for model_name, hf_id in TOKENIZER_MAP.items():
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                hf_id,
                token=hf_token or None,
                trust_remote_code=False,
            )
            loaded[model_name] = tokenizer
            print(f"  loaded  {model_name:<16} ({hf_id})")
        except Exception as e:
            skipped.append(model_name)
            print(f"  skipped {model_name:<16} ({hf_id}) — {e}")

    return loaded, list(loaded.keys()), skipped


def text_stats(text: str, tokenizers: dict) -> dict:
    """
    Compute character, word, line counts and exact per-model token counts.
    """
    token_counts: dict[str, int] = {}
    for model_name, tokenizer in tokenizers.items():
        ids = tokenizer.encode(text, add_special_tokens=False)
        token_counts[model_name] = len(ids)

    result: dict = {
        "char_count": len(text),
        "word_count": len(text.split()),
        "line_count": text.count("\n") + 1,
    }
    if token_counts:
        result["token_counts"] = token_counts
    return result


def compute_percentiles(values: list[float]) -> dict:
    """
    Return descriptive statistics for a list of numeric values.
    """
    if not values:
        return {}
    n = len(values)
    sorted_vals = sorted(values)

    def percentile(p: float) -> float:
        idx = (p / 100) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        return sorted_vals[lo] * (1 - (idx - lo)) + sorted_vals[hi] * (idx - lo)

    return {
        "mean":   round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min":    min(values),
        "max":    max(values),
        "p25":    round(percentile(25), 2),
        "p75":    round(percentile(75), 2),
        "p95":    round(percentile(95), 2),
    }


def check_structured_dosage(mr: dict) -> bool:
    """
    Return True if the MedicationRequest has any structured dosage information
    (timing or dose quantity). Mirrors the logic in ground_truth.py.
    """
    dosage_instructions = mr.get("dosageInstruction", [])
    if not dosage_instructions:
        return False
    dosage = dosage_instructions[0]

    repeat = dosage.get("timing", {}).get("repeat", {})
    has_frequency = (
        repeat.get("frequency") is not None
        and repeat.get("period") is not None
        and repeat.get("periodUnit") is not None
    )

    dose_and_rate = dosage.get("doseAndRate", [])
    has_dose = bool(
        dose_and_rate
        and dose_and_rate[0].get("doseQuantity", {}).get("value") is not None
    )

    return has_frequency or has_dose


def parse_medication_stats(raw_path: Path) -> Optional[dict]:
    """
    Parse a raw FHIR R4 bundle and return medication statistics with no entry cap.
    Uses the updated fhir_utils to resolve medicationReference correctly.
    """
    try:
        with open(raw_path, encoding="utf-8") as f:
            bundle = json.load(f)
    except Exception as e:
        print(f"\nCould not load {raw_path.name}: {e}")
        return None

    all_entries = [
        entry["resource"]
        for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == "MedicationRequest"
    ]
    all_entries = enrich_med_requests(all_entries, build_medication_index(bundle))

    status_breakdown: dict[str, int] = {}
    for mr in all_entries:
        status = mr.get("status", "unknown")
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

    active_meds = [mr for mr in all_entries if mr.get("status") == "active"]
    active_with    = sum(1 for mr in active_meds if check_structured_dosage(mr))
    active_without = len(active_meds) - active_with

    dates = sorted(
        authored[:4]
        for mr in all_entries
        if (authored := mr.get("authoredOn"))
    )
    history_span: Optional[int] = (
        int(dates[-1]) - int(dates[0]) if len(dates) >= 2 else None
    )

    return {
        "total_requests":                len(all_entries),
        "status_breakdown":              status_breakdown,
        "active_count":                  len(active_meds),
        "active_with_structured_dosage": active_with,
        "active_without_structured_dosage": active_without,
        "history_span_years":            history_span,
    }


def build_summary(all_stats: list[dict], loaded_names: list[str], skipped_names: list[str]) -> dict:
    """
    Aggregate per-patient stats into a summary dict.
    """
    active_counts   = [p["medication_stats"]["active_count"]          for p in all_stats]
    total_req_counts= [p["medication_stats"]["total_requests"]         for p in all_stats]
    with_structured = [p["medication_stats"]["active_with_structured_dosage"]    for p in all_stats]
    without_structured=[p["medication_stats"]["active_without_structured_dosage"] for p in all_stats]

    global_status_totals: dict[str, int] = {}
    for p in all_stats:
        for status, count in p["medication_stats"]["status_breakdown"].items():
            global_status_totals[status] = global_status_totals.get(status, 0) + count

    strategy_summary: dict = {}
    for strategy in STRATEGIES:
        patients_with_strategy = [p for p in all_stats if strategy in p["strategy_stats"]]
        if not patients_with_strategy:
            continue
        strategy_summary[strategy] = {}
        for section in ("input", "prompt"):
            chars = [p["strategy_stats"][strategy][section]["char_count"] for p in patients_with_strategy]
            words = [p["strategy_stats"][strategy][section]["word_count"] for p in patients_with_strategy]
            lines = [p["strategy_stats"][strategy][section]["line_count"] for p in patients_with_strategy]

            token_summary: dict[str, dict] = {}
            for model_name in loaded_names:
                counts = [
                    p["strategy_stats"][strategy][section]["token_counts"][model_name]
                    for p in patients_with_strategy
                    if "token_counts" in p["strategy_stats"][strategy][section]
                    and model_name in p["strategy_stats"][strategy][section]["token_counts"]
                ]
                if counts:
                    token_summary[model_name] = compute_percentiles(counts)

            section_summary: dict = {
                "char_count": compute_percentiles(chars),
                "word_count": compute_percentiles(words),
                "line_count": compute_percentiles(lines),
            }
            if token_summary:
                section_summary["token_counts"] = token_summary

            strategy_summary[strategy][section] = section_summary

    return {
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "total_patients":     len(all_stats),
        "tokenizers_loaded":  loaded_names,
        "tokenizers_skipped": skipped_names,
        "medication_stats": {
            "active_count_per_patient":                      compute_percentiles(active_counts),
            "total_requests_per_patient":                    compute_percentiles(total_req_counts),
            "global_status_totals":                          global_status_totals,
            "active_with_structured_dosage_per_patient":     compute_percentiles(with_structured),
            "active_without_structured_dosage_per_patient":  compute_percentiles(without_structured),
        },
        "strategy_stats": strategy_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-patient and aggregate dataset statistics."
    )
    parser.add_argument(
        "--ground-truth-dir", type=Path,
        default=REPO_ROOT / "data" / "ground_truth",
        help="Directory containing ground truth JSON files (used as patient manifest only)",
    )
    parser.add_argument(
        "--raw-dir", type=Path,
        default=REPO_ROOT / "data" / "raw",
        help="Directory containing raw FHIR R4 bundle JSON files",
    )
    parser.add_argument(
        "--preview-dir", type=Path,
        default=REPO_ROOT / "output" / "prompt_preview",
        help="Directory containing pre-generated input.txt / prompt.txt files",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=REPO_ROOT / "output" / "stats",
        help="Directory to write per-patient JSONs and summary",
    )
    args = parser.parse_args()

    hf_token = os.getenv("HF_TOKEN", "").strip() or None

    print("Loading tokenizers...")
    tokenizers, loaded_names, skipped_names = load_tokenizers(hf_token)
    print(f"\nLoaded:  {loaded_names or 'none'}")
    print(f"Skipped: {skipped_names or 'none'}")
    print()

    per_patient_dir = args.output_dir / "per_patient"
    per_patient_dir.mkdir(parents=True, exist_ok=True)

    gt_files = sorted(args.ground_truth_dir.glob("*.json"))
    if not gt_files:
        print(f"No ground truth files found in {args.ground_truth_dir}.")
        sys.exit(1)

    all_patient_stats: list[dict] = []

    for gt_path in tqdm(gt_files, desc="Processing patients"):
        with open(gt_path, encoding="utf-8") as f:
            gt = json.load(f)

        patient_id  = gt["patient_id"]
        source_file = gt.get("source_file", "")
        raw_path    = args.raw_dir / source_file

        if not raw_path.exists():
            print(f"\nWarning: raw FHIR file not found for {patient_id}: {source_file}")
            continue

        med_stats = parse_medication_stats(raw_path)
        if med_stats is None:
            continue

        strategy_stats: dict = {}
        for strategy in STRATEGIES:
            input_path  = args.preview_dir / strategy / patient_id / "input.txt"
            prompt_path = args.preview_dir / strategy / patient_id / "prompt.txt"
            if not input_path.exists() or not prompt_path.exists():
                continue
            input_stats  = text_stats(input_path.read_text(encoding="utf-8"),  tokenizers)
            prompt_stats = text_stats(prompt_path.read_text(encoding="utf-8"), tokenizers)
            input_stats["path"]  = str(input_path)
            prompt_stats["path"] = str(prompt_path)
            strategy_stats[strategy] = {
                "input":  input_stats,
                "prompt": prompt_stats,
            }

        patient_stat: dict = {
            "patient_id":   patient_id,
            "patient_name": gt["patient_name"],
            "gender":       gt["gender"],
            "history_span_years": med_stats["history_span_years"],
            "medication_stats": {
                "total_requests":                    med_stats["total_requests"],
                "status_breakdown":                  med_stats["status_breakdown"],
                "active_count":                      med_stats["active_count"],
                "active_with_structured_dosage":     med_stats["active_with_structured_dosage"],
                "active_without_structured_dosage":  med_stats["active_without_structured_dosage"],
            },
            "strategy_stats": strategy_stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        out_path = per_patient_dir / f"{patient_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(patient_stat, f, indent=2, ensure_ascii=False)

        all_patient_stats.append(patient_stat)

    print(f"\nProcessed {len(all_patient_stats)} patients. Building summary...")

    summary = build_summary(all_patient_stats, loaded_names, skipped_names)
    summary_path = args.output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Per-patient stats : {per_patient_dir}  ({len(all_patient_stats)} files)")
    print(f"Summary           : {summary_path}")


if __name__ == "__main__":
    main()
