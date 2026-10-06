"use client"

import { ListTreeIcon, Maximize2Icon, Minimize2Icon } from "lucide-react"
import Link from "next/link"
import * as React from "react"

import { ProbabilityBar } from "@/components/badges"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useResizableWidth } from "@/hooks/use-resizable-width"
import { api, errorMessage, unwrap } from "@/lib/api/client"
import type { ItemCandidates } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { pct } from "@/lib/labels"

type Sort = "search" | "probability"

/** Every candidate hybrid search handed the decision engine for one item —
 *  the full top-N, not just the alternatives on the card. Loaded on open. */
export function CandidatesSheet({
  encounterId,
  itemId,
  itemText,
  count,
}: {
  encounterId: string
  itemId: number
  itemText: string
  count: number
}) {
  const [open, setOpen] = React.useState(false)
  const [data, setData] = React.useState<ItemCandidates | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [sort, setSort] = React.useState<Sort>("search")
  const [filter, setFilter] = React.useState("")
  const panel = useResizableWidth("jev.candidates-sheet.width")

  // Fetch when opened (fresh each time — a review may have changed is_final).
  async function onOpenChange(next: boolean) {
    setOpen(next)
    if (!next) return
    setError(null)
    try {
      setData(
        unwrap(
          await api.GET("/api/v1/coding/encounters/{encounter_id}/items/{item_id}/candidates", {
            params: { path: { encounter_id: encounterId, item_id: itemId } },
          }),
        ),
      )
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const rows = React.useMemo(() => {
    if (!data) return []
    const f = filter.trim().toLowerCase()
    const filtered = f
      ? data.candidates.filter(
          (c) =>
            c.code.toLowerCase().includes(f) ||
            c.description.toLowerCase().includes(f) ||
            (c.matched_on ?? "").toLowerCase().includes(f),
        )
      : data.candidates
    return sort === "search"
      ? filtered
      : [...filtered].sort((a, b) => (a.probability_rank ?? 1e9) - (b.probability_rank ?? 1e9))
  }, [data, filter, sort])

  const scored = data?.engine != null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger render={<Button variant="ghost" size="sm" />}>
        <ListTreeIcon />
        All {count} candidates
      </SheetTrigger>
      <SheetContent
        className={cn(
          "max-w-full data-[side=right]:sm:max-w-none",
          // No slide transition while dragging, so the edge follows the pointer.
          panel.dragging && "transition-none select-none",
        )}
        style={{ width: panel.width }}
      >
        {/* Drag the left edge to resize; double-click (or the button) to expand. */}
        <div
          {...panel.handleProps}
          className={cn(
            // Fully INSIDE the panel's left edge: any part outside is under the
            // backdrop, and pressing the backdrop closes the sheet.
            "group absolute inset-y-0 left-0 z-20 hidden w-4 cursor-col-resize touch-none items-center justify-center outline-none sm:flex",
            "focus-visible:bg-ring/20",
          )}
        >
          <span
            className={cn(
              "h-12 w-1 rounded-full bg-border transition-colors group-hover:bg-foreground/40 group-focus-visible:bg-ring",
              panel.dragging && "bg-foreground/60",
            )}
          />
        </div>
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                className="absolute top-3 right-12 hidden sm:inline-flex"
                onClick={panel.toggleExpanded}
                aria-label={panel.isExpanded ? "Restore panel width" : "Expand panel"}
              />
            }
          >
            {panel.isExpanded ? <Minimize2Icon /> : <Maximize2Icon />}
          </TooltipTrigger>
          <TooltipContent>{panel.isExpanded ? "Restore width" : "Expand"} · or drag the left edge</TooltipContent>
        </Tooltip>
        <SheetHeader className="pr-24">
          <SheetTitle>Search candidates</SheetTitle>
          <SheetDescription>
            Everything hybrid search passed to the decision engine for <strong>“{itemText}”</strong>
            {data?.engine && (
              <>
                {" "}
                · scored by {data.engine} ({data.model}) · none of the above {pct(data.none_of_the_above_probability)}
              </>
            )}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-wrap items-center gap-3 px-4">
          <Tabs value={sort} onValueChange={(v) => setSort(v as Sort)}>
            <TabsList>
              <TabsTrigger value="search">Search order</TabsTrigger>
              <TabsTrigger value="probability" disabled={!scored}>
                By probability
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <Input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter by code, description or index term"
            className="max-w-xs"
            aria-label="Filter candidates"
          />
          {data && (
            <span className="text-xs text-muted-foreground">
              {rows.length} of {data.total}
            </span>
          )}
          <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            <span className="size-3 rounded-sm bg-emerald-500/20 ring-1 ring-emerald-500/50" /> suggested
            <span className="size-3 rounded-sm bg-sky-500/20 ring-1 ring-sky-500/50" /> final (reviewer)
          </span>
        </div>

        {data?.final_code_not_in_candidates && (
          <Alert className="mx-4 w-auto">
            <AlertDescription>
              The reviewer&apos;s final code <span className="font-mono">{data.final_code_not_in_candidates}</span> was
              not among these candidates — a search miss for this item.
            </AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive" className="mx-4 w-auto">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
          {!data && !error ? (
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : data && data.total === 0 ? (
            <p className="py-6 text-sm text-muted-foreground">No candidates stored for this item.</p>
          ) : (
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-popover">
                <TableRow>
                  <TableHead className="w-14 text-right">Search</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="w-40">Probability</TableHead>
                  <TableHead className="w-14 text-right">P rank</TableHead>
                  <TableHead className="hidden w-24 text-right lg:table-cell">Text / sem</TableHead>
                  <TableHead className="hidden w-20 text-right lg:table-cell">RRF score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((c) => (
                  <TableRow
                    key={c.code}
                    className={cn(
                      c.is_assigned && "bg-emerald-500/10 hover:bg-emerald-500/15",
                      c.is_final && "bg-sky-500/10 hover:bg-sky-500/15",
                    )}
                  >
                    <TableCell className="text-right tabular-nums text-muted-foreground">#{c.search_rank}</TableCell>
                    <TableCell className="font-mono text-xs">
                      <Link href={`/terminology/codes/${encodeURIComponent(c.code)}`} className="hover:underline">
                        {c.code}
                      </Link>
                      <div className="mt-0.5 flex gap-1">
                        {c.is_assigned && <Badge variant="secondary">suggested</Badge>}
                        {c.is_final && <Badge>final</Badge>}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-md whitespace-normal">
                      {c.description}
                      {c.matched_on && (
                        <div className="text-xs text-muted-foreground">
                          via index term: <span className="italic">{c.matched_on}</span>
                        </div>
                      )}
                      {c.variants.length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          + {c.variants.length} 7th-character variant{c.variants.length === 1 ? "" : "s"}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>{c.probability != null ? <ProbabilityBar value={c.probability} /> : "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.probability_rank ?? "—"}</TableCell>
                    <TableCell className="hidden text-right tabular-nums text-muted-foreground lg:table-cell">
                      {c.text_rank ?? "—"} / {c.semantic_rank ?? "—"}
                    </TableCell>
                    <TableCell className="hidden text-right tabular-nums text-muted-foreground lg:table-cell">
                      {c.search_score?.toFixed(4) ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
