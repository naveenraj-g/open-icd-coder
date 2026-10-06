"use client"

import * as React from "react"

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Spinner } from "@/components/ui/spinner"
import { api, unwrap } from "@/lib/api/client"
import type { Alternative, SearchHit } from "@/lib/api/types"
import { pct } from "@/lib/labels"

/** Override target: Jev's ranked alternatives first, or search every billable
 *  ICD-10-CM code (hybrid search) when the right one wasn't offered. */
export function CodePicker({
  alternatives,
  disabled,
  onPick,
  trigger,
}: {
  alternatives: Alternative[]
  disabled?: boolean
  onPick: (code: string) => void
  trigger: React.ReactElement
}) {
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState("")
  // Results remember the query they answer, so "loading" is derived rather
  // than set synchronously inside the effect.
  const [result, setResult] = React.useState<{ q: string; hits: SearchHit[]; error: string | null }>({
    q: "",
    hits: [],
    error: null,
  })

  const q = query.trim()
  const searching = q.length >= 2
  const loading = searching && result.q !== q
  const hits = searching && result.q === q ? result.hits : []
  const error = searching && result.q === q ? result.error : null

  React.useEffect(() => {
    if (q.length < 2) return
    let cancelled = false
    const t = setTimeout(async () => {
      try {
        const res = unwrap(
          await api.GET("/api/v1/terminology/search", {
            params: { query: { q, mode: "hybrid", billable_only: true, limit: 20 } },
          }),
        )
        if (!cancelled) setResult({ q, hits: res.data, error: null })
      } catch (err) {
        if (!cancelled) setResult({ q, hits: [], error: err instanceof Error ? err.message : String(err) })
      }
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [q])

  function pick(code: string) {
    setOpen(false)
    setQuery("")
    onPick(code)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger disabled={disabled} render={trigger} />
      <PopoverContent className="w-[min(34rem,90vw)] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            value={query}
            onValueChange={setQuery}
            placeholder="Search any ICD-10-CM code or phrase…"
          />
          <CommandList className="max-h-80">
            {!searching ? (
              <CommandGroup heading="Ranked alternatives">
                {alternatives.map((a) => (
                  <CommandItem key={a.code} value={a.code} onSelect={() => pick(a.code)}>
                    <span className="w-16 shrink-0 font-mono text-xs">{a.code}</span>
                    <span className="flex-1 truncate">{a.description}</span>
                    <span className="text-xs tabular-nums text-muted-foreground">{pct(a.probability)}</span>
                  </CommandItem>
                ))}
                {alternatives.length === 0 && (
                  <div className="px-2 py-3 text-sm text-muted-foreground">No alternatives — type to search.</div>
                )}
              </CommandGroup>
            ) : (
              <>
                {loading && (
                  <div className="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground">
                    <Spinner /> Searching…
                  </div>
                )}
                {error && <div className="px-3 py-3 text-sm text-destructive">{error}</div>}
                {!loading && !error && <CommandEmpty>No billable codes found.</CommandEmpty>}
                <CommandGroup heading="Search results (billable)">
                  {hits.map((h) => (
                    <CommandItem key={h.code} value={h.code} onSelect={() => pick(h.code)}>
                      <span className="w-16 shrink-0 font-mono text-xs">{h.code}</span>
                      <span className="flex-1 truncate">{h.display}</span>
                      {h.matched_on && (
                        <span className="max-w-40 truncate text-xs text-muted-foreground">via {h.matched_on}</span>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

