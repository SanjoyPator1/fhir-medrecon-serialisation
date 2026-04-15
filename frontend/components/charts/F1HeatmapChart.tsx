"use client"

import { MODEL_LABELS, STRATEGY_SHORT } from "@/lib/constants"
import { cn } from "@/lib/utils"

interface HeatmapRow {
  model: string
  [strategy: string]: number | string | null
}

interface F1HeatmapChartProps {
  data: HeatmapRow[]
  strategies: string[]
}

function cellClass(f1: number | null): string {
  if (f1 === null)
    return "bg-muted/40 text-muted-foreground"
  if (f1 >= 0.75)
    return "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-900 dark:text-emerald-100"
  if (f1 >= 0.60)
    return "bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-200"
  if (f1 >= 0.45)
    return "bg-amber-50 dark:bg-amber-900/25 text-amber-800 dark:text-amber-200"
  if (f1 >= 0.30)
    return "bg-orange-50 dark:bg-orange-900/25 text-orange-800 dark:text-orange-200"
  return "bg-red-50 dark:bg-red-900/25 text-red-800 dark:text-red-200"
}

export function F1HeatmapChart({ data, strategies }: F1HeatmapChartProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground w-40">
              Model
            </th>
            {strategies.map((s) => (
              <th
                key={s}
                className="text-center px-3 py-2 text-xs font-medium text-muted-foreground min-w-[110px]"
              >
                {STRATEGY_SHORT[s] ?? s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.model} className="border-t border-border/50">
              <td className="px-3 py-3 text-xs font-medium text-muted-foreground">
                {MODEL_LABELS[row.model] ?? row.model}
              </td>
              {strategies.map((s) => {
                const f1 = typeof row[s] === "number" ? (row[s] as number) : null
                return (
                  <td key={s} className="px-3 py-3">
                    <div
                      className={cn(
                        "rounded-md px-3 py-2 text-center font-mono text-sm font-semibold",
                        cellClass(f1),
                      )}
                    >
                      {f1 !== null ? f1.toFixed(3) : "—"}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center gap-4 mt-3 px-3 pb-1">
        <span className="text-xs text-muted-foreground">F1 scale:</span>
        {[
          { label: "≥0.75", cls: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200" },
          { label: "0.60–0.75", cls: "bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300" },
          { label: "0.45–0.60", cls: "bg-amber-50 dark:bg-amber-900/25 text-amber-700 dark:text-amber-300" },
          { label: "<0.45", cls: "bg-red-50 dark:bg-red-900/25 text-red-700 dark:text-red-300" },
        ].map(({ label, cls }) => (
          <span key={label} className={cn("text-xs px-2 py-0.5 rounded font-mono", cls)}>
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
