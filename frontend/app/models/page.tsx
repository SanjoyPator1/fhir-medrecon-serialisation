import { loadExperiments, MODEL_LABELS, STRATEGY_LABELS } from "@/lib/data"
import { sortModelsBySize } from "@/lib/constants"
import { groupByModel, f1Distribution } from "@/lib/aggregations"
import { MetricCard } from "@/components/layout/metric-card"
import { MetricBarChart } from "@/components/charts/MetricBarChart"
import { F1DistributionChart } from "@/components/charts/F1DistributionChart"
import { ModelPatientTable } from "@/components/patients/ModelPatientTable"
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

export default function ModelsPage() {
  const { meta, rows, ground_truth } = loadExperiments()
  const byModel = groupByModel(rows)
  const orderedModels = sortModelsBySize(meta.models)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Model Comparison</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Performance breakdown per model across all four serialisation strategies
        </p>
      </div>

      <Tabs defaultValue={orderedModels[0]}>
        <TabsList className="h-9 flex-wrap gap-1">
          {orderedModels.map((model) => (
            <TabsTrigger key={model} value={model} className="text-xs">
              {MODEL_LABELS[model] ?? model}
            </TabsTrigger>
          ))}
        </TabsList>

        {orderedModels.map((model) => {
          const modelStats = byModel[model] ?? []
          const modelRows = rows.filter((r) => r.model === model)
          const parseFailures = modelRows.filter((r) => r.parse_failed).length
          const meanF1 = modelRows.length
            ? modelRows.reduce((s, r) => s + r.f1, 0) / modelRows.length
            : 0
          const meanRecall = modelRows.length
            ? modelRows.reduce((s, r) => s + r.recall, 0) / modelRows.length
            : 0
          const meanInf = modelRows.length
            ? modelRows.reduce((s, r) => s + r.inference_time_s, 0) / modelRows.length
            : 0
          const dist = f1Distribution(modelRows)

          const sortedStats = [...modelStats].sort((a, b) => b.mean_f1 - a.mean_f1)

          const barData = meta.strategies.map((s) => {
            const stat = modelStats.find((ms) => ms.strategy === s)
            return {
              strategy: s,
              mean_f1: stat?.mean_f1 ?? 0,
              mean_precision: stat?.mean_precision ?? 0,
              mean_recall: stat?.mean_recall ?? 0,
            }
          })

          return (
            <TabsContent key={model} value={model} className="mt-6 space-y-6">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard label="Mean F1" value={meanF1.toFixed(3)} sub="all strategies" />
                <MetricCard label="Mean Recall" value={meanRecall.toFixed(3)} sub="clinically critical" />
                <MetricCard
                  label="Avg Inference"
                  value={`${meanInf.toFixed(1)}s`}
                  sub="per patient run"
                />
                <MetricCard
                  label="Parse Failures"
                  value={parseFailures}
                  sub={`of ${modelRows.length} total runs`}
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="rounded-md border shadow-none">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold">
                      Precision / Recall / F1 by Strategy
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <MetricBarChart data={barData} />
                  </CardContent>
                </Card>

                <Card className="rounded-md border shadow-none">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold">F1 Distribution</CardTitle>
                    <p className="text-xs text-muted-foreground">
                      Across all strategies and patients
                    </p>
                  </CardHeader>
                  <CardContent>
                    <F1DistributionChart data={dist} />
                  </CardContent>
                </Card>
              </div>

              <Card className="rounded-md border shadow-none">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">
                    Per-Strategy Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0 pb-2">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent border-b">
                        <TableHead className="text-xs uppercase text-muted-foreground font-medium px-4">
                          Strategy
                        </TableHead>
                        <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">
                          F1
                        </TableHead>
                        <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">
                          Precision
                        </TableHead>
                        <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">
                          Recall
                        </TableHead>
                        <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4 hidden md:table-cell">
                          Avg time
                        </TableHead>
                        <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4 hidden md:table-cell">
                          Failures
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedStats.map((s) => (
                        <TableRow
                          key={s.strategy}
                          className="hover:bg-muted/50 border-b border-border/50"
                        >
                          <TableCell className="py-2.5 px-4 text-sm">
                            {STRATEGY_LABELS[s.strategy] ?? s.strategy}
                          </TableCell>
                          <TableCell className="py-2.5 px-4 text-right font-mono text-sm font-semibold">
                            {s.mean_f1.toFixed(3)}
                          </TableCell>
                          <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground">
                            {s.mean_precision.toFixed(3)}
                          </TableCell>
                          <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground">
                            {s.mean_recall.toFixed(3)}
                          </TableCell>
                          <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground hidden md:table-cell">
                            {s.mean_inference_time.toFixed(1)}s
                          </TableCell>
                          <TableCell className="py-2.5 px-4 text-right hidden md:table-cell">
                            {s.parse_failures > 0 ? (
                              <Badge
                                variant="outline"
                                className="font-mono text-xs text-red-600 border-red-300 dark:text-red-400 dark:border-red-700"
                              >
                                {s.parse_failures}
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

              <Card className="rounded-md border shadow-none">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Patient-level Results</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    All patients · click any row to open drill-down
                  </p>
                </CardHeader>
                <CardContent>
                  <ModelPatientTable
                    rows={modelRows}
                    strategies={meta.strategies}
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
