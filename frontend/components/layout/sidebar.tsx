import { NavLinks } from "./nav-links"

export function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-56 shrink-0 border-r border-border bg-background h-full overflow-y-auto">
      <div className="px-4 py-5 border-b border-border">
        <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
          FHIR MedRecon
        </p>
        <p className="text-sm font-semibold mt-0.5">Serialisation Study</p>
      </div>
      <div className="flex-1 px-3 py-4">
        <NavLinks />
      </div>
      <div className="px-4 py-4 border-t border-border">
        <p className="text-xs text-muted-foreground">
          200 patients · 5 models · 4 strategies
        </p>
      </div>
    </aside>
  )
}
