"use client"

import { SearchIcon } from "lucide-react"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import * as React from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, errorMessage, unwrap } from "@/lib/api/client"
import type { SearchMode, SearchResponse } from "@/lib/api/types"

const MODES: { value: SearchMode; label: string; help: string }[] = [
  { value: "hybrid", label: "Hybrid", help: "Text and semantic rankings fused — the pipeline's default" },
  { value: "text", label: "Text", help: "Full-text + trigram over descriptions, inclusion terms and the Alphabetic Index" },
  { value: "semantic", label: "Semantic", help: "Embedding similarity (Qwen3) — handles lay wording like “heart attack”" },
]

const TRY = ["heart attack", "acute appendicitis with localized peritonitis", "Variola", "HTN", "K35.3"]

/** Query, mode and filter live in the URL — searches are shareable. */
export function SearchPanel() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  const q = params.get("q") ?? ""
  const mode = (params.get("mode") as SearchMode) ?? "hybrid"
  const billableOnly = params.get("billable") === "1"

  const key = `${mode}|${billableOnly}|${q}`
  // Results remember which search they answer, so "loading" is derived
  // rather than set synchronously inside the effect.
  const [result, setResult] = React.useState<{
    key: string
    res: SearchResponse | null
    error: string | null
    ms: number | null
  }>({ key: "", res: null, error: null, ms: null })

  const active = q.trim().length > 0
  const current = result.key === key
  const loading = active && !current
  const res = active ? result.res : null
  const error = active && current ? result.error : null
  const elapsed = current ? result.ms : null

  React.useEffect(() => {
    if (!q.trim()) return
    let cancelled = false
    const t0 = performance.now()
    api
      .GET("/api/v1/terminology/search", { params: { query: { q, mode, billable_only: billableOnly, limit: 50 } } })
      .then(unwrap)
      .then((r) => {
        if (!cancelled) setResult({ key, res: r, error: null, ms: performance.now() - t0 })
      })
      .catch((err) => {
        if (!cancelled) setResult((prev) => ({ ...prev, key, error: errorMessage(err), ms: null }))
      })
    return () => {
      cancelled = true
    }
  }, [key, q, mode, billableOnly])

  function push(next: { q?: string; mode?: string; billable?: boolean }) {
    const p = new URLSearchParams(params)
    if (next.q !== undefined) {
      if (next.q) p.set("q", next.q)
      else p.delete("q")
    }
    if (next.mode !== undefined) p.set("mode", next.mode)
    if (next.billable !== undefined) {
      if (next.billable) p.set("billable", "1")
      else p.delete("billable")
    }
    router.push(`${pathname}?${p}`)
  }

  const showRanks = res?.match_type === "hybrid"

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <form
            key={q}
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              const value = new FormData(e.currentTarget).get("q")
              push({ q: String(value ?? "").trim() })
            }}
          >
            <Input
              name="q"
              defaultValue={q}
              placeholder="Clinical phrase, lay term, abbreviation, or code (e.g. K35.3)"
              aria-label="Search query"
              autoFocus
            />
            <Button type="submit">
              <SearchIcon />
              Search
            </Button>
          </form>
          <div className="flex flex-wrap items-center gap-4">
            <Tabs value={mode} onValueChange={(v) => push({ mode: v as string })}>
              <TabsList>
                {MODES.map((m) => (
                  <TabsTrigger key={m.value} value={m.value} title={m.help}>
                    {m.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <div className="flex items-center gap-2">
              <Checkbox
                id="billable"
                checked={billableOnly}
                onCheckedChange={(c) => push({ billable: c === true })}
              />
              <Label htmlFor="billable">Billable codes only</Label>
            </div>
            <span className="text-xs text-muted-foreground">{MODES.find((m) => m.value === mode)?.help}</span>
          </div>
          {!q && (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">Try:</span>
              {TRY.map((t) => (
                <Button key={t} variant="outline" size="xs" onClick={() => push({ q: t })}>
                  {t}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && !res && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {res && (
        <Card className={loading ? "opacity-60" : undefined}>
          <CardContent>
            <div className="mb-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">{res.match_type} match</Badge>
              <span>
                {res.total !== null && res.total !== undefined
                  ? `${res.total} codes`
                  : `top ${res.data.length} ranked`}{" "}
                · ICD-10-CM {res.version}
                {elapsed !== null && ` · ${Math.round(elapsed)} ms`}
              </span>
            </div>
            {res.data.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Description</TableHead>
                    {res.match_type !== "code" && <TableHead className="text-right">Score</TableHead>}
                    {showRanks && <TableHead className="hidden text-right md:table-cell">Text / semantic</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {res.data.map((h, i) => (
                    <TableRow key={h.code}>
                      <TableCell className="text-muted-foreground tabular-nums">{i + 1}</TableCell>
                      <TableCell>
                        <Link
                          href={`/terminology/codes/${encodeURIComponent(h.code)}`}
                          className="font-mono text-sm font-medium hover:underline"
                        >
                          {h.code}
                        </Link>
                        {!h.is_billable && (
                          <div className="text-xs text-muted-foreground" title="Category header — not billable">
                            header
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-normal">
                        <div>{h.display}</div>
                        {h.matched_on && (
                          <div className="text-xs text-muted-foreground">
                            via Alphabetic Index: <span className="italic">{h.matched_on}</span>
                          </div>
                        )}
                        {(h.variants?.length ?? 0) > 0 && (
                          <div className="text-xs text-muted-foreground">
                            + {h.variants!.length} 7th-character variant{h.variants!.length === 1 ? "" : "s"}:{" "}
                            <span className="font-mono">{h.variants!.slice(0, 4).join(", ")}</span>
                            {h.variants!.length > 4 && "…"}
                          </div>
                        )}
                      </TableCell>
                      {res.match_type !== "code" && (
                        <TableCell className="text-right tabular-nums">{h.score?.toFixed(4) ?? "—"}</TableCell>
                      )}
                      {showRanks && (
                        <TableCell className="hidden text-right tabular-nums text-muted-foreground md:table-cell">
                          {h.text_rank ?? "—"} / {h.semantic_rank ?? "—"}
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No codes found</EmptyTitle>
                  <EmptyDescription>Try semantic or hybrid mode for lay wording.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
