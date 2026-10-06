import Link from "next/link"
import type * as React from "react"

import { Button } from "@/components/ui/button"

type ButtonProps = React.ComponentProps<typeof Button>

/** A link styled as a Button. Base UI's Button expects a native <button>
 *  unless told otherwise, so rendering it as an <a> needs nativeButton={false}
 *  — this keeps link semantics (href, middle-click, prefetch) intact. */
export function LinkButton({
  href,
  external,
  ...props
}: Omit<ButtonProps, "render" | "nativeButton"> & { href: string; external?: boolean }) {
  return (
    <Button
      {...props}
      nativeButton={false}
      render={external ? <a href={href} target="_blank" rel="noreferrer" /> : <Link href={href} />}
    />
  )
}
