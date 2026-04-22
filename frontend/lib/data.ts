import "server-only"
import fs from "fs"
import path from "path"
export { MODEL_LABELS, STRATEGY_LABELS, STRATEGY_SHORT } from "./constants"

export interface MedicationFull {
  medication_name: string
  rxnorm_code?: string
  authored_on?: string
  dosage_text?: string | null
  frequency?: string
  dose_quantity?: { value: number; unit: string | null }
  has_structured_dosage?: boolean
}

export interface GroundTruth {
  patient_name: string
  birth_date: string
  gender: string
  history_span_years: number
  total_medication_requests: number
  active_medication_count: number
  medications: string[]
  medications_full: MedicationFull[]
}

export interface ExperimentRow {
  patient_id: string
  model: string
  strategy: string
  precision: number
  recall: number
  f1: number
  exact_match: number
  inference_time_s: number
  tp: number
  fp: number
  fn: number
  predicted_count: number
  ground_truth_count: number
  parse_failed: boolean
  true_positives: string[]
  false_positives: string[]
  false_negatives: string[]
  raw_response: string | null
}

export interface ExperimentsMeta {
  generated_at: string
  total_patients: number
  total_runs: number
  models: string[]
  strategies: string[]
  mean_f1_overall: number
  best_model: string
  best_strategy: string
}

export interface ExperimentsData {
  meta: ExperimentsMeta
  rows: ExperimentRow[]
  ground_truth: Record<string, GroundTruth>
}

let _cached: ExperimentsData | null = null

export function loadExperiments(): ExperimentsData {
  if (_cached) return _cached
  const filePath = path.join(process.cwd(), "public", "data", "experiments.json")
  const raw = fs.readFileSync(filePath, "utf-8")
  _cached = JSON.parse(raw) as ExperimentsData
  return _cached
}

