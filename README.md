# fhir-medrecon-serialisation

Code, data, and results for the paper **"Serialisation Strategy Matters: How FHIR Data Format Affects LLM Medication Reconciliation"**.

> arXiv preprint: [2604.21076](https://arxiv.org/abs/2604.21076)

---

## What this research is about

When a large language model is asked to produce a current medication list from years of structured patient data, two things can go wrong. The model can hallucinate medications that are not in the source data, or it can omit medications that are genuinely active. Both are patient safety problems. Omissions are the more dangerous of the two — a missed active medication carried forward to the next clinician can cause drug interactions or dosing errors that a hallucinated finding might not.

This research investigates a specific and underexplored cause of both failure modes: the way FHIR data is formatted before being sent to the model. Raw FHIR R4 JSON is heavily nested, code-heavy with SNOMED, RxNorm, and LOINC identifiers, and not a format LLMs were pretrained to reason over fluently. The hypothesis is that the serialisation strategy — how you convert structured FHIR JSON into LLM-readable text — is a dominant variable in medication reconciliation accuracy, potentially more important than which model you use.

### The core research question

Which serialisation strategy for converting longitudinal FHIR R4 JSON into LLM-readable text produces the highest medication reconciliation accuracy, and how does this interact with model size?

### Key findings

We compare four serialisation strategies across five open-weight models on 200 synthetic patients (4,000 inference runs total):

- Clinical Narrative outperforms Raw JSON by up to **19 F1 points** for Mistral-7B
- This advantage **reverses at 70B** — Raw JSON achieves the best mean F1 of 0.9956 for Llama-3.3-70B
- **Omission is the dominant failure mode** across all conditions — models miss active medications more often than they hallucinate fake ones
- **BioMistral-7B** (domain-pretrained, not instruction-tuned) produces zero usable output in all conditions

---

## The four serialisation strategies

The central experimental variable is how FHIR data is presented to the model before the reconciliation prompt.

**Strategy A — Raw JSON.** The FHIR R4 bundle is passed directly as produced by the EHR system. This is the baseline and represents what a naive automated pipeline would do.

**Strategy B — Flat markdown table.** Key fields are extracted and formatted as a table with columns for medication name, RxNorm code, dose, frequency, start date, and status. Human-readable and structured but loses temporal narrative.

**Strategy C — Clinical narrative.** Each MedicationRequest is converted to a plain English sentence. Active medications appear first under a labelled heading, making the task-relevant partition explicit.

**Strategy D — Chronological timeline.** All medication events are sorted by date as pipe-delimited lines. No separation between active and historical — the model must reason across the full temporal sequence to determine what is currently active.

---

## Models evaluated

| Model | Params | Type | Quant |
|---|---|---|---|
| Phi-3.5-mini | 3.8B | Instruct | Q4_0 |
| Mistral-7B | 7B | Instruct | Q4_K_M |
| BioMistral-7B | 7B | Pretrain only | Q4_K_M |
| Llama-3.1-8B | 8B | Instruct | Q4_K_M |
| Llama-3.3-70B | 70B | Instruct | Q4_K_M |

All models served locally via [Ollama](https://ollama.com) on an AWS `g6e.xlarge` (NVIDIA L40S, 48 GB VRAM). The model selection spans two orders of magnitude in parameter count to test whether model size predicts accuracy and whether domain pretraining (BioMistral) helps on structured extraction.

---

## Evaluation metrics

For each model and serialisation strategy combination, the following metrics are computed over the full patient dataset:

- **Precision** — what fraction of medications in the model output were actually active. Measures hallucination rate.
- **Recall** — what fraction of active medications in the ground truth the model correctly identified. Measures omission rate. This is the patient-safety-critical metric.
- **F1 score** — harmonic mean of precision and recall.

If the model output cannot be parsed as a JSON array, precision = recall = F1 = 0.

---

## Repository structure

```
├── scripts/
│   ├── setup_synthea.sh        download the Synthea jar
│   ├── generate_sample.py      generate a small test batch
│   └── build_dataset.py        generate patients until target usable count is met
├── src/
│   ├── serialisers.py          the four serialisation strategies
│   ├── ground_truth.py         extract active medications from FHIR bundles
│   ├── run_experiments.py      main inference loop (all models × strategies)
│   ├── evaluate.py             precision, recall, F1 scoring
│   ├── analyse_results.py      aggregate tables and statistical tests
│   └── export_for_frontend.py  build experiments.json for the dashboard
├── data/
│   ├── raw/                    200 synthetic FHIR R4 patient bundles (Synthea)
│   └── ground_truth/           extracted ground truth JSONs
├── results/
│   ├── master_results.csv      one row per patient × strategy × model
│   ├── aggregate_table.csv     mean P/R/F1 per model × strategy
│   └── figures/                all paper figures
├── paper/v1/                   LaTeX source for the paper
├── frontend/                   Next.js interactive results dashboard
└── requirements.txt
```

---

## Reproducing the experiments

**Requirements:** Python 3.10+, Java 17+, [Ollama](https://ollama.com) with the five models pulled.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# generate the 200-patient synthetic cohort
bash scripts/setup_synthea.sh
python scripts/build_dataset.py

# run all 4,000 inference runs
python src/run_experiments.py

# produce aggregate tables and figures
python src/analyse_results.py
```

Raw inference outputs are written to `output/`. Run `python src/analyse_results.py` to produce `results/master_results.csv` and figures.

---

## Interactive dashboard

Live: [fhir-medrecon-serialisation.vercel.app](https://fhir-medrecon-serialisation.vercel.app/)

An interactive results dashboard built with Next.js is in `frontend/`. It lets you browse every patient, strategy, and model combination and inspect the serialised input and model output side by side.

To run locally:

```bash
cd frontend
npm install
npm run dev
```

---

## Dataset

All experiments use synthetic FHIR R4 patient data generated by [Synthea](https://github.com/synthetichealth/synthea), an open-source patient population simulator developed by MITRE. No real patient data is used at any point. Because Synthea generates patients with known ground truth, precision and recall can be measured with mathematical exactness without human annotation.

The dataset contains 200 patients, each with at least one active medication and at least 10 years of medication history. Patients are aged 40–75 at simulation end, producing realistic polypharmacy across a range of history lengths.

Ground truth is extracted deterministically from the MedicationRequest resources in the FHIR bundle. Only resources with `status == "active"` are included in the ground truth medication list.

---

## License

MIT
