"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, ResponsiveContainer, Tooltip } from "recharts"
import { STRATEGY_SHORT } from "@/lib/constants"

interface MetricBarChartProps {
  data: { strategy: string; mean_f1: number; mean_precision: number; mean_recall: number }[]
}

export function MetricBarChart({ data }: MetricBarChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    name: STRATEGY_SHORT[d.strategy] ?? d.strategy,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={formatted} barCategoryGap="25%" barGap={3}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[0, 1]}
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => v.toFixed(1)}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--color-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "6px",
            fontSize: "12px",
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any) => Number(value).toFixed(4)}
          cursor={{ fill: "var(--color-muted)", opacity: 0.4 }}
        />
        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
        <Bar dataKey="mean_f1" name="F1" fill="var(--color-chart-1)" radius={[3, 3, 0, 0]} />
        <Bar dataKey="mean_precision" name="Precision" fill="var(--color-chart-2)" radius={[3, 3, 0, 0]} />
        <Bar dataKey="mean_recall" name="Recall" fill="var(--color-chart-3)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
