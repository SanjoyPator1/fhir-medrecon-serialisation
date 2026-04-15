"""Aggregate false-negative / false-positive patterns across all runs.

Reads per-patient metric JSONs from output/results/{model}/{strategy}/*_metrics.json
and produces summary statistics for the paper's error-analysis paragraph.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "output" / "results"


def load_all() -> list[dict]:
    records: list[dict] = []
    for model_dir in sorted(RESULTS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        for strategy_dir in sorted(model_dir.iterdir()):
            if not strategy_dir.is_dir():
                continue
            for metric_file in sorted(strategy_dir.glob("*_metrics.json")):
                with metric_file.open() as f:
                    records.append(json.load(f))
    return records


def analyse(records: list[dict]) -> None:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        grouped[(r["model"], r["strategy"])].append(r)

    print(f"Total per-patient runs loaded: {len(records)}\n")

    for (model, strategy), rs in sorted(grouped.items()):
        fn_all: list[str] = []
        fp_all: list[str] = []
        tp_all: list[str] = []
        for r in rs:
            fn_all.extend(r.get("false_negatives", []) or [])
            fp_all.extend(r.get("false_positives", []) or [])
            tp_all.extend(r.get("true_positives", []) or [])

        n_patients = len(rs)
        n_fn = len(fn_all)
        n_fp = len(fp_all)
        n_tp = len(tp_all)

        fn_len_median = median([len(x) for x in fn_all]) if fn_all else 0
        tp_len_median = median([len(x) for x in tp_all]) if tp_all else 0
        fn_long_frac = (
            sum(1 for x in fn_all if len(x) > 50) / n_fn if n_fn else 0.0
        )
        tp_long_frac = (
            sum(1 for x in tp_all if len(x) > 50) / n_tp if n_tp else 0.0
        )

        top_fn = Counter(fn_all).most_common(5)
        top_fp = Counter(fp_all).most_common(5)

        print(f"=== {model} / {strategy} ===")
        print(f"  patients: {n_patients}")
        print(f"  false_negatives total: {n_fn}")
        print(f"  false_positives total: {n_fp}")
        print(f"  true_positives total:  {n_tp}")
        print(f"  median FN name length: {fn_len_median}  (TP: {tp_len_median})")
        print(
            f"  FN with name > 50 chars: {fn_long_frac:.1%}  "
            f"(TP baseline: {tp_long_frac:.1%})"
        )
        print(f"  top-5 most-omitted: {top_fn}")
        print(f"  top-5 most-hallucinated: {top_fp}")
        print()


def headline_numbers(records: list[dict]) -> None:
    print("\n--- Headline numbers for paper paragraph ---\n")

    target = [
        ("mistral-7b", "strategy_c"),
        ("mistral-7b", "strategy_a"),
        ("llama-3.3-70b", "strategy_d"),
        ("phi-3.5-mini", "strategy_a"),
    ]
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        grouped[(r["model"], r["strategy"])].append(r)

    for key in target:
        rs = grouped.get(key, [])
        fn_all: list[str] = []
        tp_all: list[str] = []
        for r in rs:
            fn_all.extend(r.get("false_negatives", []) or [])
            tp_all.extend(r.get("true_positives", []) or [])
        n_fn = len(fn_all)
        n_long = sum(1 for x in fn_all if len(x) > 50)
        top = Counter(fn_all).most_common(1)
        gt_counts_with_drug: dict[str, int] = Counter()
        for r in rs:
            for m in (r.get("true_positives", []) or []) + (
                r.get("false_negatives", []) or []
            ):
                gt_counts_with_drug[m] += 1
        top_str = (
            f"{top[0][0]!r} missed {top[0][1]}/{gt_counts_with_drug[top[0][0]]} times"
            if top
            else "n/a"
        )
        print(
            f"{key[0]} / {key[1]}: FN={n_fn}, long-name FN={n_long} "
            f"({(n_long / n_fn if n_fn else 0):.1%}), top-missed: {top_str}"
        )


if __name__ == "__main__":
    records = load_all()
    analyse(records)
    headline_numbers(records)
