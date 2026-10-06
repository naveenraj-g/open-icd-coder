/** Human wording for backend enums — one place, so every screen says the same thing. */

export const ITEM_STATUS: Record<string, { label: string; tone: Tone; help: string }> = {
  pending: { label: "Pending", tone: "muted", help: "Waiting to be searched and scored" },
  not_coded: {
    label: "Not coded",
    tone: "muted",
    help: "Stored only — this item type isn't coded yet (prototype codes conditions only)",
  },
  no_candidates: { label: "No candidates", tone: "danger", help: "Search found no codes — assign one manually" },
  scored: { label: "Needs review", tone: "info", help: "Scored by the decision engine; awaiting a reviewer" },
  failed: { label: "Failed", tone: "danger", help: "Search or scoring failed — see the error; assign a code manually" },
  approved: { label: "Approved", tone: "success", help: "Reviewer accepted the suggested code" },
  overridden: { label: "Overridden", tone: "warning", help: "Reviewer replaced the suggested code" },
  removed: { label: "Removed", tone: "muted", help: "Reviewer excluded this item from billing" },
}

export const ENCOUNTER_STATUS: Record<string, { label: string; tone: Tone }> = {
  processing: { label: "Processing", tone: "info" },
  ready_for_review: { label: "Ready for review", tone: "info" },
  reviewed: { label: "Reviewed", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
}

export const QUEUE: Record<string, { label: string; tone: Tone; help: string }> = {
  standard: { label: "Standard", tone: "success", help: "No item flagged — quick check and approve" },
  close_review: {
    label: "Close review",
    tone: "warning",
    help: "At least one item is flagged or failed — review carefully",
  },
}

export const FLAGS: Record<string, { label: string; help: string }> = {
  LOW_CONFIDENCE: {
    label: "Low confidence",
    help: "The assigned code's probability is below the low-confidence threshold",
  },
  NONE_OF_THE_ABOVE: {
    label: "None of the above",
    help: "The engine put real weight on no candidate fitting — the right code may not have been retrieved",
  },
  NO_CANDIDATES: { label: "No candidates", help: "Search returned nothing for this item" },
  SCORING_FAILED: { label: "Scoring failed", help: "The decision engine or search call failed" },
}

export const ITEM_TYPE: Record<string, string> = {
  condition: "Condition",
  observation: "Observation",
  service_request: "Service request",
  medication_request: "Medication request",
}

export const NOTE_KINDS: Record<string, string> = {
  excludes1: "Excludes1 — never code together",
  excludes2: "Excludes2 — not included here, may code both",
  code_first: "Code first",
  code_also: "Code also",
  use_additional_code: "Use additional code",
  notes: "Notes",
  seventh_character: "7th character",
  seventh_character_note: "7th character note",
}

export type Tone = "muted" | "info" | "success" | "warning" | "danger"

export const TONE_CLASS: Record<Tone, string> = {
  muted: "bg-muted text-muted-foreground",
  info: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  warning: "bg-amber-500/15 text-amber-800 dark:text-amber-300",
  danger: "bg-destructive/10 text-destructive",
}

export function pct(p: number | null | undefined, digits = 1): string {
  if (p === null || p === undefined) return "—"
  return `${(p * 100).toFixed(digits)}%`
}
