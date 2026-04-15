import { loadExperiments, MODEL_LABELS, STRATEGY_LABELS } from "@/lib/data"
import { sortModelsBySize } from "@/lib/constants"
import { groupByStrategy, f1Distribution, inferenceByModel } from "@/lib/aggregations"
import { MetricCard } from "@/components/layout/metric-card"
import { F1DistributionChart } from "@/components/charts/F1DistributionChart"
import { InferenceTimeChart } from "@/components/charts/InferenceTimeChart"
import { StrategyPatientTable } from "@/components/patients/StrategyPatientTable"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const STRATEGY_DESC: Record<string, string> = {
  strategy_a: "Raw FHIR R4 JSON bundle passed directly to the model. Maximally verbose, includes all fields.",
  strategy_b: "FHIR data flattened into a markdown table. Structured and readable, reduced verbosity.",
  strategy_c: "Medications described as plain-English clinical sentences. Natural language, clinician-friendly.",
  strategy_d: "Medication history ordered chronologically by date. Emphasises temporal progression.",
}

export default function StrategiesPage() {
  const { meta, rows, ground_truth } = loadExperiments()
  const byStrategy = groupByStrategy(rows)
  const orderedModels = sortModelsBySize(meta.models)
  const inferenceData = inferenceByModel(rows, meta.strategies, orderedModels)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Strategy Analysis</h1>
        <p className="text-sm text-muted-foreground mt-1">
          How each serialisation format affects model performance
        </p>
      </div>

      <Tabs defaultValue={meta.strategies[0]}>
        <TabsList className="h-9">
          {meta.strategies.map((s) => (
            <TabsTrigger key={s} value={s} className="text-xs">
              {s.replace("strategy_", "Strategy ").replace("a", "A").replace("b", "B").replace("c", "C").replace("d", "D")}
            </TabsTrigger>
          ))}
        </TabsList>

        {meta.strategies.map((strategy) => {
          const stratStats = byStrategy[strategy] ?? []
          const stratRows = rows.filter((r) => r.strategy === strategy)
          const parseFailures = stratRows.filter((r) => r.parse_failed).length
          const meanF1 = stratRows.length
            ? stratRows.reduce((s, r) => s + r.f1, 0) / stratRows.length
            : 0
          const f1Values = stratRows.map((r) => r.f1).sort((a, b) => a - b)
          const median =
            f1Values.length > 0
              ? f1Values[Math.floor(f1Values.length / 2)]
              : 0
          const p25 =
            f1Values.length > 0
              ? f1Values[Math.floor(f1Values.length * 0.25)]
              : 0
          const p75 =
            f1Values.length > 0
              ? f1Values[Math.floor(f1Values.length * 0.75)]
              : 0
          const dist = f1Distribution(stratRows)
          const sortedModels = [...stratStats].sort((a, b) => b.mean_f1 - a.mean_f1)

          return (
            <TabsContent key={strategy} value={strategy} className="mt-6 space-y-6">
              <div className="px-4 py-3 rounded-md border border-border bg-muted/30 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">{STRATEGY_LABELS[strategy]}: </span>
                {STRATEGY_DESC[strategy]}
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard label="Mean F1" value={meanF1.toFixed(3)} sub="valid runs only" />
                <MetricCard label="Median F1" value={median.toFixed(3)} sub="50th percentile" />
                <MetricCard label="F1 p25–p75" value={`${p25.toFixed(2)}–${p75.toFixed(2)}`} sub="interquartile range" />
                <MetricCard
                  label="Parse Failures"
                  value={parseFailures}
                  sub={`of ${stratRows.length} total runs`}
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="rounded-md border shadow-none">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold">F1 Distribution</CardTitle>
                    <p className="text-xs text-muted-foreground">All models, all patients</p>
                  </CardHeader>
                  <CardContent>
                    <F1DistributionChart data={dist} />
                  </CardContent>
                </Card>

                <Card className="rounded-md border shadow-none">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold">Per-Model Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 pb-2">
                    <Table>
                      <TableHeader>
                        <TableRow className="hover:bg-transparent border-b">
                          <TableHead className="text-xs uppercase text-muted-foreground font-medium px-4">Model</TableHead>
                          <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">F1</TableHead>
                          <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">Precision</TableHead>
                          <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">Recall</TableHead>
                          <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">Avg time</TableHead>
                          <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">Failures</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sortedModels.map((m) => (
                          <TableRow key={m.model} className="hover:bg-muted/50 border-b border-border/50">
                            <TableCell className="py-2.5 px-4 text-sm">
                              {MODEL_LABELS[m.model] ?? m.model}
                            </TableCell>
                            <TableCell className="py-2.5 px-4 text-right font-mono text-sm font-semibold">
                              {m.mean_f1.toFixed(3)}
                            </TableCell>
                            <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground">
                              {m.mean_precision.toFixed(3)}
                            </TableCell>
                            <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground">
                              {m.mean_recall.toFixed(3)}
                            </TableCell>
                            <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground">
                              {m.mean_inference_time.toFixed(1)}s
                            </TableCell>
                            <TableCell className="py-2.5 px-4 text-right">
                              {m.parse_failures > 0 ? (
                                <Badge variant="outline" className="font-mono text-xs text-red-600 border-red-300 dark:text-red-400 dark:border-red-700">
                                  {m.parse_failures}
                                </Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground font-mono">0</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>

              <Card className="rounded-md border shadow-none">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">
                    Mean Inference Time — All Models × Strategies
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">Seconds per patient run</p>
                </CardHeader>
                <CardContent>
                  <InferenceTimeChart data={inferenceData} strategies={meta.strategies} />
                </CardContent>
              </Card>

              <Card className="rounded-md border shadow-none">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Patient-level Results</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    All patients · click any row to open drill-down
                  </p>
                </CardHeader>
                <CardContent>
                  <StrategyPatientTable
                    rows={stratRows}
                    models={orderedModels}
                    groundTruth={ground_truth}
                  />
                </CardContent>
              </Card>
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}
