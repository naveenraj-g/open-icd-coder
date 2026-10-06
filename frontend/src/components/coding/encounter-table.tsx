import Link from "next/link"

import { DateTime } from "@/components/date-time"
import { EncounterStatusBadge, QueueBadge, ReviewedBadge } from "@/components/badges"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { EncounterSummary } from "@/lib/api/types"

export function EncounterTable({ rows }: { rows: EncounterSummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Encounter</TableHead>
          <TableHead className="hidden md:table-cell">Department</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Queue</TableHead>
          <TableHead className="text-right">Items</TableHead>
          <TableHead className="text-right">Flagged</TableHead>
          <TableHead className="hidden lg:table-cell">Review</TableHead>
          <TableHead className="hidden lg:table-cell">Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((e) => (
          <TableRow key={e.encounter_id}>
            <TableCell>
              <Link
                href={`/coding/encounters/${encodeURIComponent(e.encounter_id)}`}
                className="font-medium underline-offset-4 hover:underline"
              >
                {e.encounter_id}
              </Link>
              <div className="text-xs text-muted-foreground">{e.patient_id}</div>
            </TableCell>
            <TableCell className="hidden md:table-cell">{e.department ?? "—"}</TableCell>
            <TableCell>
              <EncounterStatusBadge status={e.status} />
            </TableCell>
            <TableCell>
              <QueueBadge queue={e.review_queue} />
            </TableCell>
            <TableCell className="text-right tabular-nums">{e.items}</TableCell>
            <TableCell className="text-right tabular-nums">
              {e.flagged_items > 0 ? (
                <span className="font-medium text-amber-700 dark:text-amber-300">{e.flagged_items}</span>
              ) : (
                0
              )}
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <ReviewedBadge reviewed={e.is_human_reviewed} />
            </TableCell>
            <TableCell className="hidden text-muted-foreground lg:table-cell"><DateTime value={e.created_at} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
