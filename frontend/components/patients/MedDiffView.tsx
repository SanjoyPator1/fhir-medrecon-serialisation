"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { MODEL_LABELS, STRATEGY_LABELS } from "@/lib/constants"
import type { ExperimentRow } from "@/lib/data"

interface MedDiffViewProps {
  row: ExperimentRow
  groundTruth: string[]
}

type FileTab = "response" | "prompt" | "input"

const SYSTEM_INSTRUCTION = `You are a clinical assistant performing medication reconciliation.
You will be given a patient's medication history. Your task is to identify all
medications that are currently ACTIVE for this patient.
A medication is currently active if its status is "active". Medications with
status "completed", "stopped", "cancelled", or "on-hold" are historical
and must NOT be included in your answer.
Return your answer as a JSON array of medication names exactly as they appear
in the data. Return nothing else — no explanation, no prose, just the JSON array.
If there are no active medications, return an empty array: []`

async function fetchSerializedInput(strategy: string, patientId: string): Promise<string> {
  const res = await fetch(`/data/inputs/${strategy}/${patientId}.txt`)
  if (!res.ok) throw new Error("Failed to load input")
  return res.text()
}

export function MedDiffView({ row, groundTruth }: MedDiffViewProps) {
  const tpSet = new Set(row.true_positives.map((m) => m.toLowerCase()))
  const fnSet = new Set(row.false_negatives.map((m) => m.toLowerCase()))

  const modelOutputs = [
    ...row.true_positives.map((m) => ({ name: m, kind: "correct" as const })),
    ...row.false_positives.map((m) => ({ name: m, kind: "hallucinated" as const })),
  ]

  // Raw file viewer state
  const [activeTab, setActiveTab] = useState<FileTab | null>("response")
  const [loadedContent, setLoadedContent] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  async function openTab(tab: FileTab) {
    if (activeTab === tab) {
      setActiveTab(null)
      return
    }
    setActiveTab(tab)
    if (tab === "response") return // already in memory

    const cacheKey = `${row.model}/${row.strategy}/${row.patient_id}/${tab}`
    if (loadedContent[cacheKey]) return

    setLoading(true)
    setLoadError(null)
    try {
      const serialised = await fetchSerializedInput(row.strategy, row.patient_id)
      const inputKey = `${row.model}/${row.strategy}/${row.patient_id}/input`
      const promptKey = `${row.model}/${row.strategy}/${row.patient_id}/prompt`
      setLoadedContent((prev) => ({
        ...prev,
        [inputKey]: serialised,
        [promptKey]: `${SYSTEM_INSTRUCTION}\n\n---\n\n${serialised}`,
      }))
    } catch (e) {
      setLoadError(`Could not load ${tab}`)
    } finally {
      setLoading(false)
    }
  }

  function activeContent(): string | null {
    if (!activeTab) return null
    if (activeTab === "response") return row.raw_response ?? "(no response recorded)"
    const cacheKey = `${row.model}/${row.strategy}/${row.patient_id}/${activeTab}`
    return loadedContent[cacheKey] ?? null
  }

  const content = activeContent()

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <div>
          <span className="text-muted-foreground text-xs">Model: </span>
          <span className="font-medium text-sm">{MODEL_LABELS[row.model] ?? row.model}</span>
        </div>
        <div>
          <span className="text-muted-foreground text-xs">Strategy: </span>
          <span className="font-medium text-sm">{STRATEGY_LABELS[row.strategy] ?? row.strategy}</span>
        </div>
        <div className="flex gap-3 text-xs font-mono">
          <span className="text-emerald-700 dark:text-emerald-400">F1 {row.f1.toFixed(3)}</span>
          <span className="text-muted-foreground">P {row.precision.toFixed(3)}</span>
          <span className="text-muted-foreground">R {row.recall.toFixed(3)}</span>
          <span className="text-muted-foreground">{row.inference_time_s.toFixed(1)}s</span>
        </div>
      </div>

      {/* Diff columns */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Ground Truth */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Ground Truth
            </h4>
            <span className="text-xs text-muted-foreground font-mono">{groundTruth.length} active</span>
          </div>
          <div className="rounded-md border border-border overflow-hidden">
            {groundTruth.length === 0 ? (
              <p className="px-3 py-4 text-xs text-muted-foreground text-center">No active medications</p>
            ) : (
              groundTruth.map((med, i) => {
                const matched = tpSet.has(med.toLowerCase())
                const missed = fnSet.has(med.toLowerCase())
                return (
                  <div
                    key={i}
                    className={
                      matched
                        ? "flex items-center gap-2 px-3 py-2.5 border-b border-border/40 bg-green-50 dark:bg-green-950/30 last:border-0"
                        : missed
                        ? "flex items-center gap-2 px-3 py-2.5 border-b border-border/40 bg-red-50 dark:bg-red-950/25 last:border-0"
                        : "flex items-center gap-2 px-3 py-2.5 border-b border-border/40 last:border-0"
                    }
                  >
                    <span className="font-mono text-xs flex-1 min-w-0 break-words">{med}</span>
                    {matched && (
                      <Badge variant="outline" className="shrink-0 text-xs text-green-700 border-green-300 dark:text-green-400 dark:border-green-700">
                        Matched
                      </Badge>
                    )}
                    {missed && (
                      <Badge variant="outline" className="shrink-0 text-xs text-red-700 border-red-300 dark:text-red-400 dark:border-red-700">
                        Missed
                      </Badge>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Model Output */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Model Output
            </h4>
            <span className="text-xs text-muted-foreground font-mono">{row.predicted_count} predicted</span>
          </div>
          <div className="rounded-md border border-border overflow-hidden">
            {row.parse_failed ? (
              <div className="px-3 py-4 space-y-1 text-center">
                <p className="text-xs text-red-600 dark:text-red-400 font-medium">Parse failed</p>
                <p className="text-xs text-muted-foreground">Medications could not be extracted — see raw response below</p>
              </div>
            ) : modelOutputs.length === 0 ? (
              <p className="px-3 py-4 text-xs text-muted-foreground text-center">No medications predicted</p>
            ) : (
              modelOutputs.map((item, i) => (
                <div
                  key={i}
                  className={
                    item.kind === "correct"
                      ? "flex items-center gap-2 px-3 py-2.5 border-b border-border/40 bg-green-50 dark:bg-green-950/30 last:border-0"
                      : "flex items-center gap-2 px-3 py-2.5 border-b border-border/40 bg-red-50 dark:bg-red-950/25 last:border-0"
                  }
                >
                  <span className="font-mono text-xs flex-1 min-w-0 break-words">{item.name}</span>
                  {item.kind === "correct" ? (
                    <Badge variant="outline" className="shrink-0 text-xs text-green-700 border-green-300 dark:text-green-400 dark:border-green-700">
                      Correct
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="shrink-0 text-xs text-red-700 border-red-300 dark:text-red-400 dark:border-red-700">
                      Hallucinated
                    </Badge>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Summary row */}
      <div className="flex flex-wrap gap-4 text-xs font-mono border-t border-border pt-3">
        <span className="text-green-700 dark:text-green-400">{row.tp} matched</span>
        <span className="text-red-600 dark:text-red-400">{row.fn} missed</span>
        <span className="text-orange-600 dark:text-orange-400">{row.fp} hallucinated</span>
        <span className="text-muted-foreground">
          {row.exact_match === 1 ? "exact match" : "no exact match"}
        </span>
        {row.parse_failed && (
          <span className="text-red-600 dark:text-red-400">parse failed</span>
        )}
      </div>

      {/* Raw file inspector */}
      <div className="border border-border rounded-md overflow-hidden">
        <div className="flex items-center gap-0 border-b border-border bg-muted/30 px-2">
          <span className="text-xs text-muted-foreground px-2 py-2 font-medium shrink-0">Inspect:</span>
          {(["response", "prompt", "input"] as FileTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => openTab(tab)}
              className={
                activeTab === tab
                  ? "px-3 py-2 text-xs font-medium border-b-2 border-primary text-foreground transition-colors"
                  : "px-3 py-2 text-xs text-muted-foreground hover:text-foreground border-b-2 border-transparent transition-colors"
              }
            >
              {tab === "response"
                ? "Raw Response"
                : tab === "prompt"
                ? "Full Prompt"
                : "Serialised Input"}
            </button>
          ))}
        </div>

        {activeTab && (
          <div className="relative">
            {loading && (
              <div className="px-4 py-6 text-xs text-muted-foreground text-center">
                Loading…
              </div>
            )}
            {loadError && !loading && (
              <div className="px-4 py-6 text-xs text-red-600 dark:text-red-400 text-center">
                {loadError}
              </div>
            )}
            {content && !loading && (
              <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words max-h-96 overflow-y-auto bg-muted/20 leading-relaxed">
                {content}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
