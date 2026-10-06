"use client"

import { BadgeCheckIcon, RotateCcwIcon } from "lucide-react"
import { useRouter } from "next/navigation"
import * as React from "react"
import { toast } from "sonner"

import { DateTime } from "@/components/date-time"
import { EncounterStatusBadge, QueueBadge, ReviewedBadge } from "@/components/badges"
import { ItemReviewCard, type ReviewAction } from "@/components/coding/item-review-card"
import { SoapNote } from "@/components/coding/soap-note"
import { PageHeader } from "@/components/page-header"
import { useReviewer } from "@/components/providers"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { api, errorMessage, unwrap } from "@/lib/api/client"
import type { CodingSettings, EncounterOut } from "@/lib/api/types"
import { ITEM_TYPE } from "@/lib/labels"

const UNRESOLVED = new Set(["pending", "scored", "no_candidates", "failed"])

export function EncounterReview({ initial, settings }: { initial: EncounterOut; settings: CodingSettings }) {
  const router = useRouter()
  const { reviewer } = useReviewer()
  const [enc, setEnc] = React.useState(initial)
  const [busyItem, setBusyItem] = React.useState<number | null>(null)

  const coded = enc.coded_concepts.filter((c) => c.status !== "not_coded")
  const stored = enc.coded_concepts.filter((c) => c.status === "not_coded")
  const unresolved = coded.filter((c) => UNRESOLVED.has(c.status))
  const approved = enc.audit_trail.isHumanReviewed

  const lockedReason = approved
    ? "Encounter already approved"
    : !reviewer.trim()
      ? "Enter your name in the Reviewer box (top right) first"
      : undefined

  function applied(next: EncounterOut, message: string) {
    setEnc(next)
    router.refresh() // keep lists/dashboard counts fresh
    toast.success(message)
  }

  async function review(itemId: number, a: ReviewAction) {
    setBusyItem(itemId)
    try {
      const next = unwrap(
        await api.POST("/api/v1/coding/encounters/{encounter_id}/items/{item_id}/review", {
          params: { path: { encounter_id: enc.encounter_id, item_id: itemId } },
          body: { action: a.action, reviewer: reviewer.trim(), code: a.action === "override" ? a.code : null },
        }),
      )
      const item = next.coded_concepts.find((c) => c.item_id === itemId)
      applied(
        next,
        a.action === "remove"
          ? "Item removed from billing"
          : `${a.action === "approve" ? "Approved" : "Overridden to"} ${item?.review.final_code ?? ""}`,
      )
    } catch (err) {
      toast.error("Review failed", { description: errorMessage(err) })
    } finally {
      setBusyItem(null)
    }
  }

  return (
    <>
      <PageHeader
        title={<span className="font-mono">{enc.encounter_id}</span>}
        description={
          <>
            Patient {enc.patient_id}
            {enc.clinical_input.department && <> · {enc.clinical_input.department}</>} · submitted{" "}
            <DateTime value={enc.created_at} />
          </>
        }
        actions={
          <>
            <RescoreDialog
              enc={enc}
              settings={settings}
              disabled={approved}
              onDone={(next, engine) => applied(next, `Rescored with ${engine}`)}
            />
            <ApproveDialog
              enc={enc}
              reviewer={reviewer.trim()}
              unresolved={unresolved.length}
              onDone={(next) => applied(next, "Encounter approved — isHumanReviewed = true")}
            />
          </>
        }
      >
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <EncounterStatusBadge status={enc.status} />
          <QueueBadge queue={enc.review_queue} />
          <ReviewedBadge reviewed={approved} />
        </div>
      </PageHeader>

      {!approved && !reviewer.trim() && (
        <Alert className="mb-6">
          <AlertTitle>Enter your reviewer name to review</AlertTitle>
          <AlertDescription>
            Use the Reviewer box at the top right — it is recorded with every action in the audit trail.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Coded conditions</h2>
            <span className="text-sm text-muted-foreground">
              {coded.length - unresolved.length} of {coded.length} resolved
            </span>
          </div>
          {coded.map((item) => (
            <ItemReviewCard
              key={item.item_id}
              encounterId={enc.encounter_id}
              item={item}
              threshold={settings.low_confidence_threshold}
              locked={!!lockedReason}
              lockedReason={lockedReason}
              busy={busyItem === item.item_id}
              onReview={(a) => review(item.item_id, a)}
            />
          ))}
          {coded.length === 0 && (
            <p className="text-sm text-muted-foreground">No coded items in this encounter.</p>
          )}

          {stored.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Stored, not coded</CardTitle>
                <CardDescription>
                  Only {settings.coded_item_types.map((t) => (ITEM_TYPE[t] ?? t).toLowerCase()).join(", ")}s are coded in
                  this prototype. These are kept for later (SNOMED, LOINC, RxNorm).
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {stored.map((s) => (
                    <li key={s.item_id} className="flex items-center gap-2">
                      <Badge variant="outline">{ITEM_TYPE[s.item_type] ?? s.item_type}</Badge>
                      {s.text}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6 lg:sticky lg:top-20 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Audit trail</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="isHumanReviewed">
                <span className="font-mono">{String(approved)}</span>
              </Row>
              <Row label="Reviewed by">{enc.audit_trail.reviewed_by ?? "—"}</Row>
              <Row label="Reviewed at"><DateTime value={enc.audit_trail.reviewed_at} /></Row>
              <div>
                <div className="mb-1 text-muted-foreground">
                  {approved ? "Final billing codes" : "Billing codes (preview)"}
                </div>
                <div className="flex flex-wrap gap-1">
                  {enc.audit_trail.final_billing_codes.length ? (
                    enc.audit_trail.final_billing_codes.map((c) => (
                      <Badge key={c} variant="secondary" className="font-mono">
                        {c}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground">none</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">SOAP note</CardTitle>
              <CardDescription>Findings highlighted where they appear verbatim</CardDescription>
            </CardHeader>
            <CardContent>
              <SoapNote note={enc.clinical_input.soap_note} highlights={enc.coded_concepts.map((c) => c.text)} />
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  )
}

function ApproveDialog({
  enc,
  reviewer,
  unresolved,
  onDone,
}: {
  enc: EncounterOut
  reviewer: string
  unresolved: number
  onDone: (next: EncounterOut) => void
}) {
  const [open, setOpen] = React.useState(false)
  const [busy, setBusy] = React.useState(false)
  const approved = enc.audit_trail.isHumanReviewed
  const blocked = approved || unresolved > 0 || !reviewer

  async function approve() {
    setBusy(true)
    try {
      onDone(
        unwrap(
          await api.POST("/api/v1/coding/encounters/{encounter_id}/approve", {
            params: { path: { encounter_id: enc.encounter_id } },
            body: { reviewer },
          }),
        ),
      )
      setOpen(false)
    } catch (err) {
      toast.error("Approval failed", { description: errorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button disabled={blocked} />}>
        <BadgeCheckIcon />
        {approved ? "Approved" : unresolved > 0 ? `${unresolved} item(s) to review` : "Approve encounter"}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve {enc.encounter_id}?</DialogTitle>
          <DialogDescription>
            Sets isHumanReviewed = true, recorded as approved by <strong>{reviewer}</strong>. Items can&apos;t be
            changed afterwards.
          </DialogDescription>
        </DialogHeader>
        <div className="text-sm">
          <div className="mb-2 text-muted-foreground">Final billing codes</div>
          <div className="flex flex-wrap gap-1">
            {enc.coded_concepts
              .filter((c) => (c.status === "approved" || c.status === "overridden") && c.review.final_code)
              .map((c) => (
                <Badge key={c.item_id} variant="secondary" className="font-mono">
                  {c.review.final_code}
                </Badge>
              ))}
          </div>
        </div>
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
          <Button onClick={approve} disabled={busy}>
            {busy && <Spinner />} Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RescoreDialog({
  enc,
  settings,
  disabled,
  onDone,
}: {
  enc: EncounterOut
  settings: CodingSettings
  disabled: boolean
  onDone: (next: EncounterOut, engine: string) => void
}) {
  const [open, setOpen] = React.useState(false)
  const [engine, setEngine] = React.useState(settings.default_engine)
  const [busy, setBusy] = React.useState(false)
  const selected = settings.engines.find((e) => e.name === engine)
  const items = Object.fromEntries(settings.engines.map((e) => [e.name, `${e.name} · ${e.model}`]))

  async function rescore() {
    setBusy(true)
    try {
      onDone(
        unwrap(
          await api.POST("/api/v1/coding/encounters/{encounter_id}/rescore", {
            params: { path: { encounter_id: enc.encounter_id }, query: { engine } },
          }),
        ),
        engine,
      )
      setOpen(false)
    } catch (err) {
      toast.error("Rescore failed", { description: errorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" disabled={disabled} />}>
        <RotateCcwIcon />
        Rescore
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rescore with another engine</DialogTitle>
          <DialogDescription>
            Re-runs a decision engine over the stored candidates (no new search). Replaces each item&apos;s suggestion
            and clears item reviews. The previous decisions stay in the audit trail.
          </DialogDescription>
        </DialogHeader>
        <Select items={items} value={engine} onValueChange={(v) => v && setEngine(v)}>
          <SelectTrigger className="w-full" aria-label="Decision engine">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {settings.engines.map((e) => (
              <SelectItem key={e.name} value={e.name}>
                {e.name} · {e.model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selected?.warning && <p className="text-xs text-amber-700 dark:text-amber-300">{selected.warning}</p>}
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
          <Button onClick={rescore} disabled={busy}>
            {busy && <Spinner />} Rescore
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
