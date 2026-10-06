import type { Metadata } from "next"

import { NewEncounterForm } from "@/components/coding/new-encounter-form"
import { PageHeader } from "@/components/page-header"
import { api, unwrap } from "@/lib/api/client"

export const metadata: Metadata = { title: "New encounter" }

export default async function NewEncounterPage() {
  const settings = unwrap(await api.GET("/api/v1/coding/settings"))
  return (
    <>
      <PageHeader
        title="New encounter"
        description="Submit a SOAP note and its findings. Each condition is searched (top candidates), scored by the decision engine, flagged, and queued for review."
      />
      <NewEncounterForm settings={settings} />
    </>
  )
}
