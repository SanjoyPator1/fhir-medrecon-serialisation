"use client"

import { useState, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { PatientTable } from "./PatientTable"
import type { PatientSummary } from "@/lib/aggregations"

interface PatientSearchProps {
  patients: PatientSummary[]
}

export function PatientSearch({ patients }: PatientSearchProps) {
  const [query, setQuery] = useState("")

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return patients
    return patients.filter(
      (p) =>
        p.patient_id.toLowerCase().includes(q) ||
        p.patient_name.toLowerCase().includes(q),
    )
  }, [query, patients])

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <Input
          type="search"
          placeholder="Search by patient ID or name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-9 h-9 text-sm font-mono"
        />
      </div>
      <p className="text-xs text-muted-foreground">
        {filtered.length === patients.length
          ? `${patients.length} patients`
          : `${filtered.length} of ${patients.length} patients`}
      </p>
      <PatientTable patients={filtered} />
    </div>
  )
}
