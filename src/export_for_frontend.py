"""
Export experiment results to a single JSON file for the Next.js frontend.

Reads:
  data/ground_truth/<patient_id>.json       — ground truth per patient
  output/results/<model>/<strategy>/<patient_id>_metrics.json  — per-run metrics

Writes:
  frontend/public/data/experiments.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH_DIR = ROOT / "data" / "ground_truth"
RESULTS_DIR = ROOT / "output" / "results"
INTERMEDIATE_DIR = ROOT / "output" / "intermediate"
OUTPUT_PATH = ROOT / "frontend" / "public" / "data" / "experiments.json"


def load_ground_truth() -> dict[str, dict[str, Any]]:
    ground_truth: dict[str, dict[str, Any]] = {}
    for gt_file in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        with gt_file.open() as f:
            data = json.load(f)
        patient_id = data["patient_id"]
        ground_truth[patient_id] = {
            "patient_name": data.get("patient_name", ""),
            "birth_date": data.get("birth_date", ""),
            "gender": data.get("gender", ""),
            "history_span_years": data.get("history_span_years", 0),
            "total_medication_requests": data.get("total_medication_requests", 0),
            "active_medication_count": data.get("active_medication_count", 0),
            "medications": [
                m["medication_name"] for m in data.get("medications", [])
            ],
            "medications_full": data.get("medications", []),
        }
    return ground_truth


def load_results() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_dir in sorted(RESULTS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        for strategy_dir in sorted(model_dir.iterdir()):
            if not strategy_dir.is_dir():
                continue
            strategy_name = strategy_dir.name
            for metrics_file in sorted(strategy_dir.glob("*_metrics.json")):
                with metrics_file.open() as f:
                    m = json.load(f)
                patient_id = m["patient_id"]
                # Read raw response (small, ~600B avg — embed for all runs)
                response_file = (
                    INTERMEDIATE_DIR / model_name / strategy_name / patient_id / "response.txt"
                )
                raw_response = response_file.read_text(encoding="utf-8").strip() if response_file.exists() else None

                rows.append({
                    "patient_id": patient_id,
                    "model": model_name,
                    "strategy": strategy_name,
                    "precision": m.get("precision", 0.0),
                    "recall": m.get("recall", 0.0),
                    "f1": m.get("f1", 0.0),
                    "exact_match": m.get("exact_match", 0),
                    "inference_time_s": m.get("inference_time_s", 0.0),
                    "tp": len(m.get("true_positives", [])),
                    "fp": len(m.get("false_positives", [])),
                    "fn": len(m.get("false_negatives", [])),
                    "predicted_count": m.get("predicted_count", 0),
                    "ground_truth_count": m.get("ground_truth_count", 0),
                    "parse_failed": m.get("parse_failed", False),
                    "true_positives": m.get("true_positives", []),
                    "false_positives": m.get("false_positives", []),
                    "false_negatives": m.get("false_negatives", []),
                    "raw_response": raw_response,
                })
    return rows


def derive_meta(rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = sorted({r["model"] for r in rows})
    strategies = sorted({r["strategy"] for r in rows})
    patients = sorted({r["patient_id"] for r in rows})
    total_runs = len(rows)
    # Include parse failures (f1=0) in means — consistent with the paper.
    mean_f1 = round(sum(r["f1"] for r in rows) / len(rows), 4) if rows else 0.0

    from collections import defaultdict
    model_f1s: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        model_f1s[r["model"]].append(r["f1"])
    best_model = max(model_f1s, key=lambda m: sum(model_f1s[m]) / len(model_f1s[m])) if model_f1s else ""

    strat_f1s: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        strat_f1s[r["strategy"]].append(r["f1"])
    best_strategy = max(strat_f1s, key=lambda s: sum(strat_f1s[s]) / len(strat_f1s[s])) if strat_f1s else ""

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_patients": len(patients),
        "total_runs": total_runs,
        "models": models,
        "strategies": strategies,
        "mean_f1_overall": mean_f1,
        "best_model": best_model,
        "best_strategy": best_strategy,
    }


def main() -> None:
    print("Loading ground truth...")
    ground_truth = load_ground_truth()
    print(f"  {len(ground_truth)} patients loaded")

    print("Loading experiment results...")
    rows = load_results()
    print(f"  {len(rows)} result rows loaded")

    meta = derive_meta(rows)
    print(f"  {meta['total_runs']} total runs across {len(meta['models'])} models x {len(meta['strategies'])} strategies")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "rows": rows,
        "ground_truth": ground_truth,
    }
    with OUTPUT_PATH.open("w") as f:
        json.dump(payload, f, separators=(",", ":"))

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Written to {OUTPUT_PATH}")
    print(f"File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
