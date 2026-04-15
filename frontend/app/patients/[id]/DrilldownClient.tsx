"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PatientResultsGrid } from "@/components/patients/PatientResultsGrid"
import { MedDiffView } from "@/components/patients/MedDiffView"
import type { ExperimentRow, GroundTruth } from "@/lib/data"

interface DrilldownClientProps {
  rows: ExperimentRow[]
  groundTruth: GroundTruth
  models: string[]
  strategies: string[]
}

export function DrilldownClient({
  rows,
  groundTruth,
  models,
  strategies,
}: DrilldownClientProps) {
  const validRows = rows.filter((r) => !r.parse_failed)
  const bestRow = validRows.length
    ? validRows.reduce((best, r) => (r.f1 > best.f1 ? r : best), validRows[0])
    : null

  const [selected, setSelected] = useState<{ model: string; strategy: string } | null>(
    bestRow ? { model: bestRow.model, strategy: bestRow.strategy } : null,
  )

  const selectedRow = selected
    ? rows.find((r) => r.model === selected.model && r.strategy === selected.strategy)
    : null

  return (
    <div className="space-y-6">
      <Card className="rounded-md border shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Results Grid</CardTitle>
          <p className="text-xs text-muted-foreground">
            F1 / Precision / Recall / Inference time per model × strategy
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <PatientResultsGrid
            rows={rows}
            models={models}
            strategies={strategies}
            selected={selected}
            onSelect={(model, strategy) => setSelected({ model, strategy })}
          />
        </CardContent>
      </Card>

      {selectedRow && (
        <Card className="rounded-md border shadow-none">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Medication Diff</CardTitle>
          </CardHeader>
          <CardContent>
            <MedDiffView
              row={selectedRow}
              groundTruth={groundTruth.medications}
            />
          </CardContent>
        </Card>
      )}

      {!selectedRow && rows.length > 0 && (
        <p className="text-sm text-muted-foreground text-center py-6">
          Click a cell in the results grid to compare against ground truth.
        </p>
      )}
    </div>
  )
}
