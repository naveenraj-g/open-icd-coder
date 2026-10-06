import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { EncounterReview } from "@/components/coding/encounter-review"
import { api, unwrap } from "@/lib/api/client"

export async function generateMetadata(props: PageProps<"/coding/encounters/[encounterId]">): Promise<Metadata> {
  const { encounterId } = await props.params
  return { title: decodeURIComponent(encounterId) }
}

export default async function EncounterPage(props: PageProps<"/coding/encounters/[encounterId]">) {
  const { encounterId } = await props.params
  const [res, settings] = await Promise.all([
    api.GET("/api/v1/coding/encounters/{encounter_id}", {
      params: { path: { encounter_id: decodeURIComponent(encounterId) } },
    }),
    api.GET("/api/v1/coding/settings").then(unwrap),
  ])
  if (res.response.status === 404) notFound()
  const encounter = unwrap(res)

  // key: remount when navigating between encounters so client state resets
  return <EncounterReview key={encounter.encounter_id} initial={encounter} settings={settings} />
}
