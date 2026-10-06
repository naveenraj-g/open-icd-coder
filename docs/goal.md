# Project Goal: AI-Augmented Medical Coding System (Prototype)

> **Stage:** Prototype. We are testing whether the approach works; this is not a production system.
> **Core technologies:** Terminology search engine (retrieval) + **Jev by TypeSafe AI** (decision layer) + Human-in-the-Loop (HITL) review dashboard
> **Prototype scope:** ICD-10-CM diagnosis codes, on de-identified data only

---

## 1. Executive Summary

Medical coding turns a clinician's free-text documentation into standard codes (e.g. ICD-10) that insurers and health systems can process. Today, trained coders do most of this by hand. It is **expensive, slow, and error-prone**.

This project is building a **prototype** to test one idea:

> *A retrieve-then-decide pipeline can suggest correct codes for clinical notes accurately enough, and with trustworthy enough confidence scores, to turn the coder's job from researching codes into reviewing suggestions.*

The prototype pipeline:

1. **Extracts** the codable clinical concepts (diagnoses) from a SOAP note.
2. **Retrieves** candidate ICD-10 codes for each concept with hybrid (vector + text) search.
3. **Decides** among those candidates with **Jev**, a non-autoregressive, type-safe decision model that returns a probability for each candidate.
4. **Assembles** the per-concept decisions into a list of encounter codes.
5. **Presents** the result in a simple review UI where a human approves or corrects each code.

The prototype's main output is **evidence** as much as software. We want measured answers on accuracy, calibration, latency and cost, compared against baselines. That evidence decides whether the idea is worth building toward production.

---

## 2. Problem Statement

### 2.1 How manual coding works today

| Step | Manual effort |
|---|---|
| Read the clinical note | Coder reads the full note, often unstructured and full of abbreviations |
| Identify codable concepts | Coder finds every diagnosis (and procedure) that needs a code |
| Look up terminology | Coder searches ICD-10 codebooks or encoder tools |
| Choose specificity | Coder tells apart near-identical codes (e.g. appendicitis *with localized* vs *generalized* peritonitis) |
| Sequence and validate | Coder orders the codes (principal diagnosis first), checks them against guidelines and submits |

### 2.2 Pain points

- **Cost:** Coding is skilled, labor-intensive work.
- **Latency:** Charts wait in queues, which delays claims and cash flow.
- **Errors:** Wrong or under-specific codes cause denials, underpayment or audit exposure.
- **Scalability:** Volume grows faster than hospitals can hire certified coders.

### 2.3 Why not just prompt a generative LLM?

- It can produce **codes that don't exist** or don't fit the documentation.
- It gives **no dependable confidence score** to route on.
- Putting many candidate descriptions in every prompt uses **a lot of tokens**.
- Autoregressive generation is **slower** than scoring options in parallel.

These are reasonable reasons to try a closed-set decision model. They are **still hypotheses to test**, though. An LLM can also be restricted to a candidate list, so the prototype compares against that baseline instead of assuming the answer (section 8).

---

## 3. Prototype Objectives

### 3.1 Questions the prototype must answer

| # | Question | How we'll answer it |
|---|---|---|
| H1 | Can hybrid retrieval reliably put the correct code in the candidate list? | Stage 1 recall@K on labeled data |
| H2 | Does Jev choose the correct code from the candidates more often than simpler baselines? | Top-1 / Top-5 accuracy vs. baselines |
| H3 | Are Jev's probabilities calibrated well enough to route on? | Reliability diagram, Expected Calibration Error (ECE) |
| H4 | Is the pipeline fast and cheap enough for interactive review? | p50/p95 latency and cost per encounter |
| H5 | Does the review UI make approving codes faster than manual lookup? | Informal timed review sessions (small sample) |

### 3.2 In scope

- **ICD-10-CM diagnosis codes** only.
- **Several diagnoses per encounter** (concept extraction, then one decision per concept).
- A "**none of the above**" option in every decision.
- An offline **evaluation harness** that runs on a labeled dataset.
- At least one **baseline decision layer** to compare against Jev.
- A **minimal review UI** with approve/override for each code and an audit trail.
- **De-identified or synthetic data only.**

### 3.3 Out of scope (deferred to post-prototype)

- Procedure codes (ICD-10-PCS, CPT), modifiers, DRG grouping.
- SNOMED-CT output and SNOMED→ICD mapping.
- Full sequencing logic under official coding guidelines (the prototype uses a simple rule; see 4.4).
- EHR / FHIR integration and clearinghouse submission (e.g. X12 837).
- Production concerns: HIPAA-grade infrastructure, multi-tenant auth, high availability.
- Fully autonomous coding with no human review.

---

## 4. Architecture

```
[ SOAP Note ]
      │
      ▼
┌──────────────────────────────────────────────┐
│ Stage 0: Concept Extraction                  │
│   - Split note into codable diagnoses        │
│   - Keep evidence span + assertion status    │
│     (confirmed / negated / uncertain)        │
└──────────────────────────────────────────────┘
      │   one item per concept
      ▼
┌──────────────────────────────────────────────┐
│ Stage 1: Terminology Search (per concept)    │
│   - Hybrid vector + lexical search           │
│   - Returns K candidates (K ≈ 50)            │
│   - Tuned for RECALL                         │
└──────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────┐
│ Stage 2: Decision Layer (per concept)        │
│   - Jev (or baseline) scores note context    │
│     vs. K candidates + "NONE_OF_THE_ABOVE"   │
│   - Returns a probability for each candidate │
└──────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────┐
│ Stage 3: Assembly & Routing                  │
│   - Drop duplicate / negated concepts        │
│   - Simple sequencing (principal dx first)   │
│   - Flag low-confidence or NOTA codes        │
│   - Save with isHumanReviewed = false        │
└──────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────┐
│ Stage 4: Human-in-the-Loop Review UI         │
│   - Each code pre-selected with confidence   │
│   - Ranked alternatives dropdown per code    │
│   - Approve / override / add / remove        │
│   - Flips isHumanReviewed = true             │
└──────────────────────────────────────────────┘
```

### 4.1 Stage 0: Concept Extraction *(added after design review)*

**Why it exists:** Real encounters need several codes. Searching once over a whole note mixes several problems into one query and hurts retrieval recall. Extracting concepts first gives each decision a narrow, clean input.

**Input:** SOAP note text.
**Output:** A list of concepts, each with:
- `text`: the normalized clinical phrase (e.g. "acute appendicitis with localized peritonitis")
- `evidence_span`: the character offsets in the note that support it
- `assertion`: `confirmed` | `negated` | `uncertain` | `history`
- `section`: which SOAP section it came from (Assessment is usually the most reliable)

**Prototype approach:** Start with whatever is quickest to make reliable. That could be an LLM extraction prompt with structured output, or a clinical NER model. This stage is **not** the thing being tested, so it only needs to be good enough not to limit the stages after it. Its recall is measured separately.

**Why assertion matters:** Negated findings ("no evidence of perforation") must not be coded. In outpatient coding, uncertain diagnoses ("possible", "rule out") are not coded either; the signs and symptoms are coded instead. The prototype at least **tags** assertion so these concepts can be excluded or flagged.

### 4.2 Stage 1: Terminology Search (per concept)

**Purpose:** Narrow ~70,000 ICD-10-CM codes down to a short list that very likely includes the right one.

**Index contents:** Each code's description, plus synonyms and ICD-10 index (alphabetic index) terms where available.

**Process:**
- **Vector search:** Embed the concept text and match it against embedded code descriptions.
- **Lexical search:** BM25-style keyword matching for exact terms, abbreviations and eponyms.
- **Hybrid merge:** Combine the two lists (e.g. reciprocal rank fusion) and remove duplicates.
- **Hierarchy expansion (optional):** If a parent category is retrieved (e.g. K35.3), add its billable child codes so the most specific code can be chosen.

**Key requirement: recall.** The decision layer can only pick what retrieval returns. We measure **recall@K** and choose K where recall levels off. We expect about 50, but the data decides.

### 4.3 Stage 2: Decision Layer (per concept)

**Purpose:** Pick the best-supported code for each concept and say how confident the pick is.

**Input:** The concept, its surrounding note context, and the K candidates **plus a `NONE_OF_THE_ABOVE` (NOTA) option**.

**Why NOTA is required:** Probabilities are spread across the supplied options only. Without a way out, the model can put high probability on the *least-wrong* candidate even when the correct code was never retrieved. That gives confident wrong answers, which is the worst failure for routing. NOTA lets the model say "retrieval missed it," and we route those cases to a human.

**Output (per concept):** A ranked list of `(code, probability)` including NOTA.

**Pluggable interface:** The decision layer sits behind one interface so Jev and the baselines can be swapped and compared on identical inputs:

```
decide(concept, note_context, candidates[]) -> [(code, probability)]  // sorted desc, includes NOTA
```

### 4.4 Stage 3: Assembly & Routing

- Remove concepts marked `negated` and merge concepts that resolve to the same code.
- **Simple sequencing:** Put first the code whose concept comes from the Assessment section and has the highest confidence. This is a placeholder; real principal-diagnosis rules are out of scope.
- **Routing flags for each code:**
  - `LOW_CONFIDENCE`: top probability below the threshold (starting value 0.75)
  - `NOTA`: NOTA was the top choice, or scored above a set level
  - `UNCERTAIN_ASSERTION`: the concept was tagged `uncertain`
- **Encounter-level route:** If *any* code is flagged, the whole encounter goes to the "needs close review" queue.
- Save the record with `isHumanReviewed = false`.

### 4.5 Stage 4: Human-in-the-Loop Review UI

A small UI; section 9 has the details.

---

## 5. Data Model (multi-code)

The single-code schema from the original proposal has been changed to hold **a list of coded concepts per encounter**.

```json
{
  "encounter_id": "enc_2026_98312A",
  "patient_id": "pat_4412",
  "clinical_input": {
    "soap_note": "Patient presents with acute inflammation of the appendix, showing signs of localized peritonitis. Recommending emergency laparoscopic appendectomy. Prescribed IV antibiotics.",
    "department": "Emergency Medicine"
  },
  "pipeline_meta": {
    "decision_engine": "jev",
    "engine_version": "x.y.z",
    "terminology_version": "ICD-10-CM 2026",
    "processed_at": "2026-09-26T10:15:00Z",
    "latency_ms": { "extraction": 0, "retrieval": 0, "decision": 0 }
  },
  "coded_concepts": [
    {
      "concept_id": "c1",
      "text": "acute appendicitis with localized peritonitis",
      "evidence_span": [22, 104],
      "assertion": "confirmed",
      "sequence": 1,
      "ai_classification": {
        "assigned_code": "K35.3x",
        "probability": 0.942,
        "top_alternatives": [
          { "code": "K35.80", "description": "Unspecified acute appendicitis", "probability": 0.041 },
          { "code": "K35.2x", "description": "Acute appendicitis with generalized peritonitis", "probability": 0.012 },
          { "code": "NONE_OF_THE_ABOVE", "description": "No candidate fits", "probability": 0.003 }
        ],
        "flags": []
      },
      "review": {
        "status": "pending",
        "final_code": "K35.3x"
      }
    }
  ],
  "routing": {
    "queue": "standard",
    "reasons": []
  },
  "audit_trail": {
    "isHumanReviewed": false,
    "reviewed_by": null,
    "reviewed_at": null,
    "final_billing_codes": ["K35.3x"]
  }
}
```

> **Note on the example codes:** ICD-10-CM's appendicitis codes (K35.2x / K35.3x) were expanded in recent code-set updates. The exact billable code depends on further detail (perforation, abscess, gangrene). The `x` placeholders are deliberate. The prototype must load a specific, versioned code-set release and validate codes against it. We should never hard-code examples.

### 5.1 Field reference (changes from the original proposal)

| Field | Description |
|---|---|
| `pipeline_meta` | **New.** Records which engine and code-set version produced the result, for reproducible evaluation |
| `coded_concepts[]` | **New.** Replaces the single `ai_classification`. One entry per extracted concept |
| `coded_concepts[].evidence_span` | **New.** Links each code to the text that supports it, for the reviewer and for audit |
| `coded_concepts[].assertion` | **New.** confirmed / negated / uncertain / history |
| `coded_concepts[].ai_classification.flags` | **New.** Routing flags (LOW_CONFIDENCE, NOTA, UNCERTAIN_ASSERTION) |
| `coded_concepts[].review` | **New.** Per-code review result: `approved`, `overridden`, `removed`, plus `final_code` |
| `routing` | **New.** Encounter-level queue and the reasons for it |
| `audit_trail.final_billing_codes` | Now a list, in order |
| `audit_trail.isHumanReviewed` | Unchanged. Still the gate: nothing is "final" until a human approves |

The AI's original output is **never overwritten**. Human decisions are stored beside it in `review`, so AI-vs-human agreement can be measured.

---

## 6. Confidence-Based Routing

| Condition (any code in the encounter) | Queue | Reviewer action |
|---|---|---|
| All codes ≥ threshold, no flags | Standard | Quick check, approve |
| Any code < threshold (start: **0.75**) | Close review | Careful review |
| NOTA is the top choice or high | Close review | Reviewer searches for the code manually; logged as a **retrieval miss** |
| Uncertain assertion | Close review | Decide whether to code it or code the symptoms |

**The threshold is a parameter, not a constant.** The prototype will plot, across thresholds, the % of encounters routed to close review against the error rate in the standard queue, then choose a value from that curve.

**Routing only works if the scores are calibrated.** If H3 fails (for example, 0.9-confidence predictions are right only 70% of the time), confidence routing is unsafe until the scores are recalibrated. Temperature scaling on a held-out set is the simple first fix.

---

## 7. Decision Layer: Jev and Baselines

### 7.1 Why Jev is the lead candidate

| Property | Claim | Status |
|---|---|---|
| Closed-set output | Can only return a supplied candidate: no invented codes | Structural. Easy to verify |
| Calibrated probabilities | Scores can be used for threshold routing | **To verify (H3)** |
| Latency | 70–500 ms per decision | **Vendor claim. To verify (H4)** |
| Cost | ~$0.042 per million input tokens | **Vendor claim. To verify (H4)** |
| Parallel scoring | Scores all candidates at once, not token by token | Architectural. Affects latency |

### 7.2 What "zero hallucination" does and doesn't mean

- ✅ Every suggested code is a **real, valid code** from the loaded code set.
- ❌ It does **not** make the suggested code **correct**. Picking a valid but wrong code (e.g. generalized instead of localized peritonitis) is still possible. It is also the more important billing error. That's why accuracy (H2) and calibration (H3) matter more than the closed-set property alone.

### 7.3 Baselines (same inputs, same interface)

| Baseline | Description | Why include it |
|---|---|---|
| **B0: Retrieval-only** | Take the top-ranked Stage 1 candidate | Shows how much the decision layer adds |
| **B1: Cross-encoder reranker** | A cross-encoder that scores (context, code description) pairs, with softmax over candidates | Cheap, fast, strong standard approach |
| **B2: Restricted LLM** | An LLM told to pick one ID from the numbered candidate list (structured output / enum), with probabilities from token logprobs or repeated sampling | The "why not just use an LLM?" comparison |

Jev "wins" only if it beats these on the metrics in section 10 **enough to justify the added dependency**.

---

## 8. Evaluation Plan

### 8.1 Data

| Option | Pros | Cons |
|---|---|---|
| **MIMIC-IV + MIMIC-IV-Note** (PhysioNet) | Real de-identified notes with ICD-10 labels; the standard research benchmark | Needs PhysioNet credentialed access (CITI training + data use agreement); notes are discharge summaries, not SOAP notes; labels are per-admission, not per-concept |
| **Synthetic SOAP notes** | Fast, no access barrier, can target hard cases (specificity, negation) | Not realistic; risk of evaluating on our own assumptions |
| **Hand-labeled mini set** | Per-concept gold labels, exactly our format | Small; takes labeling effort |

**Plan:** Start with a **small hand-labeled / synthetic set (~50–100 notes)** to build and debug the pipeline end to end. Apply for MIMIC access in parallel and use it for the main numbers once it is approved.

**Rules:** Never use real, identifiable patient data in the prototype. Keep a fixed held-out test split and do not tune on it.

### 8.2 Metrics

| Stage | Metric |
|---|---|
| Stage 0 | Concept recall (were all gold diagnoses extracted?), assertion accuracy |
| Stage 1 | **Recall@K** (is the gold code among the candidates?) for K = 10, 25, 50, 100 |
| Stage 2 | Top-1 / Top-5 accuracy *given the gold code was retrieved*; NOTA precision/recall when it wasn't |
| Stage 2 | **Calibration:** ECE, reliability diagram, Brier score |
| End-to-end | Encounter-level micro/macro F1 over code sets; exact-match rate |
| End-to-end | Accuracy at each hierarchy level (right category, wrong specificity), because near-misses matter |
| Routing | % routed to close review vs. error rate in standard queue, across thresholds |
| System | p50 / p95 latency per stage; cost per encounter |
| UI (informal) | Time to approve an encounter; override rate |

### 8.3 Deliverable

An **evaluation report** with one table comparing Jev, B0, B1 and B2 on all Stage 2 and end-to-end metrics, plus calibration plots and a recommendation: continue with Jev, switch, or combine.

---

## 9. Review UI (prototype scope)

Keep it minimal. The UI mainly demonstrates the workflow and supports the informal H5 timing.

- **Note panel:** The SOAP note, with each concept's **evidence span highlighted**.
- **Code list:** One row per coded concept, in order, each showing:
  - **Auto-selected code** with its confidence (e.g. `K35.3x · 94.2%`)
  - Flags (low confidence / NOTA / uncertain) shown as visible badges
  - **Ranked alternatives dropdown** with the next ~10–15 candidates by probability
  - Actions: **Approve**, **Override** (pick from the dropdown or search manually), **Remove**
- **Add code:** Manual search for a code the pipeline missed. This is logged as a missed concept or retrieval miss.
- **Approve encounter:** Enabled once every code has been dealt with. Sets `isHumanReviewed = true` and records reviewer and timestamp.
- **Queue view:** Standard vs. close-review lists.

Every override, removal and addition is logged. **This log is the most valuable output of the UI**, because it shows exactly where the pipeline fails.

---

## 10. Success Criteria for the Prototype

The targets below are **initial guesses to be revised** once we have a baseline. They define "promising enough to keep going," not production readiness.

| Criterion | Initial target |
|---|---|
| Stage 1 recall@50 | ≥ 95% |
| Stage 2 Top-1 accuracy (gold retrieved) | Clearly above B0 and at least equal to B1/B2 |
| Top-5 accuracy | ≥ 95% (so the right answer is almost always in the dropdown) |
| Calibration (ECE) | Low enough that the threshold curve gives a usable operating point |
| Decision latency | p95 < 1 s per concept |
| End-to-end latency | p95 < 5 s per encounter |

If H1 fails, fix retrieval before judging the decision layer. If H3 fails, recalibrate before using confidence routing.

---

## 11. Known Risks and Limitations

| Risk | Impact | Prototype mitigation |
|---|---|---|
| **One code per encounter** (original design) | Can't produce a realistic claim | **Addressed:** multi-concept pipeline (Stage 0) and multi-code schema |
| **Retrieval misses the right code** | Decision layer cannot recover | Measure recall@K; hybrid search; hierarchy expansion; NOTA option |
| **Overconfident wrong answers** | Unsafe routing | NOTA option; calibration measurement; temperature scaling |
| **"Zero hallucination" misread as "always correct"** | False sense of safety | Report accuracy and calibration, not just validity (7.2) |
| **Vendor claims unverified** (latency, cost, calibration) | Architecture built on shaky assumptions | Pluggable decision layer; head-to-head baselines |
| **Coding-guideline rules ignored** (negation, uncertain dx, sequencing) | Codes a coder would reject | Assertion tagging; simple sequencing placeholder; full rules deferred |
| **Automation bias** (reviewers approve without checking) | Errors pass review | Out of scope for the prototype; logged override/approve times give early signal |
| **Code-set versioning** (annual ICD-10-CM updates) | Stale or invalid codes | Load a pinned, versioned release; validate every output code against it |
| **Evaluation data mismatch** (discharge summaries ≠ SOAP notes) | Results may not transfer | Report results per dataset separately; include some SOAP-format notes |
| **Upcoding / compliance** (production concern) | Legal exposure under billing-fraud rules | Out of scope for the prototype, but the audit trail design already supports it |

---

## 12. Compliance Stance (Prototype)

- **De-identified or synthetic data only.** No real PHI enters the prototype.
- If MIMIC is used, follow the **PhysioNet data use agreement**. In particular, do **not** send MIMIC notes to third-party APIs unless the agreement allows it. Check this for Jev and any hosted LLM baseline **before** running them on MIMIC.
- The audit trail (AI suggestion kept separate from the human decision, reviewer identity, timestamps) is built now, because it is cheap to include and expensive to add later.

---

## 13. Milestones

| # | Milestone | Output |
|---|---|---|
| M1 | **Data & terminology** | ICD-10-CM code set loaded (versioned); 50–100-note labeled dev set; MIMIC access applied for |
| M2 | **Retrieval** | Hybrid search index; recall@K report (answers H1) |
| M3 | **Concept extraction** | Stage 0 working; concept recall + assertion accuracy on dev set |
| M4 | **Decision layer + baselines** | Pluggable interface; Jev, B0, B1, B2 implemented; NOTA supported |
| M5 | **Evaluation harness** | One command runs the full pipeline and writes the metrics report (H2, H3, H4) |
| M6 | **Review UI** | Minimal HITL UI with audit logging; informal timing sessions (H5) |
| M7 | **Findings report** | Comparison table, calibration plots, threshold curve, go/no-go recommendation |

M2 and M3 can run in parallel. M6 can start once the data model (section 5) is stable.

---

## 14. Open Questions

1. **Jev access:** What are the API shape, rate limits and data-handling terms? Can it be used with MIMIC data under the DUA?
2. **Concept extraction method:** LLM-based vs. clinical NER model. Which is faster to make reliable?
3. **Context window for decisions:** Should the decision layer see only the concept's evidence span, the whole section, or the whole note?
4. **Hierarchy handling:** Should candidates include non-billable parent codes, or only billable leaf codes?
5. **After the prototype:** If the results are good, what comes first: procedures (PCS/CPT), full sequencing rules, or EHR/FHIR integration?

---

## 15. Glossary

| Term | Meaning |
|---|---|
| **SOAP note** | Standard clinical note layout: Subjective, Objective, Assessment, Plan |
| **ICD-10-CM** | ICD-10 Clinical Modification: US diagnosis codes used for billing |
| **ICD-10-PCS / CPT** | Procedure code systems (inpatient / outpatient). Out of prototype scope |
| **SNOMED-CT** | Clinical terminology for detailed documentation; not a billing code set |
| **HITL** | Human-in-the-Loop: a person reviews and approves automated output |
| **Jev** | Non-autoregressive, type-safe decision model by TypeSafe AI that picks from a supplied set of options with probabilities |
| **NOTA** | "None of the above": an extra option that lets the decision layer reject every candidate |
| **Assertion status** | Whether a concept is confirmed, negated, uncertain, or historical in the note |
| **Recall@K** | % of cases where the correct answer is in the top K retrieved candidates |
| **Calibration / ECE** | How closely predicted probabilities match observed accuracy; Expected Calibration Error summarizes the gap |
| **Cross-encoder** | A model that reads a query and a candidate together and outputs a relevance score |
| **MIMIC-IV** | Public, de-identified critical-care dataset from PhysioNet, widely used for clinical NLP research |
