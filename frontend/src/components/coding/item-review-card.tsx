"use client"

import { CheckIcon, ChevronDownIcon, PencilIcon, XIcon } from "lucide-react"
import Link from "next/link"
import * as React from "react"

import { DateTime } from "@/components/date-time"
import { FlagBadge, ItemStatusBadge, ProbabilityBar } from "@/components/badges"
import { CandidatesSheet } from "@/components/coding/candidates-sheet"
import { CodePicker } from "@/components/coding/code-picker"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { CodedItem } from "@/lib/api/types"
import { ITEM_TYPE, pct } from "@/lib/labels"

export type ReviewAction = { action: "approve" } | { action: "remove" } | { action: "override"; code: string }

export function ItemReviewCard({
  encounterId,
  item,
  threshold,
  locked,
  lockedReason,
  busy,
  onReview,
}: {
  encounterId: string
  item: CodedItem
  threshold: number
  locked: boolean
  lockedReason?: string
  busy: boolean
  onReview: (action: ReviewAction) => void
}) {
  const ai = item.ai_classification
  const review = item.review
  const reviewable = !["pending", "not_coded"].includes(item.status)

  const disabledWrap = (node: React.ReactElement) =>
    locked && lockedReason ? (
      <Tooltip>
        <TooltipTrigger render={<span className="inline-flex" />}>{node}</TooltipTrigger>
        <TooltipContent>{lockedReason}</TooltipContent>
      </Tooltip>
    ) : (
      node
    )

  return (
    <Card id={`item-${item.item_id}`}>
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">#{item.sequence}</span>
          <Badge variant="outline">{ITEM_TYPE[item.item_type] ?? item.item_type}</Badge>
          <ItemStatusBadge status={item.status} />
          {ai?.flags.map((f) => <FlagBadge key={f} flag={f} />)}
        </div>
        <p className="text-base font-medium leading-snug">{item.text}</p>
      </CardHeader>

      <CardContent className="space-y-4">
        {item.error && (
          <Alert variant="destructive">
            <AlertDescription>{item.error}</AlertDescription>
          </Alert>
        )}

        {ai && (
          <div className="rounded-lg border p-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-xs text-muted-foreground">Suggested code</div>
                {ai.assigned_code ? (
                  <Link
                    href={`/terminology/codes/${encodeURIComponent(ai.assigned_code)}`}
                    className="font-mono text-lg font-semibold underline-offset-4 hover:underline"
                  >
                    {ai.assigned_code}
                  </Link>
                ) : (
                  <span className="text-muted-foreground">none</span>
                )}
                <div className="text-sm">{ai.assigned_description}</div>
              </div>
              <div className="space-y-1 text-right">
                <div className="text-xs text-muted-foreground">Probability</div>
                <ProbabilityBar value={ai.probability} threshold={threshold} />
                <div className="text-xs text-muted-foreground">
                  None of the above: {pct(ai.none_of_the_above_probability)}
                </div>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {ai.engine} · {ai.model} · {ai.candidates_scored} candidates
              {ai.latency_ms !== null && ai.latency_ms !== undefined && ` · ${Math.round(ai.latency_ms)} ms`}
            </div>
          </div>
        )}

        {ai && ai.top_alternatives.length > 0 && (
          <Collapsible>
            <div className="-ml-2 flex flex-wrap items-center gap-1">
              <CollapsibleTrigger
                render={
                  <Button variant="ghost" size="sm" className="group">
                    <ChevronDownIcon className="transition-transform group-data-[panel-open]:rotate-180" />
                    {ai.top_alternatives.length} ranked alternatives
                  </Button>
                }
              />
              <CandidatesSheet
                encounterId={encounterId}
                itemId={item.item_id}
                itemText={item.text}
                count={ai.candidates_scored}
              />
            </div>
            <CollapsibleContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Probability</TableHead>
                    <TableHead className="hidden text-right sm:table-cell">Search rank</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ai.top_alternatives.map((a) => (
                    <TableRow key={a.code}>
                      <TableCell className="font-mono text-xs">
                        <Link href={`/terminology/codes/${encodeURIComponent(a.code)}`} className="hover:underline">
                          {a.code}
                        </Link>
                      </TableCell>
                      <TableCell className="max-w-72 whitespace-normal text-sm">
                        {a.description}
                        {a.matched_on && (
                          <div className="text-xs text-muted-foreground">matched index term: {a.matched_on}</div>
                        )}
                      </TableCell>
                      <TableCell>
                        <ProbabilityBar value={a.probability} />
                      </TableCell>
                      <TableCell className="hidden text-right tabular-nums sm:table-cell">#{a.search_rank}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="xs"
                          disabled={locked || busy}
                          onClick={() => onReview({ action: "override", code: a.code })}
                        >
                          Use
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CollapsibleContent>
          </Collapsible>
        )}

        {review.action && (
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-muted/50 px-3 py-2 text-sm">
            <span className="font-medium capitalize">{review.action}</span>
            {review.final_code ? (
              <>
                <span>→</span>
                <span className="font-mono font-semibold">{review.final_code}</span>
                <span className="text-muted-foreground">{review.final_description}</span>
              </>
            ) : (
              <span className="text-muted-foreground">not billed</span>
            )}
            <span className="ml-auto text-xs text-muted-foreground">
              {review.reviewed_by} · <DateTime value={review.reviewed_at} />
            </span>
          </div>
        )}

        {reviewable && (
          <div className="flex flex-wrap items-center gap-2">
            {disabledWrap(
              <Button
                size="sm"
                disabled={locked || busy || !ai?.assigned_code}
                onClick={() => onReview({ action: "approve" })}
              >
                {busy ? <Spinner /> : <CheckIcon />}
                Approve {ai?.assigned_code ?? ""}
              </Button>,
            )}
            {disabledWrap(
              <CodePicker
                alternatives={ai?.top_alternatives ?? []}
                disabled={locked || busy}
                onPick={(code) => onReview({ action: "override", code })}
                trigger={
                  <Button variant="outline" size="sm" disabled={locked || busy}>
                    <PencilIcon />
                    Override…
                  </Button>
                }
              />,
            )}
            {disabledWrap(
              <Button variant="ghost" size="sm" disabled={locked || busy} onClick={() => onReview({ action: "remove" })}>
                <XIcon />
                Remove
              </Button>,
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
