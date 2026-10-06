# Open ICD Coder — Frontend

The review UI for the AI-augmented ICD-10-CM coding prototype: submit a SOAP note, review the suggested code for each condition, and approve it with an audit trail. Project overview, setup and data downloads are in the **[main README](../README.md)**; system design in **[ARCHITECTURE.md](../ARCHITECTURE.md)**.

**Stack:** Next.js 16 (App Router, `src/`, Turbopack) · React 19 · TypeScript · Tailwind CSS 4 · [shadcn/ui](https://ui.shadcn.com/) (`base-nova` style, built on [Base UI](https://base-ui.com/)) · [openapi-fetch](https://openapi-ts.dev/openapi-fetch/) with types generated from the backend's OpenAPI spec.

---

## Run

The backend must be running first (`just dev` in `../backend`, on `http://127.0.0.1:8001`).

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
pnpm install
pnpm dev                     # http://localhost:3000
```

| Command | What it does |
|---|---|
| `pnpm dev` | Dev server |
| `pnpm build` / `pnpm start` | Production build / serve it |
| `pnpm lint` | ESLint |
| `pnpm gen:api` | Regenerate `src/lib/api/schema.d.ts` from `openapi.json` |

> Use `127.0.0.1`, not `localhost`, for the API URL — on Windows `localhost` tries IPv6 first and adds ~200 ms to every request.

---

## Pages

The sidebar groups pages by task:

| Group | Route | Page |
|---|---|---|
| Overview | `/` | **Dashboard** — queue counts, recent encounters, pipeline summary, default-engine warning |
| Coding | `/coding/new` | **New encounter** — SOAP note + conditions (coded) and observations / service / medication requests (stored only); engine picker; built-in synthetic examples |
| | `/coding/encounters` | **Review queue** — filter by queue, status, reviewed (kept in the URL) |
| | `/coding/encounters/[encounterId]` | **Review** — per condition: suggested code, probability, flags, ranked alternatives, approve / override / remove; all 100 candidates (resizable side panel); rescore; approve encounter; audit trail; SOAP note with findings highlighted |
| Terminology | `/terminology` | **ICD-10-CM search** — hybrid / text / semantic, billable filter; shows why each code matched |
| | `/terminology/codes/[code]` | **Code detail** — parent, children, inclusion terms, notes and inherited notes |
| System | `/system` | **Status & engines** — backend/DB health, terminology and embedding coverage, engines, thresholds |

There is no login: the reviewer enters a name in the header (stored in the browser) and it's sent with every review action.

---

## Structure

```
src/
├── app/                      routes (server components fetch data on each request)
├── components/
│   ├── coding/               review card, override picker, candidates sheet, new-encounter form, …
│   ├── terminology/          search panel
│   ├── ui/                   shadcn/ui components
│   └── …                     sidebar, header, badges, providers, DateTime, LinkButton
├── hooks/                    use-mobile, use-resizable-width
└── lib/
    ├── api/                  client.ts (typed client + errors), schema.d.ts (generated), types.ts
    ├── examples.ts           synthetic example notes
    └── labels.ts             wording for statuses, flags, notes
```

---

## Working on it

**API changes.** Types come from the backend's OpenAPI spec, so a backend change that breaks the UI fails the type check:

```bash
cd ../backend && just openapi     # writes ../frontend/openapi.json
cd ../frontend && pnpm gen:api    # regenerates src/lib/api/schema.d.ts
pnpm exec tsc --noEmit
```

**Data fetching.** Pages are server components calling the API with `cache: "no-store"`. Interactive parts (review actions, search, override picker) are client components that call the API and update local state from the response.

**Things that differ from older Next.js / shadcn versions:**
- Next.js 16: `params` and `searchParams` are async (`await props.params`); use the generated `PageProps<"/route">` / `LayoutProps` types. Bundled docs: `node_modules/next/dist/docs/`.
- shadcn `base-nova` uses Base UI, not Radix: compose with `render={<Link … />}` instead of `asChild`. A `Button` rendered as a link needs `nativeButton={false}` — use the `LinkButton` component.
- Dates that depend on the viewer's locale or time zone must use `<DateTime>` (not `toLocaleString` during render), or hydration fails.
- Turbopack's on-disk cache is disabled in `next.config.ts`: it served stale Tailwind CSS (new classes never generated).
