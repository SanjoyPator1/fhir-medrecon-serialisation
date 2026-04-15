#!/usr/bin/env python3
"""
src/analyse_results.py

Phase 5 analysis: builds the master results DataFrame, generates aggregate tables,
produces 10 research figures, runs statistical significance tests, and identifies
universally hard patients.

Usage:
    python src/analyse_results.py           # all outputs
    python src/analyse_results.py --plots   # figures only
    python src/analyse_results.py --stats   # tables + tests only
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

matplotlib.use("Agg")

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "output" / "results"
GROUND_TRUTH_DIR = ROOT / "data" / "ground_truth"
STATS_DIR = ROOT / "output" / "stats" / "per_patient"
OUT_DIR = ROOT / "results"
FIGURES_DIR = OUT_DIR / "figures"

MODELS = [
    "phi-3.5-mini",
    "mistral-7b",
    "biomistral",
    "llama-3.1-8b",
    "llama-3.3-70b",
]
MAIN_MODELS = [m for m in MODELS if m != "biomistral"]
STRATEGIES = ["strategy_a", "strategy_b", "strategy_c", "strategy_d"]

MODEL_LABELS = {
    "phi-3.5-mini": "Phi-3.5-mini\n(3.8B)",
    "mistral-7b": "Mistral-7B",
    "biomistral": "BioMistral-7B",
    "llama-3.1-8b": "Llama-3.1-8B",
    "llama-3.3-70b": "Llama-3.3-70B",
}
MODEL_LABELS_SHORT = {
    "phi-3.5-mini": "Phi-3.5\n(3.8B)",
    "mistral-7b": "Mistral\n(7B)",
    "biomistral": "BioMistral\n(7B)",
    "llama-3.1-8b": "Llama-3.1\n(8B)",
    "llama-3.3-70b": "Llama-3.3\n(70B)",
}
STRATEGY_LABELS = {
    "strategy_a": "A — Raw JSON",
    "strategy_b": "B — Markdown Table",
    "strategy_c": "C — Clinical Narrative",
    "strategy_d": "D — Chrono. Timeline",
}
STRATEGY_SHORT = {
    "strategy_a": "A",
    "strategy_b": "B",
    "strategy_c": "C",
    "strategy_d": "D",
}
MODEL_SIZES = {
    "phi-3.5-mini": 3.8,
    "mistral-7b": 7.0,
    "biomistral": 7.0,
    "llama-3.1-8b": 8.0,
    "llama-3.3-70b": 70.0,
}
STRATEGY_COLORS = {
    "strategy_a": "#66c2a5",
    "strategy_b": "#fc8d62",
    "strategy_c": "#8da0cb",
    "strategy_d": "#e78ac3",
}

# BioMistral failure mode counts — hardcoded from manual inspection
# (not derivable from metrics.json; from notes/10-biomistral-results.md)
BIOMISTRAL_FAILURES = {
    "strategy_a": {"Garbled/incoherent": 140, "Empty response": 48, "Prompt continuation": 11, "Chatbot greeting": 1},
    "strategy_b": {"Garbled/incoherent": 113, "Empty response": 22, "Prompt continuation": 56, "Chatbot greeting": 3, "Other": 6},
    "strategy_c": {"Garbled/incoherent": 133, "Empty response": 14, "Prompt continuation": 44, "Chatbot greeting": 5, "Other": 4},
    "strategy_d": {"Garbled/incoherent": 113, "Empty response": 17, "Prompt continuation": 68, "Chatbot greeting": 1, "Other": 1},
}

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 150,
})


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_master_df() -> pd.DataFrame:
    """Load all metrics.json files and augment with patient metadata."""
    print("Loading metrics files...")
    rows = []
    for model in MODELS:
        for strategy in STRATEGIES:
            path = RESULTS_DIR / model / strategy
            if not path.exists():
                print(f"  WARNING: missing {model}/{strategy}", file=sys.stderr)
                continue
            for fpath in sorted(path.glob("*_metrics.json")):
                with open(fpath) as f:
                    data = json.load(f)
                rows.append({
                    "patient_id": data["patient_id"],
                    "model": model,
                    "strategy": strategy,
                    "precision": float(data.get("precision", 0.0) or 0.0),
                    "recall": float(data.get("recall", 0.0) or 0.0),
                    "f1": float(data.get("f1", 0.0) or 0.0),
                    "exact_match": int(data.get("exact_match", 0) or 0),
                    "parse_failed": bool(data.get("parse_failed", False)),
                    "inference_time_s": float(data.get("inference_time_s", 0.0) or 0.0),
                    "predicted_count": int(data.get("predicted_count", 0) or 0),
                    "ground_truth_count": int(data.get("ground_truth_count", 0) or 0),
                })

    df = pd.DataFrame(rows)
    print(f"  Loaded {len(df)} rows")

    # Augment with patient metadata
    print("Loading patient metadata...")
    gt_counts: dict[str, int] = {}
    history_spans: dict[str, float] = {}

    for fpath in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        with open(fpath) as f:
            data = json.load(f)
        pid = data["patient_id"]
        gt_counts[pid] = int(data.get("active_medication_count", 0))

    for fpath in sorted(STATS_DIR.glob("*.json")):
        with open(fpath) as f:
            data = json.load(f)
        pid = data["patient_id"]
        history_spans[pid] = float(data.get("history_span_years", 0.0))

    df["gt_count"] = df["patient_id"].map(gt_counts)
    df["history_span_years"] = df["patient_id"].map(history_spans)

    missing_gt = df["gt_count"].isna().sum()
    if missing_gt > 0:
        print(f"  WARNING: {missing_gt} rows missing gt_count", file=sys.stderr)
        df["gt_count"] = df["gt_count"].fillna(df["ground_truth_count"])

    missing_span = df["history_span_years"].isna().sum()
    if missing_span > 0:
        print(f"  WARNING: {missing_span} rows missing history_span_years", file=sys.stderr)
        df["history_span_years"] = df["history_span_years"].fillna(0.0)

    df["gt_count"] = df["gt_count"].astype(int)
    return df


def build_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Compute aggregate metrics per (model, strategy)."""
    agg = (
        df.groupby(["model", "strategy"])
        .agg(
            n=("f1", "count"),
            mean_f1=("f1", "mean"),
            std_f1=("f1", "std"),
            median_f1=("f1", "median"),
            mean_precision=("precision", "mean"),
            mean_recall=("recall", "mean"),
            perfect=("f1", lambda x: (x == 1.0).sum()),
            zero_f1=("f1", lambda x: (x == 0.0).sum()),
            parse_failed=("parse_failed", "sum"),
            mean_inference_s=("inference_time_s", "mean"),
        )
        .reset_index()
    )
    return agg


# ── Table Outputs ─────────────────────────────────────────────────────────────

def save_aggregate_csv(agg: pd.DataFrame) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    agg.to_csv(OUT_DIR / "aggregate_table.csv", index=False)
    print("Saved results/aggregate_table.csv")


def save_aggregate_markdown(agg: pd.DataFrame) -> None:
    model_order = MODELS
    strategy_order = STRATEGIES

    lines = []
    lines.append("# Aggregate Results Table")
    lines.append("")
    lines.append(
        "| Model | Strategy | n | Mean F1 | Mean Prec | Mean Recall | Median F1 | Perfect | Zero F1 | Parse Failed |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    for model in model_order:
        for strategy in strategy_order:
            row = agg[(agg["model"] == model) & (agg["strategy"] == strategy)]
            if row.empty:
                continue
            r = row.iloc[0]
            lines.append(
                f"| {MODEL_LABELS.get(model, model).replace(chr(10), ' ')} "
                f"| {STRATEGY_LABELS[strategy]} "
                f"| {int(r['n'])} "
                f"| {r['mean_f1']:.4f} "
                f"| {r['mean_precision']:.4f} "
                f"| {r['mean_recall']:.4f} "
                f"| {r['median_f1']:.4f} "
                f"| {int(r['perfect'])} "
                f"| {int(r['zero_f1'])} "
                f"| {int(r['parse_failed'])} |"
            )

    content = "\n".join(lines)
    (OUT_DIR / "aggregate_table.md").write_text(content)
    print("Saved results/aggregate_table.md")


def save_master_csv(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / "master_results.csv", index=False)
    print(f"Saved results/master_results.csv ({len(df)} rows)")


# ── Statistical Tests ─────────────────────────────────────────────────────────

def run_statistical_tests(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    lines = []
    lines.append("# Statistical Significance Tests")
    lines.append("")
    lines.append("All tests use the Wilcoxon signed-rank test (non-parametric, paired on patient ID).")
    lines.append("Effect size: r = Z / sqrt(N), where N = number of pairs.")
    lines.append("p-values for strategy comparisons are Bonferroni-corrected (4 tests per model).")
    lines.append("")

    # 1. Strategy A vs C within each main model
    lines.append("## 1. Strategy A vs Strategy C (within model, paired on patient)")
    lines.append("")
    lines.append("| Model | W | p (uncorrected) | p (Bonferroni, k=4) | r | Interpretation |")
    lines.append("|---|---|---|---|---|---|")

    for model in MAIN_MODELS:
        a = df[(df["model"] == model) & (df["strategy"] == "strategy_a")].set_index("patient_id")["f1"]
        c = df[(df["model"] == model) & (df["strategy"] == "strategy_c")].set_index("patient_id")["f1"]
        shared = a.index.intersection(c.index)
        a = a.loc[shared].sort_index()
        c = c.loc[shared].sort_index()
        diff = c.values - a.values
        if (diff == 0).all():
            lines.append(f"| {MODEL_LABELS.get(model, model).replace(chr(10), ' ')} | — | — | — | — | No difference (all zero) |")
            continue
        try:
            result = stats.wilcoxon(diff, alternative="two-sided")
            w = result.statistic
            p = result.pvalue
            p_bonf = min(p * 4, 1.0)
            n = len(diff[diff != 0])
            z = stats.norm.ppf(1 - max(min(p / 2, 0.5), 1e-15))
            r = abs(z) / np.sqrt(n) if n > 0 else 0.0
            direction = "C > A" if diff.mean() > 0 else "A > C"
            sig = "***" if p_bonf < 0.001 else ("**" if p_bonf < 0.01 else ("*" if p_bonf < 0.05 else "ns"))
            lines.append(
                f"| {MODEL_LABELS.get(model, model).replace(chr(10), ' ')} "
                f"| {w:.0f} | {p:.4e} | {p_bonf:.4e} {sig} | {r:.3f} | {direction} |"
            )
        except Exception as e:
            lines.append(f"| {model} | ERROR: {e} |")

    lines.append("")

    # 2. Cross-model comparisons on Strategy C
    lines.append("## 2. Cross-Model Comparisons on Strategy C (paired on patient)")
    lines.append("")
    lines.append("| Comparison | W | p | r | Interpretation |")
    lines.append("|---|---|---|---|---|")

    # Each tuple: (model_a, model_b, label, alternative)
    # diff = model_b - model_a; alternative describes expected direction of diff
    comparisons = [
        ("mistral-7b", "llama-3.1-8b", "Mistral-7B vs Llama-3.1-8B", "two-sided"),
        ("llama-3.1-8b", "llama-3.3-70b", "Llama-3.1-8B vs Llama-3.3-70B", "two-sided"),
        # diff = biomistral - mistral; we expect this to be < 0 (Mistral > BioMistral)
        ("mistral-7b", "biomistral", "Mistral-7B vs BioMistral-7B (one-sided: Mistral > BioMistral)", "less"),
    ]

    for model_a, model_b, label, alt in comparisons:
        a = df[(df["model"] == model_a) & (df["strategy"] == "strategy_c")].set_index("patient_id")["f1"]
        b_ser = df[(df["model"] == model_b) & (df["strategy"] == "strategy_c")].set_index("patient_id")["f1"]
        shared = a.index.intersection(b_ser.index)
        a = a.loc[shared].sort_index()
        b_ser = b_ser.loc[shared].sort_index()
        diff = b_ser.values - a.values
        if (diff == 0).all():
            lines.append(f"| {label} | — | — | — | No difference |")
            continue
        try:
            result = stats.wilcoxon(diff, alternative=alt)
            w = result.statistic
            p = result.pvalue
            n = len(diff[diff != 0])
            z = stats.norm.ppf(1 - max(min(p / 2, 0.5), 1e-15))
            r = abs(z) / np.sqrt(n) if n > 0 else 0.0
            direction = f"{model_b} > {model_a}" if diff.mean() > 0 else f"{model_a} > {model_b}"
            sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
            lines.append(f"| {label} | {w:.0f} | {p:.4e} {sig} | {r:.3f} | {direction} |")
        except Exception as e:
            lines.append(f"| {label} | ERROR: {e} |")

    lines.append("")
    lines.append("Significance codes: *** p<0.001, ** p<0.01, * p<0.05, ns not significant")

    content = "\n".join(lines)
    (OUT_DIR / "statistical_tests.md").write_text(content)
    print("Saved results/statistical_tests.md")


# ── Hard Patient Analysis ─────────────────────────────────────────────────────

def save_hard_patients(df: pd.DataFrame) -> None:
    main_df = df[df["model"].isin(MAIN_MODELS)]
    # Mean F1 per patient across all main models and strategies
    patient_mean = (
        main_df.groupby("patient_id")["f1"]
        .mean()
        .reset_index()
        .rename(columns={"f1": "mean_f1_all"})
    )
    hard = patient_mean[patient_mean["mean_f1_all"] < 0.5].sort_values("mean_f1_all")

    lines = []
    lines.append("# Hard Patient Analysis")
    lines.append("")
    lines.append(
        "Patients with mean F1 < 0.5 averaged across all 4 main models and all 4 strategies."
    )
    lines.append("")

    if hard.empty:
        lines.append("No patients with mean F1 < 0.5 found.")
    else:
        lines.append(f"Found {len(hard)} universally hard patient(s).")
        lines.append("")
        lines.append("| Patient ID (prefix) | Mean F1 | GT Count | History Span (yrs) |")
        lines.append("|---|---|---|---|")
        for _, row in hard.iterrows():
            pid = row["patient_id"]
            pid_meta = df[df["patient_id"] == pid].iloc[0]
            gt = int(pid_meta["gt_count"])
            span = pid_meta["history_span_years"]
            lines.append(f"| {pid[:8]} | {row['mean_f1_all']:.4f} | {gt} | {span:.0f} |")

        lines.append("")
        lines.append("## Per-Model Per-Strategy F1 for Hard Patients")
        lines.append("")
        for _, row in hard.iterrows():
            pid = row["patient_id"]
            lines.append(f"### Patient `{pid[:8]}` (full: `{pid}`)")
            lines.append("")
            lines.append("| Model | Strat A | Strat B | Strat C | Strat D |")
            lines.append("|---|---|---|---|---|")
            for model in MAIN_MODELS:
                f1s = []
                for strat in STRATEGIES:
                    val = df[(df["patient_id"] == pid) & (df["model"] == model) & (df["strategy"] == strat)]["f1"]
                    f1s.append(f"{val.iloc[0]:.4f}" if not val.empty else "—")
                lines.append(f"| {MODEL_LABELS.get(model, model).replace(chr(10), ' ')} | {' | '.join(f1s)} |")
            lines.append("")

    (OUT_DIR / "hard_patients.md").write_text("\n".join(lines))
    print("Saved results/hard_patients.md")


# ── Figures ───────────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  Saved results/figures/{name}")


def fig01_heatmap(agg: pd.DataFrame) -> None:
    """F1 heatmap — main paper figure."""
    model_order = MODELS
    strat_order = STRATEGIES
    bio_idx = model_order.index("biomistral")  # index 2

    # Build matrix: rows=models, cols=strategies
    matrix = np.zeros((len(model_order), len(strat_order)))
    for i, model in enumerate(model_order):
        for j, strat in enumerate(strat_order):
            row = agg[(agg["model"] == model) & (agg["strategy"] == strat)]
            if not row.empty:
                matrix[i, j] = row.iloc[0]["mean_f1"]

    fig, ax = plt.subplots(figsize=(8, 6.2))

    # Draw the main RdYlGn heatmap for all rows.
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    # Overlay a solid mid-grey rectangle on the BioMistral row only.
    # extent=(xmin, xmax, ymax, ymin) in data coordinates.
    ax.imshow(
        np.full((1, len(strat_order)), 0.55),
        cmap="Greys",
        aspect="auto",
        vmin=0,
        vmax=1,
        extent=(-0.5, len(strat_order) - 0.5,
                bio_idx + 0.5, bio_idx - 0.5),
        zorder=2,
    )

    # Annotate cells with adaptive contrast:
    #   - white text on dark green  (val > 0.75)
    #   - white text on dark red    (val < 0.15)
    #   - black text in the middle  (0.15 – 0.75)
    #   - BioMistral row always gets white text (mid-grey background)
    for i in range(len(model_order)):
        for j in range(len(strat_order)):
            val = matrix[i, j]
            if i == bio_idx:
                txt_color = "white"
            elif val > 0.75 or val < 0.15:
                txt_color = "white"
            else:
                txt_color = "#1a1a1a"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=txt_color, zorder=3)

    # Y-axis: model names, two lines → newline kept for spacing
    ax.set_yticks(range(len(model_order)))
    ax.set_yticklabels(
        [MODEL_LABELS_SHORT[m].replace("\n", "\n") for m in model_order],
        fontsize=10,
    )

    # X-axis: full strategy names at the bottom, angled to avoid overlap
    # Short x-tick labels: "A  Raw JSON", "B  Markdown Table" etc.
    short_xlabels = [
        f"{STRATEGY_SHORT[s]}  {STRATEGY_LABELS[s].split('— ')[1]}"
        for s in strat_order
    ]
    ax.set_xticks(range(len(strat_order)))
    ax.set_xticklabels(short_xlabels, fontsize=9.5)
    ax.tick_params(axis="x", length=0, pad=5)

    ax.set_xlabel("Serialisation Strategy", fontsize=11, labelpad=6)
    ax.set_title("Mean F1 Score by Model and Serialisation Strategy",
                 fontsize=12, pad=14)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Mean F1", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    # Restore ylim after the second imshow call resets it.
    ax.set_ylim(len(model_order) - 0.5, -0.5)

    fig.tight_layout()
    _save(fig, "01_heatmap_f1.png")


def fig02_bar_chart(agg: pd.DataFrame) -> None:
    """Grouped bar chart — F1 by model (main models only), colored by strategy."""
    main_agg = agg[agg["model"].isin(MAIN_MODELS)]
    model_order = MAIN_MODELS
    strat_order = STRATEGIES

    n_models = len(model_order)
    n_strats = len(strat_order)
    x = np.arange(n_models)
    width = 0.18
    offsets = np.linspace(-(n_strats - 1) / 2 * width, (n_strats - 1) / 2 * width, n_strats)

    fig, ax = plt.subplots(figsize=(9, 5))

    for k, strat in enumerate(strat_order):
        means = []
        cis = []
        for model in model_order:
            row = main_agg[(main_agg["model"] == model) & (main_agg["strategy"] == strat)]
            if row.empty:
                means.append(0)
                cis.append(0)
                continue
            r = row.iloc[0]
            means.append(r["mean_f1"])
            n = r["n"]
            # 95% CI using std
            se = r["std_f1"] / np.sqrt(n)
            cis.append(1.96 * se)

        bars = ax.bar(
            x + offsets[k],
            means,
            width=width,
            yerr=cis,
            capsize=3,
            color=STRATEGY_COLORS[strat],
            label=STRATEGY_LABELS[strat],
            alpha=0.9,
            error_kw={"elinewidth": 1, "ecolor": "grey"},
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [MODEL_LABELS_SHORT[m].replace("\n", " ") for m in model_order],
        rotation=20, ha="right", fontsize=9.5,
    )
    ax.tick_params(axis="x", length=0, pad=4)
    ax.set_ylabel("Mean F1 Score", fontsize=11)
    ax.set_ylim(0, 1.08)
    ax.set_title("Mean F1 by Model and Serialisation Strategy (±95% CI)", fontsize=12, pad=10)
    ax.legend(loc="upper left", fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)

    fig.tight_layout()
    _save(fig, "02_bar_chart_f1.png")


def fig03_strategy_rank_by_size(agg: pd.DataFrame) -> None:
    """Strategy rank across model sizes — core ablation figure."""
    fig, ax = plt.subplots(figsize=(8, 5))

    # x positions with jitter for Mistral vs BioMistral (both 7B)
    x_jitter = {
        "phi-3.5-mini": 3.8,
        "mistral-7b": 6.7,
        "biomistral": 7.3,
        "llama-3.1-8b": 8.0,
        "llama-3.3-70b": 70.0,
    }

    for strat in STRATEGIES:
        xs, ys = [], []
        for model in MAIN_MODELS:
            row = agg[(agg["model"] == model) & (agg["strategy"] == strat)]
            if row.empty:
                continue
            xs.append(x_jitter[model])
            ys.append(row.iloc[0]["mean_f1"])
        ax.plot(xs, ys, "o-", color=STRATEGY_COLORS[strat], label=STRATEGY_LABELS[strat],
                linewidth=1.8, markersize=7)

    # BioMistral — dashed line across all strategies
    bio_x = x_jitter["biomistral"]
    bio_row = agg[agg["model"] == "biomistral"]
    if not bio_row.empty:
        # All zero — plot as a single marker at 0
        ax.axhline(y=0.0, xmin=0, xmax=0, color="grey", linestyle="--", alpha=0.5)
        ax.scatter([bio_x] * 4, [0, 0, 0, 0], color="grey", marker="x", s=60, zorder=5,
                   label="BioMistral-7B (all strategies)", alpha=0.8)

    ax.set_xscale("log")
    ax.set_xticks([3.8, 7.0, 8.0, 70.0])
    ax.set_xticklabels(
        ["Phi-3.5 (3.8B)", "Mistral (7B)", "Llama-3.1 (8B)", "Llama-3.3 (70B)"],
        rotation=25, ha="right", fontsize=9.5,
    )
    ax.tick_params(axis="x", length=0, pad=4)
    ax.set_xlabel("Model (parameter count)", fontsize=11, labelpad=6)
    ax.set_ylabel("Mean F1 Score", fontsize=11)
    ax.set_ylim(-0.05, 1.08)
    ax.set_title("Serialisation Strategy Performance Across Model Sizes", fontsize=12, pad=10)
    ax.legend(loc="lower right", fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    fig.tight_layout()
    _save(fig, "03_strategy_rank_by_size.png")


def fig04_recall_vs_gt_count(df: pd.DataFrame) -> None:
    """Recall vs. active medication count (omission analysis)."""
    fig, ax = plt.subplots(figsize=(9, 5))

    colors = {
        "phi-3.5-mini": "#e41a1c",
        "mistral-7b": "#ff7f00",
        "llama-3.1-8b": "#4daf4a",
        "llama-3.3-70b": "#377eb8",
    }

    for model in MAIN_MODELS:
        sub = df[df["model"] == model]
        # Use all strategies; group by gt_count
        grouped = sub.groupby("gt_count")["recall"].agg(["mean", "std"]).reset_index()
        # Only keep gt_count values with at least 4 observations
        grouped = grouped[grouped["gt_count"] >= 1]
        ax.plot(
            grouped["gt_count"],
            grouped["mean"],
            "o-",
            color=colors[model],
            label=MODEL_LABELS.get(model, model).replace("\n", " "),
            linewidth=1.8,
            markersize=6,
        )
        ax.fill_between(
            grouped["gt_count"],
            (grouped["mean"] - grouped["std"]).clip(0, 1),
            (grouped["mean"] + grouped["std"]).clip(0, 1),
            color=colors[model],
            alpha=0.12,
        )

    ax.set_xlabel("Number of Active Medications (Ground Truth)")
    ax.set_ylabel("Mean Recall (all strategies)")
    ax.set_title("Recall vs. Active Medication Count (Omission Analysis)")
    ax.set_ylim(-0.05, 1.1)
    ax.axhline(y=0.9, linestyle="--", color="grey", alpha=0.4, linewidth=1)
    ax.legend(loc="lower left", fontsize=9)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    _save(fig, "04_recall_vs_gt_count.png")


def fig05_recall_vs_history_span(df: pd.DataFrame) -> None:
    """Recall vs. history span — temporal reasoning analysis."""
    bins = [0, 5, 10, 15, 20, 25, 100]
    bin_labels = ["0–5", "5–10", "10–15", "15–20", "20–25", "25+"]

    df2 = df.copy()
    df2["span_bin"] = pd.cut(df2["history_span_years"], bins=bins, labels=bin_labels, right=False)

    # Best strategy per model
    best_strat: dict[str, str] = {}
    for model in MAIN_MODELS:
        sub = df2[df2["model"] == model].groupby("strategy")["recall"].mean()
        best_strat[model] = sub.idxmax()

    fig, ax = plt.subplots(figsize=(9, 5))

    colors = {
        "phi-3.5-mini": "#e41a1c",
        "mistral-7b": "#ff7f00",
        "llama-3.1-8b": "#4daf4a",
        "llama-3.3-70b": "#377eb8",
    }

    x = np.arange(len(bin_labels))
    width = 0.2
    offsets = np.linspace(-(len(MAIN_MODELS) - 1) / 2 * width, (len(MAIN_MODELS) - 1) / 2 * width, len(MAIN_MODELS))

    for k, model in enumerate(MAIN_MODELS):
        sub = df2[(df2["model"] == model) & (df2["strategy"] == best_strat[model])]
        grouped = sub.groupby("span_bin", observed=True)["recall"].mean().reindex(bin_labels)
        ax.bar(
            x + offsets[k],
            grouped.values,
            width=width,
            color=colors[model],
            label=f"{MODEL_LABELS.get(model, model).replace(chr(10), ' ')} ({STRATEGY_SHORT[best_strat[model]]})",
            alpha=0.85,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([f"{b} yrs" for b in bin_labels])
    ax.set_xlabel("Medication History Span")
    ax.set_ylabel("Mean Recall (best strategy per model)")
    ax.set_title("Recall vs. Medication History Span (Temporal Reasoning)")
    ax.set_ylim(0, 1.1)
    ax.legend(loc="lower left", fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    _save(fig, "05_recall_vs_history_span.png")


def fig06_precision_recall_scatter(agg: pd.DataFrame) -> None:
    """Precision vs. recall scatter — failure mode bias.

    Two-panel layout: left shows the full [0, 1] range (where BioMistral and the
    low-performing Phi-3.5 cluster live); right zooms into the high-performance
    region [0.85, 1.0] so the Llama-3.1 / Llama-3.3 strategy points are readable.
    """
    from adjustText import adjust_text

    fig, (ax_full, ax_zoom) = plt.subplots(
        1, 2, figsize=(14, 7), gridspec_kw={"width_ratios": [1.0, 1.0], "wspace": 0.22}
    )

    markers = {
        "phi-3.5-mini": "o",
        "mistral-7b": "s",
        "biomistral": "X",
        "llama-3.1-8b": "^",
        "llama-3.3-70b": "D",
    }
    mcolors = {
        "phi-3.5-mini": "#e41a1c",
        "mistral-7b": "#ff7f00",
        "biomistral": "#999999",
        "llama-3.1-8b": "#4daf4a",
        "llama-3.3-70b": "#377eb8",
    }

    ZOOM_XLIM = (0.85, 1.005)
    ZOOM_YLIM = (0.82, 1.01)

    texts_full = []

    for model in MODELS:
        for strat in STRATEGIES:
            row = agg[(agg["model"] == model) & (agg["strategy"] == strat)]
            if row.empty:
                continue
            r = row.iloc[0]
            prec = r["mean_precision"]
            rec = r["mean_recall"]
            label = f"{MODEL_LABELS_SHORT[model].replace(chr(10), ' ')}-{STRATEGY_SHORT[strat]}"

            if model == "biomistral":
                ax_full.scatter(prec, rec, marker=markers[model], color=mcolors[model],
                                s=90, alpha=0.7, zorder=4)
                continue

            # Full-view panel: plot every point, label only those OUTSIDE the zoom window.
            ax_full.scatter(prec, rec, marker=markers[model], color=mcolors[model],
                            s=90, alpha=0.85, zorder=4)
            in_zoom = (ZOOM_XLIM[0] <= prec <= ZOOM_XLIM[1]
                       and ZOOM_YLIM[0] <= rec <= ZOOM_YLIM[1])
            if not in_zoom:
                t = ax_full.text(prec, rec, label, fontsize=9, color=mcolors[model],
                                 zorder=5)
                texts_full.append(t)

            # Zoom panel: plot points inside window with a single-letter strategy
            # label offset slightly down-right. Colour + marker already identify the model.
            if in_zoom:
                ax_zoom.scatter(prec, rec, marker=markers[model], color=mcolors[model],
                                s=110, alpha=0.9, zorder=4)
                ax_zoom.annotate(
                    STRATEGY_SHORT[strat],
                    xy=(prec, rec),
                    xytext=(6, -10),
                    textcoords="offset points",
                    fontsize=10,
                    fontweight="bold",
                    color=mcolors[model],
                    zorder=5,
                )

    # BioMistral group annotation in full-view panel.
    ax_full.annotate(
        "BioMistral\n(all 4 strategies)\nF1 = 0.000",
        xy=(0.0, 0.0),
        xytext=(0.10, 0.18),
        fontsize=9.5,
        color=mcolors["biomistral"],
        arrowprops=dict(arrowstyle="->", color=mcolors["biomistral"], lw=1.0),
        ha="left",
        zorder=6,
    )

    # Equal-error diagonal and 0.95 reference lines on full-view panel.
    ax_full.plot([0, 1], [0, 1], linestyle=":", color="#aaaaaa", linewidth=1, zorder=1)
    ax_full.text(0.48, 0.45, "Precision = Recall", fontsize=9, color="#999999",
                 rotation=42, ha="left")
    ax_full.axvline(x=0.95, linestyle="--", color="grey", alpha=0.3, linewidth=1)
    ax_full.axhline(y=0.95, linestyle="--", color="grey", alpha=0.3, linewidth=1)

    # Rectangle showing the zoom region on the full view.
    from matplotlib.patches import Rectangle
    ax_full.add_patch(Rectangle(
        (ZOOM_XLIM[0], ZOOM_YLIM[0]),
        ZOOM_XLIM[1] - ZOOM_XLIM[0],
        ZOOM_YLIM[1] - ZOOM_YLIM[0],
        fill=False, edgecolor="#444444", linewidth=1.0, linestyle="--", zorder=2,
    ))
    ax_full.text(ZOOM_XLIM[0] - 0.01, ZOOM_YLIM[0] - 0.03, "zoom \u2192",
                 fontsize=9, color="#444444", ha="right", va="top")

    # Diagonal and grid on zoom panel.
    ax_zoom.plot([0, 1], [0, 1], linestyle=":", color="#aaaaaa", linewidth=1, zorder=1)

    # Repel labels only in the full-view panel (zoom uses manual letter offsets).
    adjust_text(
        texts_full, ax=ax_full,
        expand=(1.2, 1.3),
        arrowprops=dict(arrowstyle="-", color="#bbbbbb", lw=0.7),
        force_text=(0.3, 0.4),
        only_move={"points": "y", "texts": "xy"},
    )

    # Legend by model in the full-view panel.
    handles_full = [
        mpatches.Patch(color=mcolors[m], label=MODEL_LABELS.get(m, m).replace("\n", " "))
        for m in MODELS
    ]
    ax_full.legend(handles=handles_full, loc="lower right", fontsize=9, framealpha=0.92,
                   title="Model", title_fontsize=9)

    # Second legend on the zoom panel: strategy letters spelled out, plus marker shapes.
    from matplotlib.lines import Line2D
    strat_handles = [
        Line2D([0], [0], marker="", linestyle="", label=f"{STRATEGY_SHORT[s]} = {STRATEGY_LABELS[s]}")
        for s in STRATEGIES
    ]
    marker_handles = [
        Line2D([0], [0], marker=markers[m], color="w", markerfacecolor=mcolors[m],
               markersize=9, linestyle="", label=MODEL_LABELS_SHORT[m].replace("\n", " "))
        for m in MODELS if m != "biomistral"
    ]
    leg1 = ax_zoom.legend(handles=marker_handles, loc="lower right", fontsize=8.5,
                          framealpha=0.92, title="Model", title_fontsize=8.5)
    ax_zoom.add_artist(leg1)
    ax_zoom.legend(handles=strat_handles, loc="lower left", fontsize=8.5,
                   framealpha=0.92, title="Strategy letter", title_fontsize=8.5,
                   handletextpad=0, handlelength=0)

    # Full panel styling.
    ax_full.set_xlabel("Mean Precision", fontsize=11)
    ax_full.set_ylabel("Mean Recall", fontsize=11)
    ax_full.set_xlim(-0.05, 1.08)
    ax_full.set_ylim(-0.05, 1.08)
    ax_full.set_title("(a) Full range", fontsize=12, pad=8)
    ax_full.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax_full.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax_full.set_axisbelow(True)

    # Zoom panel styling.
    ax_zoom.set_xlim(*ZOOM_XLIM)
    ax_zoom.set_ylim(*ZOOM_YLIM)
    ax_zoom.set_xlabel("Mean Precision", fontsize=11)
    ax_zoom.set_ylabel("Mean Recall", fontsize=11)
    ax_zoom.set_title("(b) High-performance region", fontsize=12, pad=8)
    ax_zoom.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax_zoom.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax_zoom.set_axisbelow(True)

    fig.suptitle("Precision vs. Recall by Model and Strategy", fontsize=14, y=0.99)

    _save(fig, "06_precision_recall_scatter.png")


def fig06_precision_recall_scatter_paper(agg: pd.DataFrame) -> None:
    """Single-panel full-range precision vs. recall scatter for the paper.

    The two-panel (full + zoom) version lives in fig06_precision_recall_scatter.
    This paper variant shows only the full [0, 1] range so it fits a single
    two-column figure slot in the ACL template.
    """
    from adjustText import adjust_text

    fig, ax = plt.subplots(figsize=(8, 7))

    markers = {
        "phi-3.5-mini": "o",
        "mistral-7b": "s",
        "biomistral": "X",
        "llama-3.1-8b": "^",
        "llama-3.3-70b": "D",
    }
    mcolors = {
        "phi-3.5-mini": "#e41a1c",
        "mistral-7b": "#ff7f00",
        "biomistral": "#999999",
        "llama-3.1-8b": "#4daf4a",
        "llama-3.3-70b": "#377eb8",
    }

    texts = []

    for model in MODELS:
        for strat in STRATEGIES:
            row = agg[(agg["model"] == model) & (agg["strategy"] == strat)]
            if row.empty:
                continue
            r = row.iloc[0]
            prec = r["mean_precision"]
            rec = r["mean_recall"]
            label = f"{MODEL_LABELS_SHORT[model].replace(chr(10), ' ')}-{STRATEGY_SHORT[strat]}"

            if model == "biomistral":
                ax.scatter(prec, rec, marker=markers[model], color=mcolors[model],
                           s=90, alpha=0.7, zorder=4)
                continue

            ax.scatter(prec, rec, marker=markers[model], color=mcolors[model],
                       s=90, alpha=0.85, zorder=4)
            t = ax.text(prec, rec, label, fontsize=9, color=mcolors[model], zorder=5)
            texts.append(t)

    ax.annotate(
        "BioMistral\n(all 4 strategies)\nF1 = 0.000",
        xy=(0.0, 0.0),
        xytext=(0.10, 0.18),
        fontsize=9.5,
        color=mcolors["biomistral"],
        arrowprops=dict(arrowstyle="->", color=mcolors["biomistral"], lw=1.0),
        ha="left",
        zorder=6,
    )

    ax.plot([0, 1], [0, 1], linestyle=":", color="#aaaaaa", linewidth=1, zorder=1)
    ax.text(0.48, 0.45, "Precision = Recall", fontsize=9, color="#999999",
            rotation=42, ha="left")
    ax.axvline(x=0.95, linestyle="--", color="grey", alpha=0.3, linewidth=1)
    ax.axhline(y=0.95, linestyle="--", color="grey", alpha=0.3, linewidth=1)

    adjust_text(
        texts, ax=ax,
        expand=(1.2, 1.3),
        arrowprops=dict(arrowstyle="-", color="#bbbbbb", lw=0.7),
        force_text=(0.3, 0.4),
        only_move={"points": "y", "texts": "xy"},
    )

    handles = [
        mpatches.Patch(color=mcolors[m], label=MODEL_LABELS.get(m, m).replace("\n", " "))
        for m in MODELS
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.92,
              title="Model", title_fontsize=9)

    ax.set_xlabel("Mean Precision", fontsize=11)
    ax.set_ylabel("Mean Recall", fontsize=11)
    ax.set_xlim(-0.05, 1.08)
    ax.set_ylim(-0.05, 1.08)
    ax.set_title("Precision vs. Recall by Model and Strategy", fontsize=12, pad=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    _save(fig, "06_precision_recall_scatter_paper.png")


def fig07_f1_distribution(df: pd.DataFrame, agg: pd.DataFrame) -> None:
    """F1 distribution violin + box — per model, best strategy."""
    # Best strategy per model (by mean F1)
    best: dict[str, str] = {}
    for model in MODELS:
        sub = agg[agg["model"] == model]
        if sub.empty:
            continue
        best[model] = sub.loc[sub["mean_f1"].idxmax(), "strategy"]

    model_order = sorted(
        MODELS,
        key=lambda m: agg[(agg["model"] == m)]["mean_f1"].max() if not agg[agg["model"] == m].empty else 0,
    )

    data_by_model = [
        df[(df["model"] == m) & (df["strategy"] == best.get(m, "strategy_c"))]["f1"].values
        for m in model_order
    ]
    labels = [f"{MODEL_LABELS_SHORT[m].replace(chr(10), ' ')}\n({STRATEGY_SHORT[best.get(m, 'strategy_c')]})"
              for m in model_order]

    fig, ax = plt.subplots(figsize=(9, 5))

    vp = ax.violinplot(data_by_model, positions=range(len(model_order)),
                       showmedians=False, showextrema=False)
    model_colors_list = ["#999999", "#e41a1c", "#ff7f00", "#4daf4a", "#377eb8"]
    for i, (body, color) in enumerate(zip(vp["bodies"], model_colors_list)):
        body.set_facecolor(color)
        body.set_alpha(0.5)

    bp = ax.boxplot(data_by_model, positions=range(len(model_order)),
                    widths=0.12, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 2},
                    whiskerprops={"color": "grey"},
                    capprops={"color": "grey"},
                    flierprops={"marker": ".", "color": "grey", "markersize": 3})
    for patch, color in zip(bp["boxes"], model_colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    ax.set_xticks(range(len(model_order)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("F1 Score (per patient)")
    ax.set_ylim(-0.05, 1.08)
    ax.set_title("F1 Score Distribution by Model (Best Strategy)")
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    _save(fig, "07_f1_distribution.png")


def fig08_inference_vs_f1(agg: pd.DataFrame) -> None:
    """Inference time vs. F1 scatter — efficiency frontier."""
    from adjustText import adjust_text

    fig, ax = plt.subplots(figsize=(11, 7))

    mcolors = {
        "phi-3.5-mini": "#e41a1c",
        "mistral-7b": "#ff7f00",
        "biomistral": "#999999",
        "llama-3.1-8b": "#4daf4a",
        "llama-3.3-70b": "#377eb8",
    }
    markers = {
        "phi-3.5-mini": "o",
        "mistral-7b": "s",
        "biomistral": "X",
        "llama-3.1-8b": "^",
        "llama-3.3-70b": "D",
    }

    points = []  # (time, f1, label, model, strategy)
    texts = []
    bio_times = []

    for model in MODELS:
        for strat in STRATEGIES:
            row = agg[(agg["model"] == model) & (agg["strategy"] == strat)]
            if row.empty:
                continue
            r = row.iloc[0]
            t = r["mean_inference_s"]
            f = r["mean_f1"]

            if model == "biomistral":
                bio_times.append(t)
                ax.scatter(t, f, marker=markers[model], color=mcolors[model],
                           s=90, alpha=0.7, zorder=4)
                continue

            label = f"{MODEL_LABELS_SHORT[model].replace(chr(10), ' ')}-{STRATEGY_SHORT[strat]}"
            ax.scatter(t, f, marker=markers[model], color=mcolors[model],
                       s=90, alpha=0.85, zorder=4)
            txt = ax.text(t, f, label, fontsize=8.5, color=mcolors[model], zorder=5)
            texts.append(txt)
            points.append((t, f, label, model, strat))

    # Single BioMistral annotation at mean-time position on F1=0 line.
    if bio_times:
        bio_x = sum(bio_times) / len(bio_times)
        ax.annotate(
            "BioMistral\n(all 4 strategies)\nF1 = 0.000",
            xy=(bio_x, 0.0),
            xytext=(bio_x, 0.18),
            fontsize=9,
            color=mcolors["biomistral"],
            arrowprops=dict(arrowstyle="->", color=mcolors["biomistral"], lw=1.0),
            ha="center",
            zorder=6,
        )

    # Pareto frontier (max F1 for any given time budget).
    points_sorted = sorted(points, key=lambda p: p[0])
    pareto = []
    max_f1_so_far = -1.0
    for t, f, lbl, m, s in points_sorted:
        if f >= max_f1_so_far:
            pareto.append((t, f))
            max_f1_so_far = f
    if len(pareto) > 1:
        px, py = zip(*pareto)
        ax.step(px, py, where="post", linestyle="--", color="black", alpha=0.35,
                linewidth=1.2, label="Efficiency frontier", zorder=2)
        ax.legend(fontsize=9, loc="lower right", framealpha=0.92)

    adjust_text(
        texts,
        ax=ax,
        expand=(1.4, 1.6),
        arrowprops=dict(arrowstyle="-", color="#bbbbbb", lw=0.7),
        force_text=(0.6, 0.8),
    )

    ax.set_xscale("log")
    ax.set_xlabel("Mean Inference Time per Patient (seconds, log scale)", fontsize=11)
    ax.set_ylabel("Mean F1 Score", fontsize=11)
    ax.set_title("Inference Time vs. Accuracy (Efficiency Frontier)",
                 fontsize=13, pad=10)
    ax.set_ylim(-0.05, 1.15)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    _save(fig, "08_inference_vs_f1.png")


def fig09_patient_difficulty_heatmap(df: pd.DataFrame) -> None:
    """Per-patient F1 heatmap — patient difficulty across models."""
    # Best strategy per main model
    agg_sub = build_aggregate(df[df["model"].isin(MAIN_MODELS)])
    best: dict[str, str] = {}
    for model in MAIN_MODELS:
        sub = agg_sub[agg_sub["model"] == model]
        best[model] = sub.loc[sub["mean_f1"].idxmax(), "strategy"] if not sub.empty else "strategy_c"

    # Get patient order: sort by gt_count ascending
    patient_order = (
        df[["patient_id", "gt_count"]]
        .drop_duplicates("patient_id")
        .sort_values("gt_count")["patient_id"]
        .tolist()
    )

    matrix = np.zeros((len(MAIN_MODELS), len(patient_order)))
    for i, model in enumerate(MAIN_MODELS):
        sub = df[(df["model"] == model) & (df["strategy"] == best[model])].set_index("patient_id")["f1"]
        for j, pid in enumerate(patient_order):
            matrix[i, j] = sub.get(pid, np.nan)

    fig, ax = plt.subplots(figsize=(14, 3.5))
    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1, interpolation="nearest")

    ax.set_yticks(range(len(MAIN_MODELS)))
    ax.set_yticklabels([MODEL_LABELS_SHORT[m].replace("\n", " ") for m in MAIN_MODELS], fontsize=9)
    ax.set_xticks([])
    ax.set_xlabel(f"Patients (n={len(patient_order)}, sorted by active medication count →)")
    ax.set_title("Per-Patient F1 Heatmap (Best Strategy per Model, Sorted by GT Complexity)")

    cbar = fig.colorbar(im, ax=ax, orientation="vertical", fraction=0.015, pad=0.02)
    cbar.set_label("F1")

    _save(fig, "09_patient_difficulty_heatmap.png")


def fig10_biomistral_failure_modes() -> None:
    """BioMistral failure taxonomy — horizontal stacked bar chart."""
    strat_order = STRATEGIES
    categories = ["Garbled/incoherent", "Prompt continuation", "Empty response",
                  "Chatbot greeting", "Other"]
    cat_colors = ["#d73027", "#f46d43", "#fdae61", "#abd9e9", "#c0c0c0"]

    data = {}
    for strat in strat_order:
        d = BIOMISTRAL_FAILURES.get(strat, {})
        data[strat] = [d.get(cat, 0) for cat in categories]

    fig, ax = plt.subplots(figsize=(9, 4))
    y = np.arange(len(strat_order))
    lefts = np.zeros(len(strat_order))

    for k, (cat, color) in enumerate(zip(categories, cat_colors)):
        vals = np.array([data[s][k] for s in strat_order], dtype=float)
        bars = ax.barh(y, vals, left=lefts, color=color, label=cat, alpha=0.88)
        # Annotate non-zero values
        for i, (v, l) in enumerate(zip(vals, lefts)):
            if v >= 10:
                ax.text(l + v / 2, i, str(int(v)), ha="center", va="center", fontsize=9,
                        color="white", fontweight="bold")
        lefts += vals

    ax.set_yticks(y)
    ax.set_yticklabels([STRATEGY_LABELS[s] for s in strat_order])
    ax.set_xlabel("Number of Patients (out of 200)")
    ax.set_title("BioMistral-7B: Failure Mode Breakdown by Strategy")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_xlim(0, 215)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    _save(fig, "10_biomistral_failure_modes.png")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5: Analysis and visualisation")
    parser.add_argument("--plots", action="store_true", help="Generate figures only")
    parser.add_argument("--stats", action="store_true", help="Generate tables and tests only")
    args = parser.parse_args()
    run_all = not args.plots and not args.stats

    OUT_DIR.mkdir(exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = load_master_df()
    agg = build_aggregate(df)

    if run_all or args.stats:
        print("\nGenerating tables...")
        save_master_csv(df)
        save_aggregate_csv(agg)
        save_aggregate_markdown(agg)
        print("\nRunning statistical tests...")
        run_statistical_tests(df)
        print("\nAnalysing hard patients...")
        save_hard_patients(df)

    if run_all or args.plots:
        print("\nGenerating figures...")
        plt.style.use("seaborn-v0_8-whitegrid")
        fig01_heatmap(agg)
        fig02_bar_chart(agg)
        fig03_strategy_rank_by_size(agg)
        fig04_recall_vs_gt_count(df)
        fig05_recall_vs_history_span(df)
        fig06_precision_recall_scatter(agg)
        fig06_precision_recall_scatter_paper(agg)
        fig07_f1_distribution(df, agg)
        fig08_inference_vs_f1(agg)
        fig09_patient_difficulty_heatmap(df)
        fig10_biomistral_failure_modes()

    print("\nDone.")


if __name__ == "__main__":
    main()
