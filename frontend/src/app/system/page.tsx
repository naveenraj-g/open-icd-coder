import type { Metadata } from "next"
import { CheckCircle2Icon, ExternalLinkIcon, XCircleIcon } from "lucide-react"

import { PageHeader } from "@/components/page-header"
import { Badge } from "@/components/ui/badge"
import { LinkButton } from "@/components/link-button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { API_URL, api, unwrap } from "@/lib/api/client"
import { ITEM_TYPE, pct } from "@/lib/labels"

export const metadata: Metadata = { title: "Status & engines" }

async function readiness(): Promise<{ ok: boolean; database: string }> {
  try {
    const r = await fetch(`${API_URL}/health/ready`, { cache: "no-store" })
    const body = (await r.json()) as { checks?: { database?: string } }
    return { ok: r.ok, database: body.checks?.database ?? "unknown" }
  } catch {
    return { ok: false, database: "unreachable" }
  }
}

export default async function SystemPage() {
  const [ready, systems, settings] = await Promise.all([
    readiness(),
    api.GET("/api/v1/terminology/code-systems").then(unwrap),
    api.GET("/api/v1/coding/settings").then(unwrap),
  ])

  return (
    <>
      <PageHeader
        title="Status & engines"
        description="Backend health, terminology coverage, and the decision engines the pipeline can use."
        actions={
          <LinkButton variant="outline" href={`${API_URL}/docs`} external>
            API docs <ExternalLinkIcon />
          </LinkButton>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Backend</CardTitle>
            <CardDescription className="font-mono">{API_URL}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Check ok label="API reachable" />
            <Check ok={ready.database === "ok"} label={`Database: ${ready.database}`} />
            <p className="pt-2 text-xs text-muted-foreground">
              Semantic and hybrid search also need LM Studio (embeddings) running; the decision engine needs its API key.
            </p>
          </CardContent>
        </Card>

        {systems.data.map((cs) => (
          <Card key={cs.id} className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">
                {cs.name} {cs.version}
              </CardTitle>
              <CardDescription>
                {cs.title} · {cs.publisher}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <Coverage
                label="Codes"
                detail={`${cs.concept_count.toLocaleString()} loaded · ${cs.embedded_count.toLocaleString()} embedded`}
                value={cs.concept_count ? cs.embedded_count / cs.concept_count : 0}
              />
              <Coverage
                label="Alphabetic Index terms"
                detail={`${cs.index_term_count.toLocaleString()} loaded · ${cs.index_terms_embedded.toLocaleString()} embedded`}
                value={cs.index_term_count ? cs.index_terms_embedded / cs.index_term_count : 0}
              />
              <p className="text-xs text-muted-foreground">Embedding model: {cs.embedding_model}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Decision engines</CardTitle>
          <CardDescription>
            Selectable per encounter or on rescore. The default is used when none is chosen.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {settings.engines.map((e) => (
                <TableRow key={e.name}>
                  <TableCell className="font-medium">
                    {e.name} {e.is_default && <Badge className="ml-1">default</Badge>}
                  </TableCell>
                  <TableCell>{e.kind === "stand_in" ? "Stand-in" : "Decision model"}</TableCell>
                  <TableCell>{e.route ?? "—"}</TableCell>
                  <TableCell className="font-mono text-xs">{e.model}</TableCell>
                  <TableCell className="max-w-md whitespace-normal text-xs text-amber-700 dark:text-amber-300">
                    {e.warning ?? ""}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Coding thresholds</CardTitle>
          <CardDescription>From backend configs/config.yaml</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-5">
          <Setting label="Coded item types" value={settings.coded_item_types.map((t) => ITEM_TYPE[t] ?? t).join(", ")} />
          <Setting label="Candidates per item" value={settings.candidates_per_item} />
          <Setting label="Alternatives shown" value={settings.alternatives_shown} />
          <Setting label="Low-confidence below" value={pct(settings.low_confidence_threshold, 0)} />
          <Setting label="None-of-the-above flag at" value={pct(settings.nota_flag_threshold, 0)} />
        </CardContent>
      </Card>
    </>
  )
}

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      {ok ? (
        <CheckCircle2Icon className="size-4 text-emerald-600" />
      ) : (
        <XCircleIcon className="size-4 text-destructive" />
      )}
      {label}
    </div>
  )
}

function Coverage({ label, detail, value }: { label: string; detail: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">
          {detail} ({pct(value, 0)})
        </span>
      </div>
      <Progress value={value * 100} aria-label={`${label} embedded`} />
    </div>
  )
}

function Setting({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  )
}
