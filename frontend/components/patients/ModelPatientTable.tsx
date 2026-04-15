"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { STRATEGY_SHORT } from "@/lib/constants"
import type { ExperimentRow } from "@/lib/data"
import type { GroundTruth } from "@/lib/data"

interface PatientModelRow {
  patient_id: string
  patient_name: string
  active_med_count: number
  mean_f1: number
  strategies: Record<string, { f1: number; parse_failed: boolean } | undefined>
}

interface ModelPatientTableProps {
  rows: ExperimentRow[]
  strategies: string[]
  groundTruth: Record<string, GroundTruth>
}

type SortKey = "patient_id" | "active_med_count" | "mean_f1"
type SortDir = "asc" | "desc"

function f1Cell(entry: { f1: number; parse_failed: boolean } | undefined) {
  if (!entry) return <span className="text-muted-foreground text-xs font-mono">—</span>
  if (entry.parse_failed) return (
    <Badge variant="outline" className="font-mono text-xs text-red-600 border-red-300 dark:text-red-400 dark:border-red-700">
      fail
    </Badge>
  )
  const f1 = entry.f1
  const cls = f1 >= 0.75
    ? "text-emerald-700 dark:text-emerald-300"
    : f1 >= 0.45
    ? "text-amber-700 dark:text-amber-300"
    : "text-red-700 dark:text-red-300"
  return <span className={cn("font-mono text-xs font-semibold", cls)}>{f1.toFixed(3)}</span>
}

const PAGE_SIZE = 50

export function ModelPatientTable({ rows, strategies, groundTruth }: ModelPatientTableProps) {
  const [query, setQuery] = useState("")
  const [sortKey, setSortKey] = useState<SortKey>("mean_f1")
  const [sortDir, setSortDir] = useState<SortDir>("asc")
  const [page, setPage] = useState(0)

  const tableRows = useMemo<PatientModelRow[]>(() => {
    const byPatient = new Map<string, ExperimentRow[]>()
    for (const r of rows) {
      const list = byPatient.get(r.patient_id) ?? []
      list.push(r)
      byPatient.set(r.patient_id, list)
    }
    const result: PatientModelRow[] = []
    for (const [patient_id, patRows] of byPatient) {
      const gt = groundTruth[patient_id]
      const mean_f1 = patRows.length
        ? patRows.reduce((s, r) => s + r.f1, 0) / patRows.length
        : 0
      const stratMap: PatientModelRow["strategies"] = {}
      for (const r of patRows) {
        stratMap[r.strategy] = { f1: r.f1, parse_failed: r.parse_failed }
      }
      result.push({
        patient_id,
        patient_name: gt?.patient_name ?? "",
        active_med_count: gt?.active_medication_count ?? 0,
        mean_f1,
        strategies: stratMap,
      })
    }
    return result
  }, [rows, groundTruth])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q
      ? tableRows.filter(
          (r) => r.patient_id.toLowerCase().includes(q) || r.patient_name.toLowerCase().includes(q),
        )
      : tableRows
  }, [tableRows, query])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortKey === "patient_id") cmp = a.patient_id.localeCompare(b.patient_id)
      else if (sortKey === "active_med_count") cmp = a.active_med_count - b.active_med_count
      else cmp = a.mean_f1 - b.mean_f1
      return sortDir === "asc" ? cmp : -cmp
    })
  }, [filtered, sortKey, sortDir])

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    else { setSortKey(key); setSortDir("asc") }
    setPage(0)
  }

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const pageItems = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <span className="ml-1 text-muted-foreground/40">↕</span>
    return <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <div className="relative max-w-xs">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <Input
            type="search"
            placeholder="Filter by patient ID or name…"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(0) }}
            className="pl-9 h-8 text-xs font-mono"
          />
        </div>
        <p className="text-xs text-muted-foreground shrink-0">
          {filtered.length === tableRows.length ? `${tableRows.length} patients` : `${filtered.length} / ${tableRows.length}`}
        </p>
      </div>

      <div className="border border-border rounded-md overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-b">
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none sticky left-0 bg-background z-10"
                onClick={() => handleSort("patient_id")}
              >
                Patient <SortIcon k="patient_id" />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium text-right cursor-pointer select-none hidden md:table-cell"
                onClick={() => handleSort("active_med_count")}
              >
                Meds <SortIcon k="active_med_count" />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium text-right cursor-pointer select-none"
                onClick={() => handleSort("mean_f1")}
              >
                Mean F1 <SortIcon k="mean_f1" />
              </TableHead>
              {strategies.map((s) => (
                <TableHead key={s} className="text-xs uppercase text-muted-foreground font-medium text-center min-w-[80px]">
                  {STRATEGY_SHORT[s] ?? s}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {pageItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={3 + strategies.length} className="text-center text-muted-foreground py-8 text-sm">
                  No patients found
                </TableCell>
              </TableRow>
            )}
            {pageItems.map((p) => {
              const hasFailure = strategies.some((s) => p.strategies[s]?.parse_failed)
              return (
                <TableRow
                  key={p.patient_id}
                  className={cn(
                    "border-b border-border/50 hover:bg-muted/50",
                    hasFailure && "bg-red-50/40 dark:bg-red-950/10",
                  )}
                >
                  <TableCell className="py-2 sticky left-0 bg-inherit z-10">
                    <Link
                      href={`/patients/${p.patient_id}`}
                      className="font-mono text-xs text-foreground hover:text-primary underline-offset-2 hover:underline"
                    >
                      {p.patient_id.slice(0, 8)}…
                    </Link>
                    <span className="ml-2 text-xs text-muted-foreground hidden md:inline">{p.patient_name}</span>
                  </TableCell>
                  <TableCell className="py-2 text-right font-mono text-xs text-muted-foreground hidden md:table-cell">
                    {p.active_med_count}
                  </TableCell>
                  <TableCell className="py-2 text-right">
                    <span className={cn(
                      "font-mono text-xs font-semibold",
                      p.mean_f1 >= 0.75 ? "text-emerald-700 dark:text-emerald-300"
                        : p.mean_f1 >= 0.45 ? "text-amber-700 dark:text-amber-300"
                        : "text-red-700 dark:text-red-300",
                    )}>
                      {p.mean_f1.toFixed(3)}
                    </span>
                  </TableCell>
                  {strategies.map((s) => (
                    <TableCell key={s} className="py-2 text-center">
                      {f1Cell(p.strategies[s])}
                    </TableCell>
                  ))}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Page {page + 1} of {totalPages}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
              className="px-2 py-1 rounded border border-border disabled:opacity-40 hover:bg-muted">Previous</button>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="px-2 py-1 rounded border border-border disabled:opacity-40 hover:bg-muted">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
