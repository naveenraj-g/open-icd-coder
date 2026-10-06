"use client"

import { PlusIcon, RefreshCwIcon, SparklesIcon, Trash2Icon } from "lucide-react"
import { useRouter } from "next/navigation"
import * as React from "react"
import { toast } from "sonner"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { api, errorMessage, unwrap } from "@/lib/api/client"
import type { CodingSettings, EncounterCreate } from "@/lib/api/types"
import { EXAMPLES, newEncounterId } from "@/lib/examples"
import { ITEM_TYPE } from "@/lib/labels"

type ListKey = "conditions" | "observations" | "service_requests" | "medication_requests"

const LISTS: { key: ListKey; type: string; placeholder: string }[] = [
  { key: "conditions", type: "condition", placeholder: "e.g. acute appendicitis with localized peritonitis" },
  { key: "observations", type: "observation", placeholder: "e.g. WBC 15.2, leukocytosis" },
  { key: "service_requests", type: "service_request", placeholder: "e.g. CT abdomen and pelvis" },
  { key: "medication_requests", type: "medication_request", placeholder: "e.g. IV ceftriaxone 1 g" },
]

type FormState = {
  encounter_id: string
  patient_id: string
  department: string
  soap_note: string
} & Record<ListKey, string[]>

const EMPTY: FormState = {
  encounter_id: "",
  patient_id: "",
  department: "",
  soap_note: "",
  conditions: [""],
  observations: [],
  service_requests: [],
  medication_requests: [],
}

export function NewEncounterForm({ settings }: { settings: CodingSettings }) {
  const router = useRouter()
  const [form, setForm] = React.useState<FormState>(EMPTY)
  const [engine, setEngine] = React.useState(settings.default_engine)
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const coded = new Set(settings.coded_item_types)
  const selectedEngine = settings.engines.find((e) => e.name === engine)
  const engineItems = Object.fromEntries(settings.engines.map((e) => [e.name, `${e.name} · ${e.model}`]))

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  function loadExample(i: number) {
    const ex = EXAMPLES[i].body
    setForm({
      encounter_id: newEncounterId(),
      patient_id: ex.patient_id,
      department: ex.department ?? "",
      soap_note: ex.soap_note,
      conditions: (ex.conditions ?? []).map((c) => c.text),
      observations: (ex.observations ?? []).map((c) => c.text),
      service_requests: (ex.service_requests ?? []).map((c) => c.text),
      medication_requests: (ex.medication_requests ?? []).map((c) => c.text),
    })
    setError(null)
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const clean = (xs: string[]) => xs.map((t) => t.trim()).filter(Boolean).map((text) => ({ text }))
    const body: EncounterCreate = {
      // Left blank -> generated here (not at render, so server and client markup match).
      encounter_id: form.encounter_id.trim() || newEncounterId(),
      patient_id: form.patient_id.trim(),
      department: form.department.trim() || null,
      soap_note: form.soap_note.trim(),
      conditions: clean(form.conditions),
      observations: clean(form.observations),
      service_requests: clean(form.service_requests),
      medication_requests: clean(form.medication_requests),
    }
    setSubmitting(true)
    try {
      const out = unwrap(
        await api.POST("/api/v1/coding/encounters", { body, params: { query: { engine } } }),
      )
      const flagged = out.coded_concepts.filter((c) => (c.ai_classification?.flags.length ?? 0) > 0).length
      toast.success(`Encounter ${out.encounter_id} coded`, {
        description: `${out.coded_concepts.filter((c) => c.status !== "not_coded").length} coded item(s) · ${flagged} flagged · queue: ${out.review_queue ?? "—"}`,
      })
      router.push(`/coding/encounters/${encodeURIComponent(out.encounter_id)}`)
    } catch (err) {
      setError(errorMessage(err))
      setSubmitting(false)
    }
  }

  const codedCount = form.conditions.filter((t) => t.trim()).length

  return (
    <form onSubmit={onSubmit} className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-3">
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-2">
            <div>
              <CardTitle>Clinical input</CardTitle>
              <CardDescription>The note is sent to the decision engine as context for every condition.</CardDescription>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button type="button" variant="outline" size="sm" />}>
                <SparklesIcon />
                Load example
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {EXAMPLES.map((ex, i) => (
                  <DropdownMenuItem key={ex.name} onClick={() => loadExample(i)}>
                    {ex.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field>
                  <FieldLabel htmlFor="encounter_id">Encounter ID</FieldLabel>
                  <div className="flex gap-1">
                    <Input
                      id="encounter_id"
                      placeholder="Auto-generated"
                      value={form.encounter_id}
                      onChange={(e) => update("encounter_id", e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="New encounter ID"
                      onClick={() => update("encounter_id", newEncounterId())}
                    >
                      <RefreshCwIcon />
                    </Button>
                  </div>
                </Field>
                <Field>
                  <FieldLabel htmlFor="patient_id">Patient ID</FieldLabel>
                  <Input
                    id="patient_id"
                    required
                    value={form.patient_id}
                    onChange={(e) => update("patient_id", e.target.value)}
                    placeholder="pat_0001"
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="department">Department</FieldLabel>
                  <Input
                    id="department"
                    value={form.department}
                    onChange={(e) => update("department", e.target.value)}
                    placeholder="Optional"
                  />
                </Field>
              </div>
              <Field>
                <FieldLabel htmlFor="soap_note">SOAP note</FieldLabel>
                <Textarea
                  id="soap_note"
                  required
                  rows={10}
                  value={form.soap_note}
                  onChange={(e) => update("soap_note", e.target.value)}
                  placeholder={"S: …\nO: …\nA: …\nP: …"}
                  className="font-mono text-sm"
                />
                <FieldDescription>Synthetic notes only while the free Jev tier is in use.</FieldDescription>
              </Field>
            </FieldGroup>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>Findings</CardTitle>
            <CardDescription>
              Already extracted from the note. Only {settings.coded_item_types.map((t) => ITEM_TYPE[t] ?? t).join(", ").toLowerCase()}s are
              coded; the rest are stored.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {LISTS.map((list) => (
              <ItemList
                key={list.key}
                label={`${ITEM_TYPE[list.type]}s`}
                coded={coded.has(list.type as never)}
                placeholder={list.placeholder}
                values={form[list.key]}
                onChange={(values) => update(list.key, values)}
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Decision engine</CardTitle>
            <CardDescription>Scores the top {settings.candidates_per_item} search candidates for each condition.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select items={engineItems} value={engine} onValueChange={(v) => v && setEngine(v)}>
              <SelectTrigger className="w-full" aria-label="Decision engine">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {settings.engines.map((e) => (
                  <SelectItem key={e.name} value={e.name}>
                    {e.name} · {e.model}
                    {e.is_default ? " (default)" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedEngine?.warning && (
              <p className="text-xs text-amber-700 dark:text-amber-300">{selectedEngine.warning}</p>
            )}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" className="w-full" disabled={submitting || codedCount === 0}>
              {submitting ? (
                <>
                  <Spinner /> Searching & scoring {codedCount} condition{codedCount === 1 ? "" : "s"}…
                </>
              ) : (
                <>Code encounter</>
              )}
            </Button>
            {codedCount === 0 && <p className="text-xs text-muted-foreground">Add at least one condition to code.</p>}
          </CardContent>
        </Card>
      </div>
    </form>
  )
}

function ItemList({
  label,
  coded,
  placeholder,
  values,
  onChange,
}: {
  label: string
  coded: boolean
  placeholder: string
  values: string[]
  onChange: (values: string[]) => void
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {label}{" "}
          {coded ? <Badge variant="secondary">coded</Badge> : <Badge variant="outline">stored only</Badge>}
        </span>
        <Button type="button" variant="ghost" size="xs" onClick={() => onChange([...values, ""])}>
          <PlusIcon /> Add
        </Button>
      </div>
      {values.map((v, i) => (
        <div key={i} className="flex gap-1">
          <Input
            aria-label={`${label} ${i + 1}`}
            value={v}
            placeholder={placeholder}
            onChange={(e) => onChange(values.map((x, j) => (j === i ? e.target.value : x)))}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={`Remove ${label} ${i + 1}`}
            onClick={() => onChange(values.filter((_, j) => j !== i))}
          >
            <Trash2Icon />
          </Button>
        </div>
      ))}
      {values.length === 0 && <p className="text-xs text-muted-foreground">None</p>}
    </div>
  )
}
