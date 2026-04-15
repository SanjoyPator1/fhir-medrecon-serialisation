import type { Metadata } from "next"
import { Plus_Jakarta_Sans, Geist_Mono } from "next/font/google"
import "./globals.css"
import { Providers } from "@/components/providers"
import { Sidebar } from "@/components/layout/sidebar"
import { TopBar } from "@/components/layout/top-bar"
import { ThemeToggle } from "@/components/layout/theme-toggle"

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "FHIR MedRecon — Serialisation Study",
  description:
    "LLM serialisation strategy benchmarks for medication reconciliation across 200 synthetic FHIR R4 patients.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${jakarta.variable} ${geistMono.variable}`}
    >
      <body className="bg-background text-foreground antialiased">
        <Providers>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
              {/* Desktop header bar */}
              <header className="hidden lg:flex items-center justify-between h-14 px-6 border-b border-border bg-background shrink-0 z-40">
                <p className="text-sm text-muted-foreground">
                  Medication Reconciliation Benchmark
                </p>
                <ThemeToggle />
              </header>
              {/* Mobile top bar */}
              <TopBar />
              <main className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
                <div className="max-w-7xl mx-auto">
                  {children}
                </div>
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  )
}
