"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts"

interface F1DistributionChartProps {
  data: { bin: string; count: number; pct: number }[]
}

function binColor(bin: string): string {
  const lower = parseFloat(bin.split("–")[0])
  if (lower >= 0.7) return "var(--color-chart-2)"
  if (lower >= 0.5) return "var(--color-chart-1)"
  if (lower >= 0.3) return "var(--color-chart-4)"
  return "var(--color-chart-5)"
}

export function F1DistributionChart({ data }: F1DistributionChartProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barCategoryGap="10%">
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis
          dataKey="bin"
          tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          angle={-30}
          textAnchor="end"
          height={42}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--color-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "6px",
            fontSize: "12px",
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any, _name: any, props: any) => [
            `${value} patients (${((props?.payload?.pct ?? 0) * 100).toFixed(1)}%)`,
            "Count",
          ]}
          cursor={{ fill: "var(--color-muted)", opacity: 0.4 }}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.bin} fill={binColor(entry.bin)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
