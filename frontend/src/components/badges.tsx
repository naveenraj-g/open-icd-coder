import { cn } from "@/lib/utils"
import { ENCOUNTER_STATUS, FLAGS, ITEM_STATUS, QUEUE, TONE_CLASS, type Tone, pct } from "@/lib/labels"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

function Pill({ tone, children, help }: { tone: Tone; children: React.ReactNode; help?: string }) {
  const pill = (
    <span
      className={cn(
        "inline-flex h-5 shrink-0 items-center rounded-full px-2 text-xs font-medium whitespace-nowrap",
        TONE_CLASS[tone],
      )}
    >
      {children}
    </span>
  )
  if (!help) return pill
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="inline-flex cursor-help" />}>{pill}</TooltipTrigger>
      <TooltipContent className="max-w-xs">{help}</TooltipContent>
    </Tooltip>
  )
}

export function ItemStatusBadge({ status }: { status: string }) {
  const s = ITEM_STATUS[status] ?? { label: status, tone: "muted" as Tone, help: undefined }
  return (
    <Pill tone={s.tone} help={s.help}>
      {s.label}
    </Pill>
  )
}

export function EncounterStatusBadge({ status }: { status: string }) {
  const s = ENCOUNTER_STATUS[status] ?? { label: status, tone: "muted" as Tone }
  return <Pill tone={s.tone}>{s.label}</Pill>
}

export function QueueBadge({ queue }: { queue: string | null | undefined }) {
  if (!queue) return null
  const q = QUEUE[queue] ?? { label: queue, tone: "muted" as Tone, help: undefined }
  return (
    <Pill tone={q.tone} help={q.help}>
      {q.label}
    </Pill>
  )
}

export function FlagBadge({ flag }: { flag: string }) {
  const f = FLAGS[flag] ?? { label: flag, help: undefined }
  return (
    <Pill tone="warning" help={f.help}>
      {f.label}
    </Pill>
  )
}

export function ReviewedBadge({ reviewed }: { reviewed: boolean }) {
  return reviewed ? (
    <Pill tone="success" help="isHumanReviewed = true — approved by a reviewer">
      Human reviewed
    </Pill>
  ) : (
    <Pill tone="muted" help="isHumanReviewed = false — not yet approved">
      Not reviewed
    </Pill>
  )
}

/** Probability as a bar + percentage; amber below the low-confidence threshold. */
export function ProbabilityBar({
  value,
  threshold,
  className,
}: {
  value: number | null | undefined
  threshold?: number
  className?: string
}) {
  const v = value ?? 0
  const low = threshold !== undefined && v < threshold
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted" aria-hidden>
        <div
          className={cn("h-full rounded-full", low ? "bg-amber-500" : "bg-emerald-500")}
          style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%` }}
        />
      </div>
      <span className={cn("text-sm tabular-nums", low && "text-amber-700 dark:text-amber-300")}>{pct(value)}</span>
    </div>
  )
}
