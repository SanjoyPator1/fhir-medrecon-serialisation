import type { ExperimentRow, GroundTruth } from "./data"

export interface ModelStrategyStats {
  model: string
  strategy: string
  mean_f1: number
  mean_precision: number
  mean_recall: number
  mean_inference_time: number
  total: number
  parse_failures: number
  exact_matches: number
}

export interface PatientSummary {
  patient_id: string
  patient_name: string
  active_med_count: number
  total_runs: number
  best_f1: number
  worst_f1: number
  mean_f1: number
  parse_failures: number
}

function mean(arr: number[]): number {
  if (arr.length === 0) return 0
  return arr.reduce((a, b) => a + b, 0) / arr.length
}

function roundTo(n: number, decimals = 4): number {
  return Math.round(n * 10 ** decimals) / 10 ** decimals
}

export function pivotByModelStrategy(rows: ExperimentRow[]): ModelStrategyStats[] {
  const groups = new Map<string, ExperimentRow[]>()
  for (const row of rows) {
    const key = `${row.model}|||${row.strategy}`
    const existing = groups.get(key) ?? []
    existing.push(row)
    groups.set(key, existing)
  }
  const results: ModelStrategyStats[] = []
  for (const [key, group] of groups) {
    const [model, strategy] = key.split("|||")
    // Include parse failures (f1=0) in the mean — consistent with the paper.
    results.push({
      model,
      strategy,
      mean_f1: roundTo(mean(group.map((r) => r.f1))),
      mean_precision: roundTo(mean(group.map((r) => r.precision))),
      mean_recall: roundTo(mean(group.map((r) => r.recall))),
      mean_inference_time: roundTo(mean(group.map((r) => r.inference_time_s))),
      total: group.length,
      parse_failures: group.filter((r) => r.parse_failed).length,
      exact_matches: group.filter((r) => r.exact_match === 1).length,
    })
  }
  return results
}

export function groupByModel(rows: ExperimentRow[]): Record<string, ModelStrategyStats[]> {
  const pivot = pivotByModelStrategy(rows)
  const byModel: Record<string, ModelStrategyStats[]> = {}
  for (const s of pivot) {
    if (!byModel[s.model]) byModel[s.model] = []
    byModel[s.model].push(s)
  }
  return byModel
}

export function groupByStrategy(rows: ExperimentRow[]): Record<string, ModelStrategyStats[]> {
  const pivot = pivotByModelStrategy(rows)
  const byStrat: Record<string, ModelStrategyStats[]> = {}
  for (const s of pivot) {
    if (!byStrat[s.strategy]) byStrat[s.strategy] = []
    byStrat[s.strategy].push(s)
  }
  return byStrat
}

export function f1Distribution(
  rows: ExperimentRow[],
  bins = 10,
): { bin: string; count: number; pct: number }[] {
  // Include parse failures (f1=0) — consistent with paper.
  const binSize = 1 / bins
  const counts = Array<number>(bins).fill(0)
  for (const r of rows) {
    const idx = Math.min(Math.floor(r.f1 / binSize), bins - 1)
    counts[idx]++
  }
  return counts.map((count, i) => ({
    bin: `${(i * binSize).toFixed(1)}–${((i + 1) * binSize).toFixed(1)}`,
    count,
    pct: roundTo(count / (rows.length || 1)),
  }))
}

export function getPatientSummaries(
  rows: ExperimentRow[],
  groundTruth: Record<string, GroundTruth>,
): PatientSummary[] {
  const byPatient = new Map<string, ExperimentRow[]>()
  for (const row of rows) {
    const existing = byPatient.get(row.patient_id) ?? []
    existing.push(row)
    byPatient.set(row.patient_id, existing)
  }
  const summaries: PatientSummary[] = []
  for (const [patient_id, patientRows] of byPatient) {
    const gt = groundTruth[patient_id]
    // Include parse failures (f1=0) in all aggregates — consistent with paper.
    const f1s = patientRows.map((r) => r.f1)
    summaries.push({
      patient_id,
      patient_name: gt?.patient_name ?? "",
      active_med_count: gt?.active_medication_count ?? 0,
      total_runs: patientRows.length,
      best_f1: roundTo(f1s.length > 0 ? Math.max(...f1s) : 0),
      worst_f1: roundTo(f1s.length > 0 ? Math.min(...f1s) : 0),
      mean_f1: roundTo(mean(f1s)),
      parse_failures: patientRows.filter((r) => r.parse_failed).length,
    })
  }
  return summaries.sort((a, b) => a.patient_id.localeCompare(b.patient_id))
}

export function getPatientRows(
  rows: ExperimentRow[],
  patientId: string,
): ExperimentRow[] {
  return rows.filter((r) => r.patient_id === patientId)
}

export function inferenceByModel(
  rows: ExperimentRow[],
  strategies: string[],
  orderedModels?: string[],
): { model: string; [strategy: string]: number | string }[] {
  const pivot = pivotByModelStrategy(rows)
  const models = orderedModels ?? [...new Set(rows.map((r) => r.model))].sort()
  return models.map((model) => {
    const entry: { model: string; [strategy: string]: number | string } = { model }
    for (const strategy of strategies) {
      const stat = pivot.find((s) => s.model === model && s.strategy === strategy)
      entry[strategy] = stat ? roundTo(stat.mean_inference_time, 2) : 0
    }
    return entry
  })
}

export function heatmapData(
  pivot: ModelStrategyStats[],
  models: string[],
  strategies: string[],
): { model: string; [strategy: string]: number | string | null }[] {
  return models.map((model) => {
    const row: { model: string; [strategy: string]: number | string | null } = { model }
    for (const strategy of strategies) {
      const stat = pivot.find((s) => s.model === model && s.strategy === strategy)
      row[strategy] = stat && stat.total > 0 ? stat.mean_f1 : null
    }
    return row
  })
}

export function overallModelRanking(
  rows: ExperimentRow[],
  models: string[],
): { model: string; mean_f1: number; mean_precision: number; mean_recall: number; mean_inference_time: number; total: number; parse_failures: number }[] {
  return models.map((model) => {
    const modelRows = rows.filter((r) => r.model === model)
    return {
      model,
      mean_f1: roundTo(mean(modelRows.map((r) => r.f1))),
      mean_precision: roundTo(mean(modelRows.map((r) => r.precision))),
      mean_recall: roundTo(mean(modelRows.map((r) => r.recall))),
      mean_inference_time: roundTo(mean(modelRows.map((r) => r.inference_time_s)), 2),
      total: modelRows.length,
      parse_failures: modelRows.filter((r) => r.parse_failed).length,
    }
  }).sort((a, b) => b.mean_f1 - a.mean_f1)
}

export function overallStrategyRanking(
  rows: ExperimentRow[],
  strategies: string[],
): { strategy: string; mean_f1: number; mean_precision: number; mean_recall: number; mean_inference_time: number; total: number; parse_failures: number }[] {
  return strategies.map((strategy) => {
    const stratRows = rows.filter((r) => r.strategy === strategy)
    return {
      strategy,
      mean_f1: roundTo(mean(stratRows.map((r) => r.f1))),
      mean_precision: roundTo(mean(stratRows.map((r) => r.precision))),
      mean_recall: roundTo(mean(stratRows.map((r) => r.recall))),
      mean_inference_time: roundTo(mean(stratRows.map((r) => r.inference_time_s)), 2),
      total: stratRows.length,
      parse_failures: stratRows.filter((r) => r.parse_failed).length,
    }
  }).sort((a, b) => b.mean_f1 - a.mean_f1)
}
