import { LinkButton } from "@/components/link-button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"

export default function NotFound() {
  return (
    <Empty className="py-16">
      <EmptyHeader>
        <EmptyTitle>Not found</EmptyTitle>
        <EmptyDescription>That encounter or code doesn&apos;t exist.</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <div className="flex gap-2">
          <LinkButton variant="outline" href="/coding/encounters">
            Review queue
          </LinkButton>
          <LinkButton variant="outline" href="/terminology">
            Code search
          </LinkButton>
        </div>
      </EmptyContent>
    </Empty>
  )
}
