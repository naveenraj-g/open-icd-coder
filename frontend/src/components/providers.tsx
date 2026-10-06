"use client"

import { ThemeProvider } from "next-themes"
import * as React from "react"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

const REVIEWER_KEY = "jev.reviewer"

type ReviewerContextValue = { reviewer: string; setReviewer: (name: string) => void }

const ReviewerContext = React.createContext<ReviewerContextValue | null>(null)

/** There is no login in the prototype: the reviewer types their name once and
 *  it is sent with every review action (it lands in the audit trail). Kept in
 *  localStorage as a per-browser convenience only. */
const CHANGE_EVENT = "jev:reviewer-change"
let memoryReviewer = "" // used when localStorage is unavailable (private mode)

function readReviewer(): string {
  try {
    return localStorage.getItem(REVIEWER_KEY) ?? ""
  } catch {
    return memoryReviewer
  }
}

function subscribeReviewer(onChange: () => void) {
  window.addEventListener("storage", onChange) // other tabs
  window.addEventListener(CHANGE_EVENT, onChange) // this tab
  return () => {
    window.removeEventListener("storage", onChange)
    window.removeEventListener(CHANGE_EVENT, onChange)
  }
}

function ReviewerProvider({ children }: { children: React.ReactNode }) {
  const reviewer = React.useSyncExternalStore(subscribeReviewer, readReviewer, () => "")

  const setReviewer = React.useCallback((name: string) => {
    memoryReviewer = name
    try {
      localStorage.setItem(REVIEWER_KEY, name)
    } catch {}
    window.dispatchEvent(new Event(CHANGE_EVENT))
  }, [])

  const value = React.useMemo(() => ({ reviewer, setReviewer }), [reviewer, setReviewer])
  return <ReviewerContext.Provider value={value}>{children}</ReviewerContext.Provider>
}

export function useReviewer(): ReviewerContextValue {
  const ctx = React.useContext(ReviewerContext)
  if (!ctx) throw new Error("useReviewer must be used inside <Providers>")
  return ctx
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <TooltipProvider>
        <ReviewerProvider>
          {children}
          <Toaster richColors closeButton />
        </ReviewerProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}
