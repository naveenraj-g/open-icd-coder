import type { Metadata } from "next"
import { FilePlus2Icon } from "lucide-react"
import { Suspense } from "react"

import { EncounterTable } from "@/components/coding/encounter-table"
import { QueueFilters } from "@/components/coding/queue-filters"
import { PageHeader } from "@/components/page-header"
import { LinkButton } from "@/components/link-button"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { api, unwrap } from "@/lib/api/client"

export const metadata: Metadata = { title: "Review queue" }

const PAGE_SIZE = 25

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v
}

export default async function EncountersPage(props: PageProps<"/coding/encounters">) {
  const sp = await props.searchParams
  const page = Math.max(1, Number(one(sp.page)) || 1)
  const reviewed = one(sp.reviewed)

  const res = unwrap(
    await api.GET("/api/v1/coding/encounters", {
      params: {
        query: {
          queue: one(sp.queue),
          status: one(sp.status),
          reviewed: reviewed === undefined ? undefined : reviewed === "true",
          limit: PAGE_SIZE,
          offset: (page - 1) * PAGE_SIZE,
        },
      },
    }),
  )
  const pages = Math.max(1, Math.ceil(res.total / PAGE_SIZE))

  function pageHref(p: number) {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(sp)) {
      const val = one(v)
      if (val && k !== "page") q.set(k, val)
    }
    q.set("page", String(p))
    return `/coding/encounters?${q}`
  }

  return (
    <>
      <PageHeader
        title="Review queue"
        description="Encounters submitted for coding. Close review = at least one item is flagged or failed."
        actions={
          <LinkButton href="/coding/new">
            <FilePlus2Icon />
            New encounter
          </LinkButton>
        }
      />
      <div className="mb-4">
        <Suspense>
          <QueueFilters />
        </Suspense>
      </div>
      <Card>
        <CardContent>
          {res.data.length ? (
            <EncounterTable rows={res.data} />
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No encounters match</EmptyTitle>
                <EmptyDescription>Change the filters, or submit a new encounter.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>
      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {res.total} encounter{res.total === 1 ? "" : "s"} · page {page} of {pages}
        </span>
        <div className="flex gap-2">
          {page > 1 ? (
            <LinkButton variant="outline" size="sm" href={pageHref(page - 1)}>
              Previous
            </LinkButton>
          ) : (
            <Button variant="outline" size="sm" disabled>
              Previous
            </Button>
          )}
          {page < pages ? (
            <LinkButton variant="outline" size="sm" href={pageHref(page + 1)}>
              Next
            </LinkButton>
          ) : (
            <Button variant="outline" size="sm" disabled>
              Next
            </Button>
          )}
        </div>
      </div>
    </>
  )
}
