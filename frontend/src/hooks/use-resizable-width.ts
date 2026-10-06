"use client"

import * as React from "react"

const MARGIN = 48 // keep a sliver of the page visible behind a right-side panel
const STEP = 40 // arrow-key resize step (px)

function maxWidth() {
  return Math.max(320, window.innerWidth - MARGIN)
}

function clamp(w: number, min: number) {
  return Math.round(Math.min(Math.max(w, min), maxWidth()))
}

function readStored(key: string, fallback: number): number {
  if (typeof window === "undefined") return fallback
  try {
    const v = Number(localStorage.getItem(key))
    return Number.isFinite(v) && v > 0 ? v : fallback
  } catch {
    return fallback
  }
}

/** Width of a right-anchored panel that the user resizes by dragging its left
 *  edge (or with the arrow keys on the handle). Remembered per key in
 *  localStorage — a per-browser convenience only. */
export function useResizableWidth(storageKey: string, { initial = 1024, min = 480 } = {}) {
  // The panel only renders once opened (client side), so reading storage in
  // the initializer can't cause a hydration mismatch.
  const [width, setWidthState] = React.useState(() => readStored(storageKey, initial))
  const [dragging, setDragging] = React.useState(false)
  const restoreRef = React.useRef<number | null>(null)

  const setWidth = React.useCallback(
    (w: number) => {
      const next = clamp(w, min)
      setWidthState(next)
      try {
        localStorage.setItem(storageKey, String(next))
      } catch {}
    },
    [storageKey, min],
  )

  const onPointerDown = React.useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (e.button !== 0) return
      e.preventDefault()
      const handle = e.currentTarget
      handle.setPointerCapture(e.pointerId)
      setDragging(true)
      const onMove = (ev: PointerEvent) => setWidth(window.innerWidth - ev.clientX)
      const onUp = (ev: PointerEvent) => {
        handle.releasePointerCapture(ev.pointerId)
        handle.removeEventListener("pointermove", onMove)
        handle.removeEventListener("pointerup", onUp)
        handle.removeEventListener("pointercancel", onUp)
        setDragging(false)
      }
      handle.addEventListener("pointermove", onMove)
      handle.addEventListener("pointerup", onUp)
      handle.addEventListener("pointercancel", onUp)
    },
    [setWidth],
  )

  const onKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLElement>) => {
      // The handle sits on the LEFT edge: left arrow widens, right narrows.
      if (e.key === "ArrowLeft") setWidth(width + STEP)
      else if (e.key === "ArrowRight") setWidth(width - STEP)
      else if (e.key === "Home") setWidth(maxWidth())
      else if (e.key === "End") setWidth(min)
      else return
      e.preventDefault()
    },
    [setWidth, width, min],
  )

  const isExpanded = typeof window !== "undefined" && width >= maxWidth() - 1

  /** Expand to (almost) full width, or restore the width before expanding. */
  const toggleExpanded = React.useCallback(() => {
    if (width >= maxWidth() - 1) {
      setWidth(restoreRef.current ?? initial)
      restoreRef.current = null
    } else {
      restoreRef.current = width
      setWidth(maxWidth())
    }
  }, [width, setWidth, initial])

  return {
    width,
    dragging,
    isExpanded,
    toggleExpanded,
    handleProps: {
      role: "separator" as const,
      "aria-orientation": "vertical" as const,
      "aria-label": "Resize panel",
      "aria-valuemin": min,
      "aria-valuenow": width,
      tabIndex: 0,
      onPointerDown,
      onKeyDown,
      onDoubleClick: toggleExpanded,
    },
  }
}
