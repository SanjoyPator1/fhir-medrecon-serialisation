import { loadExperiments } from "@/lib/data"
import { getPatientSummaries } from "@/lib/aggregations"
import { PatientSearch } from "@/components/patients/PatientSearch"

export default function PatientsPage() {
  const { rows, ground_truth } = loadExperiments()
  const patients = getPatientSummaries(rows, ground_truth)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Patient Explorer</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Search by patient ID or name · click any row to see full model results and medication diff
        </p>
      </div>
      <PatientSearch patients={patients} />
    </div>
  )
}
