import * as React from "react"

/** The note with each finding's text highlighted where it appears verbatim
 *  (case-insensitive) — a quick visual check of what was coded. */
export function SoapNote({ note, highlights }: { note: string; highlights: string[] }) {
  const terms = highlights.map((h) => h.trim()).filter((h) => h.length >= 3)
  if (!terms.length) return <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{note}</pre>

  const escaped = terms
    .sort((a, b) => b.length - a.length)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
  const re = new RegExp(`(${escaped.join("|")})`, "gi")
  const parts = note.split(re)

  return (
    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="rounded bg-amber-200/60 px-0.5 text-foreground dark:bg-amber-400/25">
            {part}
          </mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        ),
      )}
    </pre>
  )
}
