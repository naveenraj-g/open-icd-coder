"use client"

import * as React from "react"

const noopSubscribe = () => () => {}

function format(value: string, locale?: string, timeZone?: string): string {
  return new Date(value).toLocaleString(locale, { dateStyle: "medium", timeStyle: "short", timeZone })
}

/** A timestamp in the viewer's own locale and time zone.
 *
 *  The server can't know either, so formatting during render would differ
 *  between the server HTML and the browser and break hydration. The server
 *  snapshot is a fixed en-US/UTC rendering; after hydration React switches to
 *  the browser's locale — no mismatch, no effect. */
export function DateTime({ value }: { value: string | null | undefined }) {
  const text = React.useSyncExternalStore(
    noopSubscribe,
    () => (value ? format(value) : "—"),
    () => (value ? `${format(value, "en-US", "UTC")} UTC` : "—"),
  )
  return value ? (
    <time dateTime={value} title={value}>
      {text}
    </time>
  ) : (
    <>—</>
  )
}
