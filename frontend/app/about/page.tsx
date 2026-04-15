import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

const MODELS = [
  { name: "Phi-3.5 Mini Instruct", size: "3.8B", type: "General", vram: "~8 GB" },
  { name: "Mistral 7B v0.3 Instruct", size: "7B", type: "General", vram: "~16 GB" },
  { name: "BioMistral 7B", size: "7B", type: "Biomedical", vram: "~16 GB" },
  { name: "Llama 3.1 8B Instruct", size: "8B", type: "General", vram: "~18 GB" },
  { name: "Llama 3.3 70B Instruct", size: "70B", type: "General", vram: "~43 GB" },
]

const STRATEGIES = [
  {
    id: "A",
    label: "Raw FHIR JSON",
    desc: "The FHIR R4 MedicationRequest resources are passed directly as cleaned JSON, preserving the original structure. All clinical fields remain intact. This is the baseline — what a naive automated pipeline would do.",
    example: `Patient: Harold Pacocha | Age: 74 | Gender: male

[
  {
    "resourceType": "MedicationRequest",
    "status": "active",
    "authoredOn": "2023-11-14",
    "medicationCodeableConcept": {
      "coding": [{ "system": "...rxnorm", "code": "314076",
                   "display": "Lisinopril 10 MG Oral Tablet" }],
      "text": "Lisinopril 10 MG Oral Tablet"
    },
    "dosageInstruction": [{
      "timing": { "repeat": { "frequency": 1, "period": 1, "periodUnit": "d" } },
      "doseAndRate": [{ "doseQuantity": { "value": 1, "unit": "tablet" } }]
    }]
  },
  ...
]`,
  },
  {
    id: "B",
    label: "Flat Markdown Table",
    desc: "Key fields from every MedicationRequest are extracted and formatted as a markdown table with columns for medication name, RxNorm code, status, date, dose, and frequency. All statuses are included — the model must determine which are active.",
    example: `Patient: Harold Pacocha | Age: 74 | Gender: male

| Medication                   | RxNorm | Status  | Prescribed | Dose     | Frequency           |
| ---                          | ---    | ---     | ---        | ---      | ---                 |
| Metformin 500 MG Oral Tablet | 860975 | stopped | 2019-03-01 | -        | -                   |
| Lisinopril 10 MG Oral Tablet | 314076 | active  | 2023-11-14 | 1 tablet | 1 time(s) per 1 day |
| Amlodipine 5 MG Oral Tablet  | 197361 | active  | 2024-02-03 | 1 tablet | 1 time(s) per 1 day |`,
  },
  {
    id: "C",
    label: "Clinical Narrative",
    desc: "Each MedicationRequest is converted into a plain English sentence with codes expanded to readable text. Active medications are listed first under a clear heading, followed by the full history. The goal is something close to how a clinical note reads.",
    example: `Patient: Harold Pacocha | Age: 74 | Gender: male

Currently active medications:
  - Lisinopril 10 MG Oral Tablet (RxNorm: 314076), prescribed on 2023-11-14,
    status: active. Dose: 1 tablet, frequency: 1 time(s) per 1 day.
  - Amlodipine 5 MG Oral Tablet (RxNorm: 197361), prescribed on 2024-02-03,
    status: active. Dose: 1 tablet, frequency: 1 time(s) per 1 day.

Medication history (no longer active):
  - Metformin 500 MG Oral Tablet (RxNorm: 860975), prescribed on 2019-03-01,
    status: stopped. Dosage not recorded.`,
  },
  {
    id: "D",
    label: "Chronological Timeline",
    desc: "All MedicationRequests are sorted by date, oldest to newest, regardless of status. The model must read the full history and reason about what is currently active versus what was stopped. This is the most temporally demanding format.",
    example: `Patient: Harold Pacocha | Age: 74 | Gender: male

Chronological medication history (oldest to newest):

2019-03-01 | stopped | Metformin 500 MG Oral Tablet (RxNorm: 860975) | -
2020-07-15 | stopped | Atorvastatin 20 MG Tablet (RxNorm: 617311) | 1 tablet, 1x/day
2023-11-14 | active  | Lisinopril 10 MG Oral Tablet (RxNorm: 314076) | 1 tablet, 1x/day
2024-02-03 | active  | Amlodipine 5 MG Oral Tablet (RxNorm: 197361) | 1 tablet, 1x/day`,
  },
]

const DASHBOARD_SECTIONS = [
  {
    page: "Overview",
    href: "/",
    desc: "Start here. Four headline numbers — total runs, overall mean F1, best model, and best strategy. Below that, a colour-coded heatmap showing F1 for every model × strategy combination at a glance, followed by a ranked summary table.",
  },
  {
    page: "Models",
    href: "/models",
    desc: "One tab per model, smallest to largest. Each tab shows KPI cards, a grouped precision/recall/F1 bar chart across strategies, an F1 distribution histogram, a per-strategy breakdown table, and a full patient-level results table with per-strategy scores and links to individual drill-downs.",
  },
  {
    page: "Strategies",
    href: "/strategies",
    desc: "One tab per strategy. Each tab shows distribution stats (mean, median, IQR), an F1 histogram, a per-model breakdown table, a mean inference time chart, and a patient-level table with per-model scores.",
  },
  {
    page: "Patients",
    href: "/patients",
    desc: "Search and filter all 200 patients by ID or name. The table shows each patient's active medication count and mean F1. Click any row to open the patient drill-down.",
  },
  {
    page: "Patient drill-down",
    href: "/patients",
    desc: "The core inspection view. A model × strategy grid shows F1, precision, recall, and inference time for every run on this patient. Click any cell to load a side-by-side diff of the ground truth medications versus the model output — green for matched, red for missed or hallucinated. Three tabs below let you inspect the raw model response, the full prompt that was sent, and the serialised input the model actually saw.",
  },
]

export default function AboutPage() {
  return (
    <div className="space-y-10 max-w-4xl">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">About this Research</h1>
        <p className="text-sm text-muted-foreground mt-1">
          FHIR Medication Reconciliation — Serialisation Strategy Benchmark
        </p>
      </div>

      {/* The Problem */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">The Problem</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          <strong className="text-foreground">Medication reconciliation</strong> is the clinical process of producing
          an accurate current medication list from a patient's health records. It is one of the most error-prone steps
          in care — when patients are transferred or discharged, an incorrect list can cause drug interactions, missed
          doses, or wrong prescriptions.
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Large language models can read months or years of medication records and produce a summarised current list
          far faster than a human can. But two failure modes matter critically:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-md border border-red-200 dark:border-red-900 bg-red-50/50 dark:bg-red-950/20 px-4 py-3">
            <p className="text-sm font-medium text-red-700 dark:text-red-400">Hallucination</p>
            <p className="text-xs text-muted-foreground mt-1">
              The model lists a medication that is not in the source data. Can be caught on manual review.
            </p>
          </div>
          <div className="rounded-md border border-orange-200 dark:border-orange-900 bg-orange-50/50 dark:bg-orange-950/20 px-4 py-3">
            <p className="text-sm font-medium text-orange-700 dark:text-orange-400">Omission — the more dangerous failure</p>
            <p className="text-xs text-muted-foreground mt-1">
              The model misses an active medication. May be silently carried forward, causing harm.
            </p>
          </div>
        </div>
      </section>

      {/* Research Hypothesis */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">The Research Hypothesis</h2>
        <div className="rounded-md border border-border bg-muted/30 px-4 py-4">
          <p className="text-sm leading-relaxed">
            Both failure modes are significantly influenced not by <em>which model</em> you use, but by{" "}
            <strong>how the source data is formatted</strong> before it is given to the model.
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed mt-2">
            FHIR R4 — the international standard for electronic health records — stores data as deeply nested JSON
            with numeric codes from medical ontologies (RxNorm, SNOMED, LOINC). This is not a format language models
            were trained to reason over naturally. We believe the serialisation step is a dominant variable that has
            not been systematically studied.
          </p>
        </div>
      </section>

      {/* Core questions */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Core Research Questions</h2>
        <ol className="space-y-2 list-none">
          {[
            "Does serialisation strategy matter more than model size? A 3.8B model with a well-formatted input might outperform a 70B model given raw FHIR JSON.",
            "Which format is safest for omission? Recall — not missing active medications — is the priority metric in a clinical setting.",
            "Does biomedical domain pretraining help? BioMistral was trained on medical literature. Does that give it an advantage over a general-purpose model of the same size?",
            "At what history length do models start failing? Patients with many years of records accumulate hundreds of medication entries. Does recall degrade with history length?",
          ].map((q, i) => (
            <li key={i} className="flex gap-3 text-sm text-muted-foreground">
              <span className="shrink-0 font-mono text-xs font-semibold text-foreground bg-muted rounded px-1.5 py-0.5 h-fit mt-0.5">
                Q{i + 1}
              </span>
              <span className="leading-relaxed">{q}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* Dataset */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">The Dataset</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          All experiments use <strong className="text-foreground">synthetic patient data</strong> generated by{" "}
          <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">Synthea</span>, an open-source patient
          simulator developed by MITRE Corporation. No real patient data is used at any point.
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Because the ground truth is known exactly — we generated the data — model accuracy can be measured with
          mathematical precision, with no need for human annotation.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Patients", value: "200+" },
            { label: "Min. history", value: "3 years" },
            { label: "Population", value: "Elderly adults" },
            { label: "Ground truth", value: "status == active" },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-md border border-border px-3 py-2.5">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-semibold font-mono mt-0.5">{value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Serialisation Strategies */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">The Four Serialisation Strategies</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          The central experimental variable is how each patient's FHIR R4 JSON bundle is converted into text before
          being sent to the model. All four strategies are given the same instruction prompt — only the input format
          changes.
        </p>
        <div className="space-y-4">
          {STRATEGIES.map((s) => (
            <Card key={s.id} className="rounded-md border shadow-none">
              <CardHeader className="pb-2 pt-4">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">Strategy {s.id}</Badge>
                  <CardTitle className="text-sm font-semibold">{s.label}</CardTitle>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed pt-1">{s.desc}</p>
              </CardHeader>
              <CardContent className="pb-4">
                <pre className="text-xs font-mono bg-muted/40 border border-border rounded-md p-3 whitespace-pre-wrap break-words leading-relaxed overflow-x-auto">
                  {s.example}
                </pre>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="rounded-md border border-border bg-muted/30 px-4 py-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">The prompt (same for all strategies)</p>
          <p className="text-xs text-muted-foreground leading-relaxed italic">
            "You are a clinical assistant performing medication reconciliation. You will be given a patient's
            medication history. Your task is to identify all medications that are currently ACTIVE for this patient.
            Return your answer as a JSON array of medication names exactly as they appear in the data. Return nothing
            else — no explanation, no prose, just the JSON array."
          </p>
        </div>
      </section>

      {/* Models */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">The Models</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Five open-source models are evaluated, running on an AWS GPU instance with 48 GB VRAM. The
          selection spans a practical deployment spectrum — from a 3.8B model any clinic can run on a consumer GPU,
          to a 70B model requiring a large workstation. One domain-specialised model (BioMistral) is included to test
          whether biomedical pretraining gives an advantage over general-purpose models of the same size.
        </p>
        <Card className="rounded-md border shadow-none">
          <CardContent className="p-0 pb-2">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent border-b">
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium px-4">Model</TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-center px-4">Size</TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-center px-4">Type</TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">VRAM</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MODELS.map((m) => (
                  <TableRow key={m.name} className="hover:bg-muted/50 border-b border-border/50">
                    <TableCell className="py-2.5 px-4 text-sm font-medium">{m.name}</TableCell>
                    <TableCell className="py-2.5 px-4 text-center font-mono text-xs text-muted-foreground">{m.size}</TableCell>
                    <TableCell className="py-2.5 px-4 text-center">
                      <Badge
                        variant="outline"
                        className={
                          m.type === "Biomedical"
                            ? "text-xs text-violet-700 border-violet-300 dark:text-violet-400 dark:border-violet-700"
                            : "text-xs text-muted-foreground"
                        }
                      >
                        {m.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-xs text-muted-foreground">{m.vram}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>

      {/* Metrics */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">How We Measure Success</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          For each of the 20 model × strategy combinations, we run all 200 patients and compute three core metrics:
        </p>
        <div className="space-y-2">
          {[
            {
              label: "Precision",
              color: "text-muted-foreground",
              def: "Of the medications the model listed, what fraction were actually active? Low precision means hallucination — the model invented medications not present in the record.",
            },
            {
              label: "Recall",
              color: "text-orange-700 dark:text-orange-400",
              def: "Of the medications that were truly active, what fraction did the model find? Low recall means omission — the safety-critical metric. A missed active medication may be silently carried forward to the next clinician.",
            },
            {
              label: "F1 Score",
              color: "text-emerald-700 dark:text-emerald-400",
              def: "The harmonic mean of precision and recall. The primary ranking metric used throughout this dashboard.",
            },
          ].map(({ label, color, def }) => (
            <div key={label} className="flex gap-3 text-sm">
              <span className={`shrink-0 font-semibold font-mono text-xs pt-0.5 w-20 ${color}`}>{label}</span>
              <span className="text-muted-foreground leading-relaxed text-xs">{def}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          A run is marked as a <span className="font-medium text-red-600 dark:text-red-400">parse failure</span> when
          the model does not return a valid JSON array. These runs are counted as F1 = precision = recall = 0
          in all aggregations, consistent with the paper. Raw responses are visible in the response inspector.
        </p>
      </section>

      {/* How to use the dashboard */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Navigating This Dashboard</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Every result from every run — 200 patients × 5 models × 4 strategies = 4,000 runs — is loaded into the
          dashboard. Here is what each section gives you.
        </p>
        <div className="space-y-2">
          {DASHBOARD_SECTIONS.map(({ page, desc }) => (
            <div key={page} className="flex gap-3">
              <span className="shrink-0 font-mono text-xs font-semibold bg-muted rounded px-1.5 py-0.5 h-fit mt-0.5 whitespace-nowrap">
                {page}
              </span>
              <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
