import { NextRequest, NextResponse } from "next/server"
import fs from "fs"
import path from "path"

const ALLOWED_FILES = new Set(["prompt", "input"])

function sanitizeSegment(segment: string): string {
  // Allow only alphanumeric, hyphens, underscores, dots — no path traversal
  return segment.replace(/[^a-zA-Z0-9\-_.]/g, "")
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const model = sanitizeSegment(searchParams.get("model") ?? "")
  const strategy = sanitizeSegment(searchParams.get("strategy") ?? "")
  const patientId = sanitizeSegment(searchParams.get("patientId") ?? "")
  const file = searchParams.get("file") ?? ""

  if (!model || !strategy || !patientId || !ALLOWED_FILES.has(file)) {
    return NextResponse.json({ error: "Invalid parameters" }, { status: 400 })
  }

  // Resolve to: <project_root>/output/intermediate/<model>/<strategy>/<patientId>/<file>.txt
  const projectRoot = path.join(process.cwd(), "..")
  const filePath = path.join(
    projectRoot,
    "output",
    "intermediate",
    model,
    strategy,
    patientId,
    `${file}.txt`,
  )

  // Verify the resolved path stays within the intended directory (prevent traversal)
  const allowedBase = path.join(projectRoot, "output", "intermediate")
  if (!filePath.startsWith(allowedBase + path.sep)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 })
  }

  const content = fs.readFileSync(filePath, "utf-8")
  return new NextResponse(content, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  })
}
