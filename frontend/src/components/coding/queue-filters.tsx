"use client"

import { usePathname, useRouter, useSearchParams } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const ANY = "any"

const FILTERS = [
  {
    key: "queue",
    label: "Queue",
    items: { [ANY]: "Any queue", standard: "Standard", close_review: "Close review" },
  },
  {
    key: "status",
    label: "Status",
    items: {
      [ANY]: "Any status",
      processing: "Processing",
      ready_for_review: "Ready for review",
      reviewed: "Reviewed",
      failed: "Failed",
    },
  },
  {
    key: "reviewed",
    label: "Human reviewed",
    items: { [ANY]: "Reviewed or not", false: "Not reviewed", true: "Human reviewed" },
  },
] as const

/** Filters live in the URL so a filtered queue can be bookmarked or shared. */
export function QueueFilters() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  function set(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (!value || value === ANY) next.delete(key)
    else next.set(key, value)
    next.delete("page")
    router.push(`${pathname}?${next.toString()}`)
  }

  const active = FILTERS.some((f) => params.get(f.key))

  return (
    <div className="flex flex-wrap items-center gap-2">
      {FILTERS.map((f) => (
        <Select key={f.key} items={f.items} value={params.get(f.key) ?? ANY} onValueChange={(v) => set(f.key, v)}>
          <SelectTrigger aria-label={f.label} className="min-w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(f.items).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
      {active && (
        <Button variant="ghost" size="sm" onClick={() => router.push(pathname)}>
          Clear filters
        </Button>
      )}
    </div>
  )
}
