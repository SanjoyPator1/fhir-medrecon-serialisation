import { loadExperiments, MODEL_LABELS, STRATEGY_LABELS } from "@/lib/data"
import { sortModelsBySize } from "@/lib/constants"
import {
  pivotByModelStrategy,
  heatmapData,
  overallModelRanking,
  overallStrategyRanking,
} from "@/lib/aggregations"
import { MetricCard } from "@/components/layout/metric-card"
import { F1HeatmapChart } from "@/components/charts/F1HeatmapChart"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function OverviewPage() {
  const { meta, rows } = loadExperiments()
  const pivot = pivotByModelStrategy(rows)
  const orderedModels = sortModelsBySize(meta.models)
  const heatmap = heatmapData(pivot, orderedModels, meta.strategies)
  const modelRanking = overallModelRanking(rows, meta.models)
  const stratRanking = overallStrategyRanking(rows, meta.strategies)
  const totalParseFailures = rows.filter((r) => r.parse_failed).length

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Medication reconciliation accuracy across {meta.total_patients} patients ·{" "}
          {meta.models.length} models · {meta.strategies.length} strategies
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Patients"
          value={meta.total_patients}
          sub={`${meta.total_runs} total runs`}
        />
        <MetricCard
          label="Mean F1 (all)"
          value={meta.mean_f1_overall.toFixed(3)}
          sub="across all models & strategies"
        />
        <MetricCard
          label="Best Model"
          value={MODEL_LABELS[meta.best_model] ?? meta.best_model}
          sub="by mean F1 across strategies"
        />
        <MetricCard
          label="Best Strategy"
          value={
            STRATEGY_LABELS[meta.best_strategy]?.split("—")[1]?.trim() ??
            meta.best_strategy
          }
          sub="by mean F1 across models"
        />
      </div>

      {totalParseFailures > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20 text-sm">
          <span className="text-amber-700 dark:text-amber-400 font-medium">
            {totalParseFailures} parse failures
          </span>
          <span className="text-amber-600 dark:text-amber-500">
            counted as F1 = 0 in all metrics
          </span>
        </div>
      )}

      <Card className="rounded-md border shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">
            F1 Score — Model × Strategy Heatmap
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Mean F1 across all patients · cells with fewer runs marked —
          </p>
        </CardHeader>
        <CardContent>
          <F1HeatmapChart data={heatmap} strategies={meta.strategies} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="rounded-md border shadow-none">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Model Rankings</CardTitle>
          </CardHeader>
          <CardContent className="p-0 pb-2">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent border-b">
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium px-4">
                    Model
                  </TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">
                    F1
                  </TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4 hidden md:table-cell">
                    Precision
                  </TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4 hidden md:table-cell">
                    Recall
                  </TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">
                    Failures
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {modelRanking.map((m, i) => (
                  <TableRow
                    key={m.model}
                    className="hover:bg-muted/50 border-b border-border/50"
                  >
                    <TableCell className="py-2.5 px-4 text-sm">
                      <span className="text-xs text-muted-foreground font-mono mr-2">
                        {i + 1}
                      </span>
                      {MODEL_LABELS[m.model] ?? m.model}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm font-semibold">
                      {m.mean_f1.toFixed(3)}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground hidden md:table-cell">
                      {m.mean_precision.toFixed(3)}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground hidden md:table-cell">
                      {m.mean_recall.toFixed(3)}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right">
                      {m.parse_failures > 0 ? (
                        <Badge
                          variant="outline"
                          className="font-mono text-xs text-red-600 border-red-300 dark:text-red-400 dark:border-red-700"
                        >
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

        <Card className="rounded-md border shadow-none">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Strategy Rankings</CardTitle>
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
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4 hidden md:table-cell">
                    Precision
                  </TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4 hidden md:table-cell">
                    Recall
                  </TableHead>
                  <TableHead className="text-xs uppercase text-muted-foreground font-medium text-right px-4">
                    Avg time
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stratRanking.map((s, i) => (
                  <TableRow
                    key={s.strategy}
                    className="hover:bg-muted/50 border-b border-border/50"
                  >
                    <TableCell className="py-2.5 px-4 text-sm">
                      <span className="text-xs text-muted-foreground font-mono mr-2">
                        {i + 1}
                      </span>
                      {STRATEGY_LABELS[s.strategy] ?? s.strategy}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm font-semibold">
                      {s.mean_f1.toFixed(3)}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground hidden md:table-cell">
                      {s.mean_precision.toFixed(3)}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground hidden md:table-cell">
                      {s.mean_recall.toFixed(3)}
                    </TableCell>
                    <TableCell className="py-2.5 px-4 text-right font-mono text-sm text-muted-foreground">
                      {s.mean_inference_time.toFixed(1)}s
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
