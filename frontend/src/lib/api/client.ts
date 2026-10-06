import createClient from "openapi-fetch"

import type { paths } from "./schema"

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001"

/** Typed client for the FastAPI backend — types generated from its OpenAPI spec
 *  (`pnpm gen:api`). Works in server and client components. */
export const api = createClient<paths>({ baseUrl: API_URL, cache: "no-store" })

/** The backend returns every error as { error: { code, message, details? } };
 *  request validation errors carry per-field details. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly details?: { field: string; message: string }[],
  ) {
    super(message)
    this.name = "ApiError"
  }
}

type ErrorBody = {
  error?: { code?: string; message?: string; details?: { field: string; message: string }[] }
}

/** Unwrap an openapi-fetch result: return data, or throw an ApiError with the
 *  backend's message (and field details for validation errors). */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    const body = (result.error ?? {}) as ErrorBody
    const details = body.error?.details
    const message =
      body.error?.message ??
      (result.response.status >= 500 ? "The backend hit an internal error" : `Request failed (${result.response.status})`)
    const withDetails = details?.length
      ? `${message}: ${details.map((d) => (d.field ? `${d.field} — ${d.message}` : d.message)).join("; ")}`
      : message
    throw new ApiError(withDetails, result.response.status, body.error?.code, details)
  }
  return result.data
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof TypeError) return `Cannot reach the backend at ${API_URL}. Is it running (just dev)?`
  return err instanceof Error ? err.message : String(err)
}
