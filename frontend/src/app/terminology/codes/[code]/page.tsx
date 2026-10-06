import type { Metadata } from "next"
import { ArrowUpIcon } from "lucide-react"
import Link from "next/link"
import { notFound } from "next/navigation"

import { PageHeader } from "@/components/page-header"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { api, unwrap } from "@/lib/api/client"
import type { ConceptSummary } from "@/lib/api/types"
import { NOTE_KINDS } from "@/lib/labels"

export async function generateMetadata(props: PageProps<"/terminology/codes/[code]">): Promise<Metadata> {
  const { code } = await props.params
  return { title: decodeURIComponent(code) }
}

export default async function CodePage(props: PageProps<"/terminology/codes/[code]">) {
  const { code } = await props.params
  const res = await api.GET("/api/v1/terminology/concepts/{code}", {
    params: { path: { code: decodeURIComponent(code) } },
  })
  if (res.response.status === 404) notFound()
  const c = unwrap(res)

  return (
    <>
      <PageHeader
        title={
          <span className="flex flex-wrap items-baseline gap-3">
            <span className="font-mono">{c.code}</span>
            <span className="text-lg font-normal">{c.display}</span>
          </span>
        }
        description={`ICD-10-CM ${c.version}${c.short_display ? ` · short: ${c.short_display}` : ""}`}
      >
        <div className="flex gap-2 pt-1">
          {c.is_billable ? (
            <Badge>Billable</Badge>
          ) : (
            <Badge variant="outline">Category header — not billable</Badge>
          )}
        </div>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Instructional notes</CardTitle>
              <CardDescription>From the tabular list — on this code, and inherited from its categories</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <Notes notes={c.notes} />
              {c.inherited_notes.map((inh) => (
                <div key={inh.code} className="space-y-2 rounded-lg border p-3">
                  <div className="text-sm">
                    Inherited from{" "}
                    <CodeLink code={inh.code} /> <span className="text-muted-foreground">{inh.display}</span>
                  </div>
                  <Notes notes={inh.notes} />
                </div>
              ))}
              {Object.keys(c.notes).length === 0 && c.inherited_notes.length === 0 && (
                <p className="text-sm text-muted-foreground">No instructional notes for this code or its categories.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Inclusion terms</CardTitle>
              <CardDescription>Synonyms from the tabular list (searchable)</CardDescription>
            </CardHeader>
            <CardContent>
              {c.synonyms.length ? (
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {c.synonyms.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">None.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="lg:self-start">
          <CardHeader>
            <CardTitle className="text-base">Hierarchy</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <div className="mb-1 text-muted-foreground">Parent</div>
              {c.parent ? (
                <SummaryLink s={c.parent} icon />
              ) : (
                <span className="text-muted-foreground">Top-level category</span>
              )}
            </div>
            <div>
              <div className="mb-1 text-muted-foreground">Children ({c.children.length})</div>
              {c.children.length ? (
                <ul className="space-y-1">
                  {c.children.map((ch) => (
                    <li key={ch.code}>
                      <SummaryLink s={ch} />
                    </li>
                  ))}
                </ul>
              ) : (
                <span className="text-muted-foreground">None — most specific level</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function CodeLink({ code }: { code: string }) {
  return (
    <Link href={`/terminology/codes/${encodeURIComponent(code)}`} className="font-mono font-medium hover:underline">
      {code}
    </Link>
  )
}

function SummaryLink({ s, icon }: { s: ConceptSummary; icon?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      {icon && <ArrowUpIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />}
      <div>
        <CodeLink code={s.code} />{" "}
        {!s.is_billable && <span className="text-xs text-muted-foreground">(header)</span>}
        <div className="text-muted-foreground">{s.display}</div>
      </div>
    </div>
  )
}

function Notes({ notes }: { notes: Record<string, string[]> }) {
  const entries = Object.entries(notes)
  if (!entries.length) return null
  return (
    <dl className="space-y-3">
      {entries.map(([kind, items]) => (
        <div key={kind}>
          <dt className="text-sm font-medium">{NOTE_KINDS[kind] ?? kind}</dt>
          <dd>
            <ul className="list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
              {items.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </dd>
        </div>
      ))}
    </dl>
  )
}
