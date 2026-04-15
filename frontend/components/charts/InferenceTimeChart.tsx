"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { MODEL_LABELS, STRATEGY_SHORT } from "@/lib/constants"

interface InferenceTimeChartProps {
  data: { model: string; [strategy: string]: number | string }[]
  strategies: string[]
}

const COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
]

export function InferenceTimeChart({ data, strategies }: InferenceTimeChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    name: (MODEL_LABELS[d.model as string] ?? (d.model as string))
      .replace(" (3.8B)", "")
      .replace(" v0.3", ""),
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={formatted} barCategoryGap="20%" barGap={2}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${v}s`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--color-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "6px",
            fontSize: "12px",
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any) => [`${Number(value).toFixed(2)}s`, ""]}
          cursor={{ fill: "var(--color-muted)", opacity: 0.4 }}
        />
        <Legend
          wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
          formatter={(value: string) => STRATEGY_SHORT[value] ?? value}
        />
        {strategies.map((s, i) => (
          <Bar
            key={s}
            dataKey={s}
            name={s}
            fill={COLORS[i % COLORS.length]}
            radius={[3, 3, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
