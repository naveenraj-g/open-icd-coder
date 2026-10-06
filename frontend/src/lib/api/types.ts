import type { components } from "./schema"

type S = components["schemas"]

export type EncounterOut = S["EncounterOut"]
export type EncounterSummary = S["EncounterSummary"]
export type EncounterCreate = S["EncounterCreate"]
export type CodedItem = S["CodedItemOut"]
export type AIClassification = S["AIClassification"]
export type Alternative = S["Alternative"]
export type ItemReview = S["ItemReview"]
export type CodingSettings = S["CodingSettings"]
export type EngineInfo = S["EngineInfo"]
export type ItemCandidates = S["ItemCandidatesResponse"]
export type Candidate = S["CandidateOut"]

export type SearchResponse = S["SearchResponse"]
export type SearchHit = S["SearchHit"]
export type ConceptDetail = S["ConceptDetailResponse"]
export type ConceptSummary = S["ConceptSummary"]
export type CodeSystem = S["CodeSystemResponse"]

export type ItemStatus =
  | "pending"
  | "not_coded"
  | "no_candidates"
  | "scored"
  | "failed"
  | "approved"
  | "overridden"
  | "removed"
export type EncounterStatus = "processing" | "ready_for_review" | "reviewed" | "failed"
export type SearchMode = "hybrid" | "text" | "semantic"
