"""
generate_strategy_figure.py

Generates a 4-panel figure showing the same patient serialised in all 4 strategies.
Print-friendly: white background, black text, coloured header bars.
Output: paper/v1/figures/strategy_examples.png

Usage:
    python src/generate_strategy_figure.py
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from serialisers import serialise_a, serialise_b, serialise_c, serialise_d

GT_DIR = REPO_ROOT / "data" / "ground_truth"
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_PATH = REPO_ROOT / "paper" / "v1" / "figures" / "strategy_examples.png"

DEMO_PATIENT_PREFIX = "1b488cde"

STRATEGY_LABELS = [
    ("A", "Raw JSON", "#2563eb"),
    ("B", "Markdown Table", "#d97706"),
    ("C", "Clinical Narrative", "#16a34a"),
    ("D", "Chronological Timeline", "#dc2626"),
]

SERIALISE_FNS = {"a": serialise_a, "b": serialise_b, "c": serialise_c, "d": serialise_d}

# Shorter truncation so text is larger and more readable at column width
MAX_LINES = 30


def find_patient() -> tuple[str, dict]:
    for f in sorted(GT_DIR.glob("*.json")):
        gt = json.loads(f.read_text())
        if gt["patient_id"].startswith(DEMO_PATIENT_PREFIX):
            source = gt.get("source_file", "")
            raw_path = RAW_DIR / source
            if raw_path.exists():
                bundle = json.loads(raw_path.read_text())
                return gt["patient_id"], bundle
    raise FileNotFoundError(f"Patient {DEMO_PATIENT_PREFIX} not found")


def trim_to_lines(text: str, max_lines: int) -> str:
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + "\n...  [truncated]"


def make_figure(patient_id: str, bundle: dict) -> None:
    serialised = {key: SERIALISE_FNS[key](bundle) for key in ["a", "b", "c", "d"]}

    fig, axes = plt.subplots(1, 4, figsize=(22, 10))
    fig.patch.set_facecolor("white")

    for ax, (key, (label, name, color)) in zip(axes, zip(["a", "b", "c", "d"], STRATEGY_LABELS)):
        text = trim_to_lines(serialised[key], MAX_LINES)

        ax.set_facecolor("#fafafa")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Coloured header bar
        header_rect = mpatches.FancyBboxPatch(
            (0, 0.92), 1.0, 0.08,
            boxstyle="square,pad=0",
            facecolor=color,
            transform=ax.transAxes,
            clip_on=False,
            zorder=3,
        )
        ax.add_patch(header_rect)

        ax.text(
            0.5, 0.96,
            f"Strategy {label}  —  {name}",
            transform=ax.transAxes,
            fontsize=11,
            fontweight="bold",
            color="white",
            ha="center",
            va="center",
            fontfamily="sans-serif",
            zorder=4,
        )

        # Monospace content — black text on near-white background
        ax.text(
            0.03, 0.90,
            text,
            transform=ax.transAxes,
            fontsize=7.0,
            color="#111111",
            va="top",
            ha="left",
            fontfamily="monospace",
            wrap=False,
            clip_on=True,
            linespacing=1.35,
        )

        # Border matching header colour
        for spine_name in ["top", "bottom", "left", "right"]:
            ax.spines[spine_name].set_visible(False)
        border = mpatches.FancyBboxPatch(
            (0, 0), 1, 1,
            boxstyle="square,pad=0",
            linewidth=2,
            edgecolor=color,
            facecolor="none",
            transform=ax.transAxes,
            zorder=2,
        )
        ax.add_patch(border)

    pid_short = patient_id[:8]
    fig.suptitle(
        f"The same patient serialised in all four strategies  (Patient ID: {pid_short}...)",
        fontsize=13,
        fontweight="bold",
        color="#111111",
        fontfamily="sans-serif",
        y=1.01,
    )

    plt.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.02, wspace=0.06)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUT_PATH}")


def main() -> None:
    patient_id, bundle = find_patient()
    print(f"Using patient: {patient_id}")
    make_figure(patient_id, bundle)


if __name__ == "__main__":
    main()
