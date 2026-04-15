import { notFound } from "next/navigation"
import Link from "next/link"
import { loadExperiments } from "@/lib/data"
import { sortModelsBySize } from "@/lib/constants"
import { getPatientRows } from "@/lib/aggregations"
import { MetricCard } from "@/components/layout/metric-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DrilldownClient } from "./DrilldownClient"

interface PageProps {
  params: Promise<{ id: string }>
}

export async function generateStaticParams() {
  const { ground_truth } = loadExperiments()
  return Object.keys(ground_truth).map((id) => ({ id }))
}

export default async function PatientDrilldownPage({ params }: PageProps) {
  const { id } = await params
  const { rows, ground_truth, meta } = loadExperiments()
  const gt = ground_truth[id]
  if (!gt) notFound()

  const patientRows = getPatientRows(rows, id)
  const meanF1 = patientRows.length
    ? patientRows.reduce((s, r) => s + r.f1, 0) / patientRows.length
    : 0
  const bestF1 = patientRows.length ? Math.max(...patientRows.map((r) => r.f1)) : 0
  const parseFailures = patientRows.filter((r) => r.parse_failed).length

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Patients
        </Link>
        <span>/</span>
        <span className="font-mono text-xs">{id}</span>
      </div>

      {/* Patient header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{gt.patient_name || "Unknown"}</h1>
        <div className="flex flex-wrap gap-3 text-sm text-muted-foreground font-mono">
          <span>{gt.birth_date}</span>
          <span>{gt.gender}</span>
          <span>{gt.history_span_years}yr history</span>
          <span>{gt.total_medication_requests} total medication requests</span>
        </div>
        <p className="text-xs font-mono text-muted-foreground break-all mt-1">{id}</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Medications"
          value={gt.active_medication_count}
          sub="ground truth"
        />
        <MetricCard label="Best F1" value={bestF1.toFixed(3)} sub="across all runs" />
        <MetricCard label="Mean F1" value={meanF1.toFixed(3)} sub="all models & strategies" />
        <MetricCard
          label="Parse Failures"
          value={parseFailures}
          sub={`of ${patientRows.length} runs`}
        />
      </div>

      {/* Ground truth medications */}
      <Card className="rounded-md border shadow-none">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold">Ground Truth — Active Medications</CardTitle>
            <Badge variant="secondary" className="font-mono text-xs">
              {gt.active_medication_count} active
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {gt.medications.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active medications on record.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {gt.medications.map((med, i) => (
                <span
                  key={i}
                  className="inline-block px-2 py-1 rounded border border-border bg-muted/40 font-mono text-xs"
                >
                  {med}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Interactive grid + diff */}
      <DrilldownClient
        rows={patientRows}
        groundTruth={gt}
        models={sortModelsBySize(meta.models)}
        strategies={meta.strategies}
      />
    </div>
  )
}
