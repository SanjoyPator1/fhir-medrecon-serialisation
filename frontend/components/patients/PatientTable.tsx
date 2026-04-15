"use client"

import { useState } from "react"
import Link from "next/link"
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
import type { PatientSummary } from "@/lib/aggregations"

type SortKey = keyof PatientSummary
type SortDir = "asc" | "desc"

const PAGE_SIZE = 50

interface PatientTableProps {
  patients: PatientSummary[]
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active)
    return <span className="ml-1 text-muted-foreground/40">↕</span>
  return <span className="ml-1">{dir === "asc" ? "↑" : "↓"}</span>
}

function f1Badge(f1: number) {
  if (f1 >= 0.75)
    return <Badge variant="outline" className="font-mono text-xs text-emerald-700 border-emerald-300 dark:text-emerald-300 dark:border-emerald-700">{f1.toFixed(3)}</Badge>
  if (f1 >= 0.45)
    return <Badge variant="outline" className="font-mono text-xs text-amber-700 border-amber-300 dark:text-amber-300 dark:border-amber-700">{f1.toFixed(3)}</Badge>
  return <Badge variant="outline" className="font-mono text-xs text-red-700 border-red-300 dark:text-red-300 dark:border-red-700">{f1.toFixed(3)}</Badge>
}

export function PatientTable({ patients }: PatientTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("patient_id")
  const [sortDir, setSortDir] = useState<SortDir>("asc")
  const [page, setPage] = useState(0)

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
    setPage(0)
  }

  const sorted = [...patients].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number)
    return sortDir === "asc" ? cmp : -cmp
  })

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const pageItems = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <div className="space-y-3">
      <div className="border border-border rounded-md overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-b">
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none whitespace-nowrap"
                onClick={() => handleSort("patient_id")}
              >
                Patient ID <SortIcon active={sortKey === "patient_id"} dir={sortDir} />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none hidden md:table-cell"
                onClick={() => handleSort("patient_name")}
              >
                Name <SortIcon active={sortKey === "patient_name"} dir={sortDir} />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none text-right"
                onClick={() => handleSort("active_med_count")}
              >
                Active Meds <SortIcon active={sortKey === "active_med_count"} dir={sortDir} />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none text-right"
                onClick={() => handleSort("best_f1")}
              >
                Best F1 <SortIcon active={sortKey === "best_f1"} dir={sortDir} />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none text-right"
                onClick={() => handleSort("mean_f1")}
              >
                Mean F1 <SortIcon active={sortKey === "mean_f1"} dir={sortDir} />
              </TableHead>
              <TableHead
                className="text-xs uppercase text-muted-foreground font-medium cursor-pointer select-none text-right hidden md:table-cell"
                onClick={() => handleSort("parse_failures")}
              >
                Failures <SortIcon active={sortKey === "parse_failures"} dir={sortDir} />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pageItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8 text-sm">
                  No patients found
                </TableCell>
              </TableRow>
            )}
            {pageItems.map((p) => (
              <TableRow
                key={p.patient_id}
                className="hover:bg-muted/50 border-b border-border/50 cursor-pointer"
              >
                <TableCell className="py-2.5">
                  <Link
                    href={`/patients/${p.patient_id}`}
                    className="font-mono text-xs text-foreground hover:text-primary underline-offset-2 hover:underline"
                  >
                    {p.patient_id.slice(0, 8)}…
                  </Link>
                </TableCell>
                <TableCell className="py-2.5 text-sm hidden md:table-cell">
                  {p.patient_name || "—"}
                </TableCell>
                <TableCell className="py-2.5 text-right font-mono text-sm">
                  {p.active_med_count}
                </TableCell>
                <TableCell className="py-2.5 text-right">
                  {f1Badge(p.best_f1)}
                </TableCell>
                <TableCell className="py-2.5 text-right">
                  {f1Badge(p.mean_f1)}
                </TableCell>
                <TableCell className="py-2.5 text-right font-mono text-sm hidden md:table-cell">
                  <span className={cn(p.parse_failures > 0 ? "text-red-600 dark:text-red-400" : "text-muted-foreground")}>
                    {p.parse_failures}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2 py-1 rounded border border-border disabled:opacity-40 hover:bg-muted"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2 py-1 rounded border border-border disabled:opacity-40 hover:bg-muted"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
