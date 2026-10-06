import { AlertTriangleIcon, ArrowRightIcon, FilePlus2Icon } from "lucide-react"
import Link from "next/link"

import { EncounterTable } from "@/components/coding/encounter-table"
import { PageHeader } from "@/components/page-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { LinkButton } from "@/components/link-button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { api, unwrap } from "@/lib/api/client"

async function count(query: { queue?: string; status?: string; reviewed?: boolean }) {
  const res = unwrap(await api.GET("/api/v1/coding/encounters", { params: { query: { ...query, limit: 1 } } }))
  return res.total
}

export default async function DashboardPage() {
  const [settings, systems, standard, close, reviewed, failed, recent] = await Promise.all([
    api.GET("/api/v1/coding/settings").then(unwrap),
    api.GET("/api/v1/terminology/code-systems").then(unwrap),
    count({ queue: "standard", reviewed: false }),
    count({ queue: "close_review", reviewed: false }),
    count({ reviewed: true }),
    count({ status: "failed" }),
    api.GET("/api/v1/coding/encounters", { params: { query: { limit: 8 } } }).then(unwrap),
  ])
  const engine = settings.engines.find((e) => e.name === settings.default_engine)
  const icd = systems.data[0]

  const stats = [
    {
      label: "Awaiting review",
      value: standard,
      help: "Standard queue — nothing flagged",
      href: "/coding/encounters?queue=standard&reviewed=false",
    },
    {
      label: "Close review",
      value: close,
      help: "Flagged or failed items",
      href: "/coding/encounters?queue=close_review&reviewed=false",
      warn: close > 0,
    },
    { label: "Human reviewed", value: reviewed, help: "Approved encounters", href: "/coding/encounters?reviewed=true" },
    { label: "Failed", value: failed, help: "Every coded item failed", href: "/coding/encounters?status=failed" },
  ]

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Condition notes go through hybrid search, then the Jev decision engine, then human review."
        actions={
          <LinkButton href="/coding/new">
            <FilePlus2Icon />
            New encounter
          </LinkButton>
        }
      />

      {engine?.warning && (
        <Alert className="mb-6">
          <AlertTriangleIcon />
          <AlertTitle>
            Default engine: {engine.name} ({engine.model})
          </AlertTitle>
          <AlertDescription>{engine.warning}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Link key={s.label} href={s.href} className="group">
            <Card className="h-full transition-colors group-hover:bg-muted/40">
              <CardHeader>
                <CardDescription>{s.label}</CardDescription>
                <CardTitle className={`text-3xl tabular-nums ${s.warn ? "text-amber-700 dark:text-amber-300" : ""}`}>
                  {s.value}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">{s.help}</CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent encounters</CardTitle>
              <CardDescription>Latest submissions, newest first</CardDescription>
            </div>
            <LinkButton variant="ghost" size="sm" href="/coding/encounters">
              Review queue <ArrowRightIcon />
            </LinkButton>
          </CardHeader>
          <CardContent>
            {recent.data.length ? (
              <EncounterTable rows={recent.data} />
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No encounters yet</EmptyTitle>
                  <EmptyDescription>
                    Submit a SOAP note with its conditions from <Link href="/coding/new">New encounter</Link>.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>What runs on each condition</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <Step n={1} title="Hybrid search">
              Top {settings.candidates_per_item} of {icd ? icd.concept_count.toLocaleString() : "—"} ICD-10-CM{" "}
              {icd?.version} codes (text + semantic + Alphabetic Index)
            </Step>
            <Step n={2} title="Decision engine">
              {engine ? `${engine.name} → ${engine.model}` : settings.default_engine} scores every candidate plus
              &ldquo;none of the above&rdquo;
            </Step>
            <Step n={3} title="Flag & route">
              Below {Math.round(settings.low_confidence_threshold * 100)}% → low confidence; NOTA ≥{" "}
              {Math.round(settings.nota_flag_threshold * 100)}% → none of the above; either → close review
            </Step>
            <Step n={4} title="Human review">
              Approve, override or remove each code, then approve the encounter
            </Step>
            <LinkButton variant="outline" size="sm" className="w-full" href="/system">
              Status & engines
            </LinkButton>
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
        {n}
      </span>
      <div>
        <div className="font-medium">{title}</div>
        <div className="text-muted-foreground">{children}</div>
      </div>
    </div>
  )
}
