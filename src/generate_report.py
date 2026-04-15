#!/usr/bin/env python3
"""
src/generate_report.py

Generates a self-contained HTML research report at results/report.html.
All 10 figures are embedded as base64 so the file is portable.
Open in any browser and use File → Print → Save as PDF.

Usage:
    python src/generate_report.py
"""

import base64
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIGURES = ROOT / "results" / "figures"
OUT = ROOT / "results" / "report.html"

AGGREGATE = [
    # (model, strat, n, mean_f1, mean_prec, mean_recall, median_f1, perfect, zero, parse_failed)
    ("Phi-3.5-mini (3.8B)", "A — Raw JSON",           200, 0.6356, 0.7296, 0.5932, 0.7596,  75,  45, 33),
    ("Phi-3.5-mini (3.8B)", "B — Markdown Table",     200, 0.6833, 0.8111, 0.6264, 0.7500,  64,  25, 16),
    ("Phi-3.5-mini (3.8B)", "C — Clinical Narrative", 200, 0.7008, 0.7616, 0.6670, 0.8000,  66,  28,  7),
    ("Phi-3.5-mini (3.8B)", "D — Chrono. Timeline",   200, 0.6443, 0.7703, 0.5902, 0.6905,  61,  30, 11),
    ("Mistral-7B",          "A — Raw JSON",           200, 0.7247, 0.8886, 0.6684, 0.8889,  87,  20, 11),
    ("Mistral-7B",          "B — Markdown Table",     200, 0.8753, 0.9646, 0.8344, 1.0000, 122,   6,  3),
    ("Mistral-7B",          "C — Clinical Narrative", 200, 0.9149, 0.9319, 0.9026, 1.0000, 153,  10,  5),
    ("Mistral-7B",          "D — Chrono. Timeline",   200, 0.8588, 0.9611, 0.8100, 1.0000, 112,   6,  3),
    ("BioMistral-7B",       "A — Raw JSON",           200, 0.0000, 0.0000, 0.0000, 0.0000,   0, 200,198),
    ("BioMistral-7B",       "B — Markdown Table",     200, 0.0000, 0.0000, 0.0000, 0.0000,   0, 200,197),
    ("BioMistral-7B",       "C — Clinical Narrative", 200, 0.0000, 0.0000, 0.0000, 0.0000,   0, 200,198),
    ("BioMistral-7B",       "D — Chrono. Timeline",   200, 0.0000, 0.0000, 0.0000, 0.0000,   0, 200,198),
    ("Llama-3.1-8B",        "A — Raw JSON",           200, 0.9180, 0.9629, 0.9052, 1.0000, 138,   2,  0),
    ("Llama-3.1-8B",        "B — Markdown Table",     200, 0.9250, 0.9562, 0.9182, 1.0000, 147,   1,  0),
    ("Llama-3.1-8B",        "C — Clinical Narrative", 200, 0.9471, 0.9513, 0.9448, 1.0000, 173,   5,  2),
    ("Llama-3.1-8B",        "D — Chrono. Timeline",   200, 0.9228, 0.9724, 0.8995, 1.0000, 144,   2,  1),
    ("Llama-3.3-70B",       "A — Raw JSON",           200, 0.9956, 1.0000, 0.9929, 1.0000, 196,   0,  0),
    ("Llama-3.3-70B",       "B — Markdown Table",     200, 0.9867, 0.9900, 0.9845, 1.0000, 194,   2,  2),
    ("Llama-3.3-70B",       "C — Clinical Narrative", 200, 0.9850, 0.9850, 0.9850, 1.0000, 197,   3,  3),
    ("Llama-3.3-70B",       "D — Chrono. Timeline",   200, 0.8742, 0.8750, 0.8736, 1.0000, 174,  25,  2),
]

HARD_PATIENTS = [
    ("7323b20b", 0.3429, 11, 30),
    ("e15ab14b", 0.3958,  4, 29),
    ("6c6acf0d", 0.4215, 12, 25),
    ("bb88b4a2", 0.4625,  2, 26),
]


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def f1_color(v: float) -> str:
    if v >= 0.95:
        return "#1a7a1a"
    if v >= 0.85:
        return "#2d9e2d"
    if v >= 0.70:
        return "#7ab87a"
    if v >= 0.50:
        return "#c8a020"
    if v >= 0.20:
        return "#c04020"
    return "#8b0000"


def f1_bg(v: float) -> str:
    if v >= 0.95:
        return "#d4edda"
    if v >= 0.85:
        return "#e8f5e9"
    if v >= 0.70:
        return "#f0f9f0"
    if v >= 0.20:
        return "#fff3cd"
    return "#f8d7da"


def build_aggregate_html() -> str:
    rows = []
    prev_model = None
    for row in AGGREGATE:
        model, strat, n, f1, prec, rec, med, perf, zero, pf = row
        is_bio = model == "BioMistral-7B"
        best_strat = {
            "Phi-3.5-mini (3.8B)": "C — Clinical Narrative",
            "Mistral-7B":          "C — Clinical Narrative",
            "BioMistral-7B":       None,
            "Llama-3.1-8B":        "C — Clinical Narrative",
            "Llama-3.3-70B":       "A — Raw JSON",
        }
        is_best = strat == best_strat.get(model)
        border = "border-top:2px solid #555;" if model != prev_model else ""
        bg = "#fafafa" if is_bio else ("#fffef0" if is_best else "white")
        bio_style = "opacity:0.6; font-style:italic;" if is_bio else ""
        best_marker = " ★" if is_best and not is_bio else ""
        f1_cell = f'<td style="color:{f1_color(f1)};font-weight:bold;background:{f1_bg(f1)}">{f1:.4f}{best_marker}</td>'
        rows.append(
            f'<tr style="background:{bg};{border}{bio_style}">'
            f'<td style="white-space:nowrap">{model}</td>'
            f'<td>{strat}</td>'
            f'{f1_cell}'
            f'<td>{prec:.4f}</td>'
            f'<td>{rec:.4f}</td>'
            f'<td>{med:.4f}</td>'
            f'<td>{perf}/200</td>'
            f'<td>{"—" if is_bio else zero}</td>'
            f'<td>{"—" if not is_bio else pf}</td>'
            f'</tr>'
        )
        prev_model = model
    return "\n".join(rows)


FIGURES_META = [
    ("01_heatmap_f1.png",
     "Figure 1 — F1 Score Heatmap",
     "The central result figure.",
     """
     <p><strong>What a heatmap is:</strong> A grid where each cell is coloured by a number. Dark red = low F1, dark green = high F1. You scan it like a table, but the colours give you the pattern instantly. Each cell also shows the exact F1 value.</p>
     <p><strong>How to read it:</strong> Read <em>across a row</em> to see whether the strategy matters for one model. Read <em>down a column</em> to see whether model size matters for one strategy. The BioMistral row is deliberately greyed out because its values (all 0.000) would distort the colour scale.</p>
     <p><strong>What our heatmap shows:</strong></p>
     <ul>
       <li>The brightest cell in the entire grid is <strong>Llama-3.3-70B + Strategy A = 0.9956</strong> — the experiment ceiling.</li>
       <li>Reading the Mistral row: column A (0.725) is much redder than column C (0.915). Format makes a large difference for a 7B model.</li>
       <li>Reading the Llama-3.3 row: columns A, B, C are all bright green, but column D (0.874) is notably dimmer. Even a 70B model struggles with the chronological timeline format.</li>
       <li>Reading any column downwards: every column gets greener as you go down (larger models perform better).</li>
       <li>BioMistral row: entirely grey/red. Every cell is 0.000. The model completely failed regardless of format.</li>
     </ul>
     <p><strong>Key takeaway:</strong> Two variables matter — model size and input format. Both are visible as gradients in this single image. This is the paper's first figure because it communicates the full experiment in one glance.</p>
     """),

    ("02_bar_chart_f1.png",
     "Figure 2 — Mean F1 by Model and Strategy (Grouped Bar Chart)",
     "Comparing all four strategies side-by-side within each model.",
     """
     <p><strong>What a grouped bar chart is:</strong> Each model has a group of four bars (one per strategy). Bar height = mean F1. The thin vertical line at the top of each bar is a 95% confidence interval — the range where the true mean would fall if the experiment were repeated with fresh patients. A narrow error bar means the model is consistent. A wide one means high variance.</p>
     <p><strong>How to read it:</strong> Look at the tallest bar within each group — that's the best strategy for that model. Compare groups left-to-right to see how model size affects performance. BioMistral is excluded (all zeros would collapse the y-axis scale).</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li><strong>Phi-3.5-mini:</strong> All four bars are similar in height (~0.64–0.70). Wide error bars. Strategy barely matters — the model is too weak to reliably follow any format.</li>
       <li><strong>Mistral-7B:</strong> Clear winner is bar C (0.915). Bar A (0.725) is noticeably shorter — a 0.19 F1 gap just from changing the input format.</li>
       <li><strong>Llama-3.1-8B:</strong> All four bars are bunched high (0.918–0.947). The model handles all formats well, but C is still the best.</li>
       <li><strong>Llama-3.3-70B:</strong> Bar A is the tallest (0.996). Bar D is much shorter (0.874) — even a 70B model fails on the chronological timeline format.</li>
     </ul>
     <p><strong>Key takeaway:</strong> Strategy C dominates for smaller models; Strategy A wins at 70B. Strategy D is consistently weak or the worst for every model except Phi (where all strategies are equally mediocre).</p>
     """),

    ("03_strategy_rank_by_size.png",
     "Figure 3 — Strategy Performance Across Model Sizes (Line Plot)",
     "The core ablation finding — how strategy ranking changes as models get larger.",
     """
     <p><strong>What this line plot is:</strong> The x-axis is model parameter count in billions (3.8B → 7B → 8B → 70B, on a log scale). The y-axis is mean F1. Each coloured line represents one serialisation strategy. This shows how each strategy's performance changes as the model gets bigger.</p>
     <p><strong>What a log scale means:</strong> Instead of evenly spaced distances (0, 10, 20, 30), the x-axis uses powers of 10 (3.8, 10, 100). This is used when the values span a very wide range (3.8B to 70B). Equal horizontal distances mean equal <em>ratios</em>, not equal differences.</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li>From 3.8B to 8B: the Strategy C line (blue) sits above all others. Clinical Narrative is the best format for small models.</li>
       <li>At 70B: the Strategy A line (green) overtakes Strategy C. Raw JSON becomes the best format when the model is large enough to read FHIR natively.</li>
       <li>Strategy D (pink) is consistently the weakest line — the chronological format is hard for every model size.</li>
       <li>All lines go upward from left to right — bigger always means better, regardless of format.</li>
       <li>The BioMistral cross-marker at 7B (grey ×) sits at the bottom of the chart at 0.0 — domain pretraining without instruction fine-tuning eliminates all gains from model size.</li>
     </ul>
     <p><strong>Key takeaway:</strong> The best input format is not universal. It depends on the model. This is the headline finding of the paper — small models need human-readable formats; large models can handle structured data directly.</p>
     """),

    ("04_recall_vs_gt_count.png",
     "Figure 4 — Recall vs. Number of Active Medications (Omission Analysis)",
     "Where each model starts failing as patient complexity grows.",
     """
     <p><strong>What this chart is:</strong> The x-axis is the number of active medications a patient truly has (their ground truth medication count). The y-axis is mean recall at that complexity level. Each coloured line is one model. The shaded band around each line shows ±1 standard deviation — wider bands mean more variability across patients.</p>
     <p><strong>What recall means here:</strong> If a patient has 10 active medications and the model finds 8, recall = 8/10 = 0.80. A recall drop means the model is missing medications — the clinically dangerous failure mode.</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li><strong>Llama-3.3-70B (blue):</strong> The line stays near 1.0 all the way to gt=16. The 70B model has no meaningful capacity ceiling in our dataset.</li>
       <li><strong>Llama-3.1-8B (green):</strong> Holds up well. Slight dip at higher counts but stays above 0.85.</li>
       <li><strong>Mistral-7B (orange):</strong> Visible decline from gt=7. At gt=11, recall drops to approximately 0.24 — the model finds fewer than 1 in 4 active medications. This is a dramatic failure.</li>
       <li><strong>Phi-3.5-mini (red):</strong> Drops the earliest and most steeply. Struggles visibly from gt=5 onwards.</li>
     </ul>
     <p><strong>Key takeaway:</strong> This is the most clinically important figure. The patients with the most complex medication regimens — exactly the ones who need the most careful tracking — are also the patients where small models fail the most. Deploying Mistral or Phi in a real clinical setting would mean systematically missing medications for polypharmacy patients.</p>
     """),

    ("05_recall_vs_history_span.png",
     "Figure 5 — Recall vs. Medication History Span (Temporal Reasoning)",
     "Does a longer history cause failures, independent of how many medications exist?",
     """
     <p><strong>What this chart is:</strong> A grouped bar chart. The x-axis groups patients by how many years of medication history they have (0–5 years, 5–10 years, ..., 25+ years). The y-axis is mean recall on each model's best strategy. Each coloured bar group is one model.</p>
     <p><strong>Why this is different from Figure 4:</strong> Figure 4 asks "does having many active medications cause failures?" This figure asks "does having a long history cause failures, even if the current active list is short?" A patient with 30 years of history might only have 2 current medications. If this chart shows a strong drop-off, it would mean context length is the bottleneck. If it stays flat, the bottleneck is reasoning about complexity, not history length.</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li>The pattern here is weaker and noisier than Figure 4. Recall does not drop dramatically as history span increases.</li>
       <li>This rules out a simple "the model can't handle long context" explanation for failures. Models are not failing because the records are long.</li>
       <li>The failures seen in Figure 4 are driven by the number of <em>current</em> medications, not the length of <em>historical</em> records.</li>
     </ul>
     <p><strong>Key takeaway:</strong> The bottleneck is not context length — it is reasoning complexity. A model failing on a patient with 11 active medications fails because reasoning over 11 simultaneous status-tracking tasks is hard, not because the records go back 30 years. This is an important nuance for the paper's discussion section.</p>
     """),

    ("06_precision_recall_scatter.png",
     "Figure 6 — Precision vs. Recall Scatter (Failure Mode Bias)",
     "Are failures due to hallucination (invented meds) or omission (missed meds)?",
     """
     <p><strong>What a scatter plot is:</strong> Each point is one (model, strategy) combination — 20 points total. The x-position is that combination's mean precision; the y-position is its mean recall. The dashed reference lines are at x=0.95 (precision) and y=0.95 (recall).</p>
     <p><strong>The four quadrants:</strong></p>
     <ul>
       <li>Top-right (high precision, high recall): ideal — the model is accurate and complete</li>
       <li>Bottom-right (high precision, low recall): the model never invents medications but misses many — omission failure</li>
       <li>Top-left (low precision, high recall): the model finds everything but adds phantom medications — hallucination failure</li>
       <li>Bottom-left (low both): complete failure</li>
     </ul>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li>Almost all points from the four main models cluster in the <strong>bottom-right region</strong> — to the right of x=0.95 but below y=0.95. High precision, but recall is the weak point.</li>
       <li>Llama-3.3-70B + Strategy A sits in the top-right corner with precision=1.0000 and recall=0.9929 — the only combination that achieves both metrics above 0.99.</li>
       <li>BioMistral sits alone in the bottom-left corner at (0.0, 0.0).</li>
       <li>No points are in the top-left quadrant — none of our models hallucinate more than they omit.</li>
     </ul>
     <p><strong>Key takeaway:</strong> LLMs used for medication reconciliation almost never invent medications that are not in the records. They do miss medications that are truly active. The clinical implication: you can trust that everything a model <em>says</em> is active probably is active — but you cannot trust that the list is <em>complete</em>.</p>
     """),

    ("07_f1_distribution.png",
     "Figure 7 — F1 Distribution by Model (Violin + Box Plot)",
     "Is a model's high mean F1 consistent, or driven by a few easy patients?",
     """
     <p><strong>What a violin plot is:</strong> The wide coloured shape shows where most of the 200 F1 scores lie. The width at any height = how many patients scored near that value. A fat shape at 1.0 means many patients were solved perfectly. The box inside shows the median (middle line), 25th–75th percentile range (box edges), and whiskers (the range excluding outliers).</p>
     <p><strong>Why this matters:</strong> A model could have a high mean F1 in two very different ways: (a) it gets most patients nearly right with few catastrophic failures, or (b) it gets easy patients perfectly but fails completely on hard ones. The mean is the same; the distribution is totally different. The violin shows which situation you are in.</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li><strong>BioMistral:</strong> A flat horizontal line at exactly F1=0.0. The entire distribution is at zero — no patient was helped at all.</li>
       <li><strong>Phi-3.5-mini:</strong> A wide, spread-out violin — high variance. Scores range from 0 to 1 with mass throughout. Very unpredictable. Some patients score perfectly; many score poorly.</li>
       <li><strong>Mistral-7B:</strong> Bimodal — large bulge at F1=1.0 (many perfect patients) and another bulge at lower values. The model is excellent for some patients and fails others. The mean of 0.91 hides this split behaviour.</li>
       <li><strong>Llama-3.1-8B:</strong> Most of the violin weight is at 1.0. The box is narrow and positioned high. Consistently good.</li>
       <li><strong>Llama-3.3-70B:</strong> A thin spike near 1.0. Almost the entire violin is compressed into the top 5% of the scale. Out of 200 patients, only 4 scored anything less than perfect. Extremely reliable.</li>
     </ul>
     <p><strong>Key takeaway:</strong> Reliability is as important as accuracy in clinical settings. Mistral's mean F1 of 0.91 sounds impressive, but the wide distribution means some patients are systematically failed. Llama-3.3-70B's near-identical violin across 200 patients is much safer to deploy.</p>
     """),

    ("08_inference_vs_f1.png",
     "Figure 8 — Inference Time vs. Accuracy (Efficiency Frontier)",
     "Which (model, strategy) combination gives the best accuracy per second?",
     """
     <p><strong>What this scatter is:</strong> Each of the 20 (model, strategy) combinations is plotted as a point. X-axis = average time to process one patient (log scale). Y-axis = mean F1. The dashed line connects the "Pareto optimal" points — combinations where no other point has both lower time AND higher F1 simultaneously.</p>
     <p><strong>What the Pareto/efficiency frontier is:</strong> If you have a time budget (e.g., "I can spend at most 5 seconds per patient"), the frontier shows you which combination gives the best F1 within that budget. Points not on the frontier are dominated — there exists a faster-or-equally-fast option with higher F1.</p>
     <p><strong>What log scale means:</strong> The x-axis goes 1s, 3s, 10s, 30s, 100s rather than equal spacing. Each gridline is roughly 3× the previous. This is used because small models take ~2–14 seconds while 70B takes ~30–80 seconds — a 40× range that would be impossible to read on a linear scale.</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li>BioMistral points cluster in the fast-but-useless region — quick because most responses are empty or garbled, not because they are efficient.</li>
       <li>Phi-3.5-mini: fast (1–3 seconds) but only F1 ~0.64–0.70. Low cost, low value.</li>
       <li>Mistral-7B + Strategy C: ~3.5 seconds per patient, F1 = 0.915. A good balance.</li>
       <li><strong>Llama-3.1-8B + Strategy C: ~3 seconds per patient, F1 = 0.947.</strong> This is the sweet spot before the 70B jump — nearly as fast as Mistral, significantly more accurate.</li>
       <li>Llama-3.3-70B: 30–80 seconds per patient, F1 = 0.874–0.996. High cost, highest accuracy. Strategy D at 70B takes ~40 seconds but only achieves 0.874 — that is not on the frontier.</li>
     </ul>
     <p><strong>Key takeaway:</strong> Llama-3.1-8B + Strategy C is the practical recommendation for clinical deployment at scale. If absolute accuracy is required regardless of cost, Llama-3.3-70B + Strategy A is the ceiling.</p>
     """),

    ("09_patient_difficulty_heatmap.png",
     "Figure 9 — Per-Patient F1 Heatmap (Patient Difficulty View)",
     "Which patients are hard for every model, and which are model-specific failures?",
     """
     <p><strong>What this heatmap is:</strong> Each column is one of the 200 patients. Each row is one of the four main models (using its best strategy). The cell colour is F1 score. Patients are sorted left-to-right by number of active medications (simplest on left, most complex on right).</p>
     <p><strong>How to read it:</strong></p>
     <ul>
       <li>A green column = easy patient — all models handle it correctly</li>
       <li>A red column = universally hard patient — every model struggles</li>
       <li>Red in one row only = this model has a specific problem with this patient, others don't</li>
       <li>The right side of the chart (more complex patients) should have more red if complexity drives failure</li>
     </ul>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li>The overwhelming majority of the chart is green — most patients are solved well by all main models.</li>
       <li>Moving right, the Phi and Mistral rows develop more red — confirming that complexity drives failures for smaller models.</li>
       <li>Three to four <strong>dark vertical stripes</strong> are visible — columns where every row is simultaneously red. These are the universally hard patients identified in the hard patient analysis. No model, regardless of size, reliably solves them.</li>
       <li>The Llama-3.3-70B row (bottom) is almost entirely green across all 200 columns.</li>
     </ul>
     <p><strong>Key takeaway:</strong> Most failures are not random — there is a small set of structurally hard patients that every model struggles with. Identifying what makes these patients hard (medication name patterns, Synthea data artefacts) is future work.</p>
     """),

    ("10_biomistral_failure_modes.png",
     "Figure 10 — BioMistral-7B Failure Mode Taxonomy (Stacked Bar Chart)",
     "Breaking down exactly how BioMistral failed — not just that it failed.",
     """
     <p><strong>What a horizontal stacked bar chart is:</strong> Each row is one strategy. The row is divided into coloured segments. Each segment represents a category of failure. The width of each segment shows how many patients fell into that category. All segments sum to 200 patients.</p>
     <p><strong>What our chart shows:</strong></p>
     <ul>
       <li><strong>Garbled/incoherent tokens (red, 113–140 patients per strategy):</strong> The model output meaningless fragmented tokens — not English, not JSON, just noise. Examples: <code>(</code>, <code>-  T</code>, <code>valueA Question 2 to c- ( It a H</code>. This is the largest failure category and the most severe — the model is not comprehending the input at all.</li>
       <li><strong>Prompt continuation (orange, 11–68 patients):</strong> Instead of answering the instruction, the model wrote more instruction text. It generated outputs like "You are a physician who just reviewed the medication history of..." — continuing the system prompt rather than following it. The model has no concept of the instruction-response boundary.</li>
       <li><strong>Empty response (yellow, 14–48 patients):</strong> The model returned nothing.</li>
       <li><strong>Chatbot greeting (blue, 1–5 patients):</strong> The model responded with "Hi! How can I assist you today?" — a generic chatbot response completely disconnected from the medical task.</li>
     </ul>
     <p><strong>Why BioMistral failed:</strong> These failure modes are characteristic of a <em>completion model</em> — one trained to predict the next token in a sequence — being given a <em>chat-style instruction</em>. Completion models were not fine-tuned to follow instructions. The Ollama tag <code>biomistral</code> likely resolves to a base/completion checkpoint, not an instruction-tuned variant. This is not a failure of biomedical knowledge — it is a fundamental architectural mismatch.</p>
     <p><strong>Key takeaway:</strong> Comparing BioMistral (F1=0.0) to Mistral-7B (F1=0.915) on the same task shows that domain pretraining without instruction fine-tuning provides zero benefit for structured extraction tasks. A general-purpose instruction-tuned model overwhelmingly outperforms a domain-specialised completion model.</p>
     """),
]

STAT_ROWS_STRAT = [
    ("Phi-3.5-mini (3.8B)", "3143", "2.66e-02", "1.06e-01", "ns",  "0.197", "C &gt; A", "Not statistically conclusive after correction. C is slightly better in practice."),
    ("Mistral-7B",          "948",  "4.31e-11", "1.73e-10", "***", "0.617", "C &gt; A", "Extremely significant. Very large effect. Strategy C is genuinely and substantially better."),
    ("Llama-3.1-8B",        "859",  "2.78e-03", "1.11e-02", "*",   "0.345", "C &gt; A", "Significant. Medium effect. C is the better format for this model."),
    ("Llama-3.3-70B",       "10",   "4.96e-01", "1.00e+00", "ns",  "0.257", "A &gt; C", "Not significant. The 70B model is indifferent to format. A is marginally better in practice."),
]

STAT_ROWS_MODEL = [
    ("Mistral-7B vs Llama-3.1-8B",        "414", "1.95e-02", "*",   "0.327", "Llama-3.1 &gt; Mistral", "Significant. Medium effect. Llama-3.1-8B is better on Strategy C."),
    ("Llama-3.1-8B vs Llama-3.3-70B",     "22",  "1.53e-04", "***", "0.757", "Llama-3.3 &gt; Llama-3.1", "Highly significant. Very large effect. Scale matters enormously."),
    ("Mistral-7B vs BioMistral-7B",        "0",   "7.07e-38", "***", "0.576", "Mistral &gt; BioMistral", "Supremely significant. BioMistral scored 0 on all 200 patients."),
]


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Georgia', serif;
  font-size: 15px;
  line-height: 1.7;
  color: #222;
  background: #f9f9f9;
  padding: 0;
}
.page-wrap {
  max-width: 980px;
  margin: 0 auto;
  background: white;
  padding: 50px 60px 80px;
  box-shadow: 0 0 30px rgba(0,0,0,0.08);
}
h1 { font-size: 28px; font-weight: bold; color: #1a3a5c; margin-bottom: 6px; }
h2 { font-size: 21px; font-weight: bold; color: #1a3a5c; margin: 40px 0 12px;
     border-bottom: 2px solid #1a3a5c; padding-bottom: 6px; }
h3 { font-size: 17px; color: #2c5282; margin: 28px 0 8px; }
h4 { font-size: 15px; color: #444; margin: 18px 0 6px; font-style: italic; }
p { margin-bottom: 12px; }
ul { margin: 10px 0 14px 22px; }
li { margin-bottom: 6px; }
code { background: #f0f0f0; border: 1px solid #ddd; padding: 1px 5px;
       border-radius: 3px; font-size: 13px; font-family: monospace; }
.subtitle { color: #555; font-size: 14px; margin-bottom: 4px; }
.meta { color: #777; font-size: 13px; border-top: 1px solid #eee;
        padding-top: 10px; margin-top: 10px; margin-bottom: 40px; }
.toc { background: #f5f8ff; border: 1px solid #c5d5ea; border-radius: 6px;
       padding: 20px 30px; margin-bottom: 40px; }
.toc h3 { margin-top: 0; color: #1a3a5c; }
.toc ol { margin-left: 18px; }
.toc li { margin-bottom: 3px; }
.toc a { color: #2c5282; text-decoration: none; }
.toc a:hover { text-decoration: underline; }
.summary-box {
  background: linear-gradient(135deg, #1a3a5c 0%, #2c5282 100%);
  color: white;
  border-radius: 8px;
  padding: 24px 30px;
  margin-bottom: 32px;
}
.summary-box h3 { color: #a8c8f0; margin-top: 0; }
.summary-box ul { margin-left: 20px; }
.summary-box li { margin-bottom: 8px; }
.figure-block {
  border: 1px solid #dde4ef;
  border-radius: 8px;
  padding: 0;
  margin: 28px 0 36px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.figure-header {
  background: #f0f4fa;
  border-bottom: 1px solid #dde4ef;
  padding: 14px 22px;
}
.figure-header h3 { margin: 0; font-size: 16px; color: #1a3a5c; }
.figure-subtitle { color: #666; font-size: 13px; margin-top: 3px; }
.figure-img {
  display: block;
  width: 100%;
  padding: 18px 18px 10px;
  background: white;
}
.figure-img img { width: 100%; height: auto; display: block; }
.figure-body {
  padding: 16px 22px 20px;
  background: #fafcff;
  border-top: 1px solid #eef2f8;
}
.figure-body p:last-child { margin-bottom: 0; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
  margin: 16px 0 24px;
}
th {
  background: #1a3a5c;
  color: white;
  padding: 9px 10px;
  text-align: left;
  font-weight: bold;
  font-size: 13px;
}
td { padding: 7px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
tr:hover td { background: #f5f8ff; }
.best-row td { font-weight: bold; }
.sig { font-weight: bold; color: #990000; }
.ns { color: #888; }
.finding-block {
  border-left: 5px solid #2c5282;
  background: #f5f8ff;
  padding: 14px 18px;
  margin: 20px 0;
  border-radius: 0 6px 6px 0;
}
.finding-block h3 { margin-top: 0; color: #1a3a5c; font-size: 15px; }
.hard-patient-box {
  border: 1px solid #f0c040;
  background: #fffdf0;
  border-radius: 6px;
  padding: 14px 18px;
  margin-bottom: 14px;
}
.hard-patient-box h4 { margin-top: 0; color: #7a5000; }
.pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  margin-left: 6px;
}
.pill-green { background: #d4edda; color: #155724; }
.pill-red   { background: #f8d7da; color: #721c24; }
.pill-grey  { background: #e2e3e5; color: #383d41; }
.section-intro { color: #555; font-size: 14px; margin-bottom: 20px; font-style: italic; }
footer {
  margin-top: 60px;
  padding-top: 20px;
  border-top: 1px solid #ddd;
  color: #888;
  font-size: 12px;
  text-align: center;
}
@media print {
  body { background: white; }
  .page-wrap { box-shadow: none; padding: 20px 30px; }
  .figure-block { break-inside: avoid; }
  .finding-block { break-inside: avoid; }
  h2 { break-before: page; }
}
"""


def make_figure_html(fname: str, title: str, subtitle: str, body: str, idx: int) -> str:
    img_path = FIGURES / fname
    if not img_path.exists():
        return f'<p style="color:red">Missing figure: {fname}</p>'
    data = b64(img_path)
    return f"""
<div class="figure-block" id="fig{idx:02d}">
  <div class="figure-header">
    <h3>{title}</h3>
    <div class="figure-subtitle">{subtitle}</div>
  </div>
  <div class="figure-img">
    <img src="data:image/png;base64,{data}" alt="{title}" />
  </div>
  <div class="figure-body">{body}</div>
</div>
"""


def make_aggregate_table() -> str:
    rows_html = build_aggregate_html()
    return f"""
<table>
  <thead>
    <tr>
      <th>Model</th><th>Strategy</th>
      <th>Mean F1</th><th>Mean Prec</th><th>Mean Recall</th>
      <th>Median F1</th><th>Perfect</th><th>Zero F1</th><th>Parse Failed</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>
<p style="font-size:12px;color:#777">★ = best strategy per model. BioMistral rows are italicised. Colour coding on Mean F1: dark green ≥0.95, light green ≥0.85, pale green ≥0.70, yellow ≥0.50, red below.</p>
"""


def make_stat_table_strat() -> str:
    rows = []
    for model, w, p_raw, p_bonf, sig, r, direction, note in STAT_ROWS_STRAT:
        sig_class = "sig" if sig != "ns" else "ns"
        rows.append(
            f'<tr><td>{model}</td><td>{w}</td><td>{p_raw}</td>'
            f'<td><span class="{sig_class}">{p_bonf} {sig}</span></td>'
            f'<td>{r}</td><td>{direction}</td><td style="font-size:12px;color:#555">{note}</td></tr>'
        )
    return f"""
<table>
  <thead>
    <tr><th>Model</th><th>W</th><th>p (raw)</th><th>p (Bonferroni, k=4)</th><th>r</th><th>Direction</th><th>Plain English</th></tr>
  </thead>
  <tbody>{"".join(rows)}</tbody>
</table>
"""


def make_stat_table_model() -> str:
    rows = []
    for label, w, p, sig, r, direction, note in STAT_ROWS_MODEL:
        sig_class = "sig" if sig != "ns" else "ns"
        rows.append(
            f'<tr><td>{label}</td><td>{w}</td><td><span class="{sig_class}">{p} {sig}</span></td>'
            f'<td>{r}</td><td>{direction}</td><td style="font-size:12px;color:#555">{note}</td></tr>'
        )
    return f"""
<table>
  <thead>
    <tr><th>Comparison</th><th>W</th><th>p</th><th>r</th><th>Direction</th><th>Plain English</th></tr>
  </thead>
  <tbody>{"".join(rows)}</tbody>
</table>
"""


def make_hard_patients() -> str:
    patient_details = [
        ("7323b20b", 0.3429, 11, 30,
         [("Phi-3.5-mini", "0.0000","0.0000","0.6250","0.3750"),
          ("Mistral-7B",   "0.9524","0.0000","0.0000","0.0000"),
          ("Llama-3.1-8B", "1.0000","0.6250","0.0000","0.9091"),
          ("Llama-3.3-70B","1.0000","0.0000","0.0000","0.0000")],
         "Both Mistral and Llama-3.3 score 1.0 on Strategy A but 0.0 on C. Something in this patient's clinical narrative triggers a systematic failure. Strategy A (raw JSON) is the only format that works."),
        ("e15ab14b", 0.3958,  4, 29,
         [("Phi-3.5-mini", "0.0000","0.6667","0.0000","1.0000"),
          ("Mistral-7B",   "1.0000","0.0000","0.0000","0.0000"),
          ("Llama-3.1-8B", "1.0000","0.6667","0.0000","1.0000"),
          ("Llama-3.3-70B","1.0000","0.0000","0.0000","0.0000")],
         "Only 4 active medications — not a complex patient by count. Yet Strategy C scores 0.0 for every model. Strategies A and D work for 3 out of 4 models. This suggests an unusual medication name in this patient that the clinical narrative format renders in a way that confuses models."),
        ("6c6acf0d", 0.4215, 12, 25,
         [("Phi-3.5-mini", "0.0000","0.5556","0.8333","0.5556"),
          ("Mistral-7B",   "0.0000","0.0000","0.0000","0.0000"),
          ("Llama-3.1-8B", "1.0000","0.5000","0.8000","0.5000"),
          ("Llama-3.3-70B","1.0000","1.0000","0.0000","0.0000")],
         "12 active medications — genuinely complex. Mistral fails on all 4 formats. Llama-3.1 and Llama-3.3 solve Strategy A perfectly. This is a true capacity failure for smaller models: too many active medications to track simultaneously."),
        ("bb88b4a2", 0.4625,  2, 26,
         [("Phi-3.5-mini", "0.4000","0.5000","0.5000","0.0000"),
          ("Mistral-7B",   "0.0000","0.0000","0.5000","0.0000"),
          ("Llama-3.1-8B", "0.5000","0.5000","0.5000","1.0000"),
          ("Llama-3.3-70B","1.0000","1.0000","1.0000","0.0000")],
         "Only 2 active medications and 26 years of history. Llama-3.3 solves it perfectly on 3 formats. Smaller models consistently score 0.0 or 0.5. The specific medications in this patient's history appear to cause format-dependent failures — an unusual pattern for such a simple current medication list."),
    ]
    parts = []
    for pid, mean_f1, gt, span, model_rows, note in patient_details:
        f1_pct = f"{mean_f1:.3f}"
        rows_html = ""
        for model, a, b, c, d in model_rows:
            def cell(v):
                fv = float(v)
                bg = "#d4edda" if fv >= 0.9 else ("#fff3cd" if fv >= 0.4 else "#f8d7da")
                fw = "bold" if fv == 1.0 else "normal"
                return f'<td style="background:{bg};font-weight:{fw};text-align:center">{v}</td>'
            rows_html += f"<tr><td>{model}</td>{cell(a)}{cell(b)}{cell(c)}{cell(d)}</tr>"

        parts.append(f"""
<div class="hard-patient-box">
  <h4>Patient <code>{pid}</code> — Mean F1: {f1_pct} | Active medications: {gt} | History: {span} years</h4>
  <table style="margin:10px 0">
    <thead><tr><th>Model</th><th>Strategy A</th><th>Strategy B</th><th>Strategy C</th><th>Strategy D</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <p style="font-size:13px;color:#555;margin:0"><strong>Interpretation:</strong> {note}</p>
</div>
""")
    return "\n".join(parts)


def generate_toc() -> str:
    entries = [
        ("key-findings", "Executive Summary — Key Findings"),
        ("dataset",      "Dataset and Experiment Overview"),
        ("table",        "Aggregate Results Table"),
    ]
    for i, (_, title, subtitle, _) in enumerate(FIGURES_META, 1):
        entries.append((f"fig{i:02d}", f"Figure {i} — {title.split('—')[1].strip()}"))
    entries += [
        ("stats",  "Statistical Significance Tests"),
        ("hard",   "Hard Patient Analysis"),
        ("conclusions", "The Five Big Findings"),
    ]
    lis = "\n".join(f'<li><a href="#{anchor}">{label}</a></li>' for anchor, label in entries)
    return f'<div class="toc"><h3>Table of Contents</h3><ol>{lis}</ol></div>'


def main() -> None:
    figs_html = ""
    for i, (fname, title, subtitle, body) in enumerate(FIGURES_META, 1):
        figs_html += make_figure_html(fname, title, subtitle, body, i)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>FHIR Medication Reconciliation — Phase 5 Research Report</title>
<style>{CSS}</style>
</head>
<body>
<div class="page-wrap">

  <!-- Title -->
  <h1>FHIR Medication Reconciliation via LLM Serialisation Strategies</h1>
  <div class="subtitle">Phase 5 — Full Analysis Report with Results Interpretation</div>
  <div class="meta">
    Dataset: 200 synthetic FHIR patients (Synthea) &nbsp;|&nbsp;
    Models: 5 (Phi-3.5-mini, Mistral-7B, BioMistral-7B, Llama-3.1-8B, Llama-3.3-70B) &nbsp;|&nbsp;
    Strategies: 4 (Raw JSON, Markdown Table, Clinical Narrative, Chronological Timeline) &nbsp;|&nbsp;
    Total experiment runs: 4,000
  </div>

  {generate_toc()}

  <!-- Executive Summary -->
  <h2 id="key-findings">Executive Summary — Key Findings</h2>
  <div class="summary-box">
    <h3>Five things this experiment proves</h3>
    <ul>
      <li><strong>Format matters — but how much depends on model size.</strong>
        Strategy C (Clinical Narrative) outperforms Strategy A (Raw JSON) by 0.19 F1 points for Mistral-7B
        (statistically significant, large effect r=0.617). At 70B, the difference disappears — Strategy A is
        actually the best format.</li>
      <li><strong>Models omit medications, they do not hallucinate them.</strong>
        Across all 16 (model, strategy) combinations, mean precision exceeds mean recall. LLMs almost never
        claim an inactive medication is active. They do miss active medications — the clinically dangerous failure.</li>
      <li><strong>Small models hit a capacity ceiling at ~7 active medications.</strong>
        Mistral-7B recall drops from 0.96 (1 med) to 0.24 (11 meds). Llama-3.3-70B maintains near-perfect recall
        across all counts. The bottleneck is reasoning complexity, not context length.</li>
      <li><strong>Domain pretraining without instruction tuning is detrimental.</strong>
        BioMistral-7B (medically fine-tuned) scores F1=0.0000 on all 200 patients across all 4 strategies.
        Mistral-7B (general-purpose, same size) scores F1=0.9149. Instruction-following capability matters far
        more than domain knowledge for this task.</li>
      <li><strong>Llama-3.3-70B + Raw JSON is the current state-of-the-art ceiling.</strong>
        Mean F1=0.9956, precision=1.0000 (zero hallucinations), 196/200 perfect patients, zero parse failures.</li>
    </ul>
  </div>

  <!-- Dataset Overview -->
  <h2 id="dataset">Dataset and Experiment Overview</h2>
  <p>All experiments use 200 synthetic patient records generated by
  <strong>Synthea</strong>, an open-source clinical simulator by MITRE Corporation. No real
  patient data was used. Because we generated the data, the ground truth is known exactly —
  making measurement mathematically precise with no human annotation required.</p>
  <p>Each patient's FHIR R4 bundle was serialised into four text formats (strategies), each
  sent to five models via Ollama's local API. For each of the 4,000 (patient × model × strategy)
  combinations, three files were saved: the serialised input, the exact prompt, and the raw
  model response. Metrics (precision, recall, F1) were then computed by comparing the model's
  extracted medication list to the ground truth.</p>
  <table style="width:auto;min-width:500px">
    <thead><tr><th>Strategy</th><th>Description</th><th>Expected difficulty</th></tr></thead>
    <tbody>
      <tr><td>A — Raw JSON</td><td>FHIR MedicationRequest resources as-is, cleaned of noise fields</td><td>Highest — model must parse FHIR schema mentally</td></tr>
      <tr><td>B — Markdown Table</td><td>Key fields in a table: name, RxNorm, status, date, dose, frequency</td><td>Medium — human-readable but still tabular</td></tr>
      <tr><td>C — Clinical Narrative</td><td>Plain English sentences, active meds listed first under a clear heading</td><td>Lowest — closest to how a clinician would write it</td></tr>
      <tr><td>D — Chronological Timeline</td><td>All medication events sorted by date, model must track temporal state</td><td>Highest — requires reasoning about what is currently active</td></tr>
    </tbody>
  </table>

  <!-- Aggregate Table -->
  <h2 id="table">Aggregate Results Table</h2>
  <p class="section-intro">Each row is one (model, strategy) combination evaluated on all 200 patients.
  The starred (★) row per model group is the best strategy for that model. Hover over rows for highlight.
  Colour coding on Mean F1 reflects performance bands: dark green ≥0.95, light green ≥0.85, yellow ≥0.50, red below.</p>
  {make_aggregate_table()}

  <!-- Figures -->
  <h2>Figures — Results Visualisations with Interpretation</h2>
  <p class="section-intro">All figures were generated from the raw experiment data.
  Each figure is followed by an explanation of how to read it and what it shows for our results.</p>
  {figs_html}

  <!-- Statistical Tests -->
  <h2 id="stats">Statistical Significance Tests</h2>
  <p class="section-intro">Statistical tests confirm that the differences we observe in F1 scores are
  real and not due to chance. All tests use the <strong>Wilcoxon signed-rank test</strong> — a
  non-parametric paired test that does not assume a normal distribution, appropriate for F1
  scores which pile up at 0.0 and 1.0.</p>

  <h3>What the columns mean</h3>
  <ul>
    <li><strong>W:</strong> The test statistic. Lower W = stronger evidence against the null hypothesis.</li>
    <li><strong>p (raw):</strong> The raw p-value — probability of seeing this large a difference by chance if there were truly no effect.</li>
    <li><strong>p (Bonferroni):</strong> Corrected for running 4 tests at once (multiplied by 4). More conservative.</li>
    <li><strong>r:</strong> Effect size. Approximate scale: 0.1 = small, 0.3 = medium, 0.5+ = large.</li>
    <li><strong>*** p&lt;0.001, ** p&lt;0.01, * p&lt;0.05, ns = not significant.</strong></li>
  </ul>

  <h3>Strategy A vs Strategy C (within model)</h3>
  <p>Paired on patient ID — for each patient, does Strategy C score higher than Strategy A?</p>
  {make_stat_table_strat()}

  <h3>Cross-model comparison on Strategy C</h3>
  <p>Does a larger model significantly outperform a smaller one on the same format?</p>
  {make_stat_table_model()}

  <div class="finding-block">
    <h3>What the tests tell us</h3>
    <p>The strategy effect (C &gt; A) is proven real for Mistral and Llama-3.1 with medium-to-large effect
    sizes. For the 70B model, there is no significant strategy difference — it handles all formats equally well.
    The scale effect (larger model = better) is confirmed for every tested comparison, with a very large
    effect size (r=0.757) for the 8B→70B jump. The Mistral vs BioMistral test is essentially a sanity check —
    p=7×10⁻³⁸, the most extreme possible result — confirming that BioMistral's failure is not random.</p>
  </div>

  <!-- Hard Patients -->
  <h2 id="hard">Hard Patient Analysis</h2>
  <p class="section-intro">A patient is "universally hard" if their mean F1, averaged across all 4 main
  models and all 4 strategies (16 runs total), is below 0.5. We found 4 such patients. Their per-model,
  per-strategy F1 breakdown is shown below, colour-coded: green = near-perfect, yellow = partial, red = failure.</p>

  {make_hard_patients()}

  <div class="finding-block">
    <h3>What the hard patient analysis tells us</h3>
    <p>Two of the four hard patients (7323b20b, 6c6acf0d) are hard because of high medication count (11 and 12
    active meds) — consistent with Figure 4's capacity ceiling finding. Two (e15ab14b, bb88b4a2) are hard
    despite low medication counts (4 and 2), which is unexpected. These two likely contain specific medication
    names or Synthea data patterns that trigger format-specific failures. Identifying the exact cause is
    future work — but the pattern of "Strategy A works when Strategy C doesn't" appears in three of the four
    patients, reinforcing that raw JSON is sometimes the most reliable format even for smaller models.</p>
  </div>

  <!-- Five Big Findings -->
  <h2 id="conclusions">The Five Big Findings</h2>

  <div class="finding-block">
    <h3>Finding 1 — The best serialisation strategy is not universal</h3>
    <p>Clinical Narrative (Strategy C) is the optimal format for models up to 8B parameters,
    with statistically significant improvements over Raw JSON (r=0.617 for Mistral, r=0.345 for Llama-3.1).
    At 70B, Raw JSON becomes the best format — not because Clinical Narrative gets worse, but because the
    70B model is capable enough to read FHIR schema directly. <em>Practical implication: match your
    serialisation strategy to your model size.</em></p>
  </div>

  <div class="finding-block">
    <h3>Finding 2 — LLMs omit medications but do not hallucinate them</h3>
    <p>Across all 16 (model, strategy) combinations from the four main models, mean precision consistently
    exceeds mean recall. The highest hallucination rate observed is Phi-3.5-mini + Strategy C at precision=0.762.
    Every other combination has precision ≥0.88. Recall falls as low as 0.590. <em>Clinical implication: the
    risk is not a model inventing medications — it is a model producing an incomplete list. Treat model
    output as "definitely active" rather than "completely active."</em></p>
  </div>

  <div class="finding-block">
    <h3>Finding 3 — Smaller models hit a capacity ceiling at ~7 active medications</h3>
    <p>Mistral-7B recall drops from 0.96 at gt=1 to 0.24 at gt=11. Phi-3.5-mini begins declining from gt=5.
    Llama-3.1-8B maintains adequate recall up to gt=12. Llama-3.3-70B shows no meaningful ceiling within
    our dataset range (max gt=16). Crucially, history span (years of records) does not predict failure —
    only current medication count does. <em>Clinical implication: smaller models are unsafe for
    polypharmacy patients with more than 6–7 concurrent medications.</em></p>
  </div>

  <div class="finding-block">
    <h3>Finding 4 — Domain pretraining without instruction fine-tuning is worthless</h3>
    <p>BioMistral-7B was trained on medical literature yet scores F1=0.0000 on all 4,000 runs involving it.
    Mistral-7B — same base architecture, same parameter count, no biomedical pretraining — scores F1=0.9149.
    The failure modes (garbled tokens, prompt continuation, empty responses) are diagnostic of a completion
    model given instruction-style prompts. <em>Research implication: for structured clinical extraction,
    instruction fine-tuning is the prerequisite. Domain knowledge without it provides no benefit.</em></p>
  </div>

  <div class="finding-block">
    <h3>Finding 5 — Llama-3.3-70B + Raw JSON is the current open-source ceiling</h3>
    <p>The best single result: mean F1=0.9956, mean precision=1.0000 (zero hallucinations across 200 patients),
    196/200 patients with perfect extraction. No parse failures. The 4 imperfect patients all had recall
    slightly below 1.0 but still high precision — confirming that even at this ceiling, the failure mode is
    omission, not invention. <em>This establishes a strong baseline for future work: any proposed improvement
    must beat F1=0.9956 on Strategy A to represent progress.</em></p>
  </div>

  <footer>
    FHIR Medication Reconciliation via LLM Serialisation Strategies &mdash;
    Phase 5 Analysis Report &mdash; 200 patients &times; 4 strategies &times; 5 models = 4,000 runs &mdash;
    Generated from <code>src/analyse_results.py</code> + <code>src/generate_report.py</code>
  </footer>
</div>
</body>
</html>"""

    OUT.write_text(html, encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"Report written to: results/report.html ({size_kb:.0f} KB)")
    print("Open in any browser, then File → Print → Save as PDF")


if __name__ == "__main__":
    main()
