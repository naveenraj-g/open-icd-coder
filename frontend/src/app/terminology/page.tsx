import type { Metadata } from "next"
import { Suspense } from "react"

import { PageHeader } from "@/components/page-header"
import { SearchPanel } from "@/components/terminology/search-panel"

export const metadata: Metadata = { title: "ICD-10-CM search" }

export default function TerminologySearchPage() {
  return (
    <>
      <PageHeader
        title="ICD-10-CM search"
        description="The same Stage 1 search the coding pipeline uses. Code-shaped queries (K35.3, k3530) list codes by prefix; anything else is ranked by the selected mode."
      />
      <Suspense>
        <SearchPanel />
      </Suspense>
    </>
  )
}
