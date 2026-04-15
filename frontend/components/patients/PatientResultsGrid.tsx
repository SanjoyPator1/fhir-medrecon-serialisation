"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { MODEL_LABELS, STRATEGY_SHORT } from "@/lib/constants"
import type { ExperimentRow } from "@/lib/data"

interface PatientResultsGridProps {
  rows: ExperimentRow[]
  models: string[]
  strategies: string[]
  selected: { model: string; strategy: string } | null
  onSelect: (model: string, strategy: string) => void
}

function f1Class(f1: number): string {
  if (f1 >= 0.75) return "text-emerald-700 dark:text-emerald-300"
  if (f1 >= 0.45) return "text-amber-700 dark:text-amber-300"
  return "text-red-700 dark:text-red-300"
}

export function PatientResultsGrid({
  rows,
  models,
  strategies,
  selected,
  onSelect,
}: PatientResultsGridProps) {
  function getRow(model: string, strategy: string): ExperimentRow | undefined {
    return rows.find((r) => r.model === model && r.strategy === strategy)
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent border-b">
            <TableHead className="text-xs uppercase text-muted-foreground font-medium w-40">
              Model
            </TableHead>
            {strategies.map((s) => (
              <TableHead
                key={s}
                className="text-xs uppercase text-muted-foreground font-medium text-center min-w-[130px]"
              >
                {STRATEGY_SHORT[s] ?? s}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {models.map((model) => (
            <TableRow key={model} className="border-b border-border/50 hover:bg-transparent">
              <TableCell className="text-xs font-medium text-muted-foreground py-3">
                {MODEL_LABELS[model] ?? model}
              </TableCell>
              {strategies.map((strategy) => {
                const row = getRow(model, strategy)
                const isSelected =
                  selected?.model === model && selected?.strategy === strategy
                if (!row) {
                  return (
                    <TableCell key={strategy} className="text-center py-3">
                      <span className="text-xs text-muted-foreground">—</span>
                    </TableCell>
                  )
                }
                return (
                  <TableCell key={strategy} className="py-2 px-2">
                    <button
                      onClick={() => onSelect(model, strategy)}
                      className={cn(
                        "w-full rounded-md px-2 py-2 text-left transition-colors border",
                        isSelected
                          ? "border-primary bg-primary/5 dark:bg-primary/10"
                          : "border-transparent hover:border-border hover:bg-muted/50",
                      )}
                    >
                      {row.parse_failed ? (
                        <div className="text-center">
                          <Badge variant="outline" className="text-xs text-red-600 border-red-300 dark:text-red-400 dark:border-red-700">
                            Parse fail
                          </Badge>
                        </div>
                      ) : (
                        <div className="space-y-0.5">
                          <p className={cn("font-mono text-sm font-semibold", f1Class(row.f1))}>
                            {row.f1.toFixed(3)}
                          </p>
                          <div className="flex gap-2 text-xs text-muted-foreground font-mono">
                            <span>P {row.precision.toFixed(2)}</span>
                            <span>R {row.recall.toFixed(2)}</span>
                          </div>
                          <p className="text-xs text-muted-foreground font-mono">
                            {row.inference_time_s.toFixed(1)}s
                          </p>
                        </div>
                      )}
                    </button>
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <p className="text-xs text-muted-foreground px-1 mt-2">
        Click a cell to compare that result against ground truth below.
      </p>
    </div>
  )
}
