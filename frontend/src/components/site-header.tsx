"use client"

import { MoonIcon, SunIcon, UserIcon } from "lucide-react"
import { useTheme } from "next-themes"

import { useReviewer } from "@/components/providers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"

export function SiteHeader() {
  const { reviewer, setReviewer } = useReviewer()
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
      <div className="ml-auto flex items-center gap-2">
        <label className="flex items-center gap-2 text-sm text-muted-foreground" htmlFor="reviewer">
          <UserIcon className="size-4" />
          <span className="hidden sm:inline">Reviewer</span>
        </label>
        <Input
          id="reviewer"
          value={reviewer}
          onChange={(e) => setReviewer(e.target.value)}
          placeholder="Your name"
          className="h-8 w-36 sm:w-44"
          aria-describedby="reviewer-help"
        />
        <span id="reviewer-help" className="sr-only">
          Recorded on every review action in the audit trail
        </span>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle dark mode"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
        >
          <SunIcon className="dark:hidden" />
          <MoonIcon className="hidden dark:block" />
        </Button>
      </div>
    </header>
  )
}
