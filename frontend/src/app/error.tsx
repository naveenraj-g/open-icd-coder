"use client"

import { AlertTriangleIcon, RotateCcwIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { API_URL } from "@/lib/api/client"

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const unreachable = /fetch failed|ECONNREFUSED|Failed to fetch/i.test(error.message)
  return (
    <div className="mx-auto max-w-xl py-12">
      <Alert variant="destructive">
        <AlertTriangleIcon />
        <AlertTitle>{unreachable ? "Backend unreachable" : "Something went wrong"}</AlertTitle>
        <AlertDescription>
          {unreachable ? (
            <>
              Can&apos;t reach the API at <span className="font-mono">{API_URL}</span>. Start it with{" "}
              <span className="font-mono">just dev</span> in <span className="font-mono">backend/</span>.
            </>
          ) : (
            error.message
          )}
        </AlertDescription>
      </Alert>
      <Button variant="outline" className="mt-4" onClick={reset}>
        <RotateCcwIcon /> Try again
      </Button>
    </div>
  )
}
