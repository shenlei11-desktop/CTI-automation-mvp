// Mirrors app/schemas/*.py. Kept in sync by hand -- there's no shared schema
// generation step, so a backend field rename needs updating here too.

export type Recommendation = "proceed" | "flag_for_review"

export interface SourceSpan {
  sentence: string
  start: number
  end: number
}

// -- ingestion (app/schemas/ingestion.py) -----------------------------------

export type IngestSourceType = "text" | "html" | "url" | "pdf"

export interface IngestQuality {
  recommendation: Recommendation
  reason: string
}

export interface IngestResponse {
  text: string
  title: string | null
  source_type: IngestSourceType
  quality: IngestQuality
}

export interface FeedItem {
  title: string
  url: string
  published: string | null
}

export interface FeedResponse {
  items: FeedItem[]
}

// -- extraction (app/schemas/extraction.py) ----------------------------------

export type IOCType = "ipv4" | "domain" | "md5" | "sha1" | "sha256" | "cve"
export type EntityType =
  | "threat_actor"
  | "ics_vendor"
  | "sector"
  | "organization"
  | "location"
  | "person"

export interface IOC {
  type: IOCType
  value_raw: string
  value_normalized: string
  is_private: boolean | null
  source: SourceSpan
}

export interface Entity {
  type: EntityType
  text: string
  method: "gazetteer" | "spacy_ner"
  source: SourceSpan
}

export interface ExtractionQuality {
  n_iocs: number
  n_entities: number
  text_length: number
  signal_density: number
  recommendation: Recommendation
  reason: string
}

export interface ExtractResponse {
  report_id: string | null
  iocs: IOC[]
  entities: Entity[]
  quality: ExtractionQuality
}

// -- classification (app/schemas/classification.py) -------------------------

export interface TechniqueMatch {
  technique_id: string
  technique_name: string
  tactics: string[]
  retrieval_score: number
  rerank_score: number
}

export interface ClassificationQuality {
  top1_score: number | null
  top1_margin: number | null
  recommendation: Recommendation
  reason: string
}

export interface BehaviorClassification {
  text: string
  source: SourceSpan | null
  matches: TechniqueMatch[]
  quality: ClassificationQuality
}

export interface BehaviorEvidence {
  text: string
  source: SourceSpan | null
}

export interface TechniqueRollup {
  technique_id: string
  technique_name: string
  tactics: string[]
  attack_url: string
  mitigation: string
  best_rerank_score: number
  best_margin: number | null
  recommendation: Recommendation
  evidence: BehaviorEvidence[]
}

export interface ClassifyResponse {
  report_id: string | null
  behaviors: BehaviorClassification[]
  techniques: TechniqueRollup[]
}

// -- triage (app/schemas/triage.py) ------------------------------------------

export type KEVStatus = "listed" | "not_listed" | "unknown"
export type ExposureLevel = "internet_facing" | "segmented" | "unknown"
export type AssetTier = "safety_critical" | "process_critical" | "monitoring_only" | "unknown"
export type SeverityBand = "Critical" | "High" | "Medium" | "Low"
export type TriageDecision = "scored" | "needs_clarification"

export interface RuleTrace {
  rule: string
  detail: string
  resulting_band: SeverityBand
  source: SourceSpan | null
}

export interface CVEFinding {
  cve_id: string | null
  cvss_score: number | null
  kev_status: KEVStatus
  severity: SeverityBand
  rule_trace: RuleTrace[]
  source: SourceSpan | null
}

export interface TriageContext {
  exposure: ExposureLevel
  exposure_source: SourceSpan | null
  asset_tier: AssetTier
  asset_tier_source: SourceSpan | null
}

export interface TriageQuality {
  decision: TriageDecision
  reason: string
}

export interface TriageResponse {
  report_id: string | null
  context: TriageContext
  findings: CVEFinding[]
  quality: TriageQuality
}

// -- orchestration (app/schemas/orchestration.py) ----------------------------

export type AdvisoryStatus = "completed" | "needs_extraction_review" | "needs_clarification"

export interface TraceEntry {
  node: string
  detail: string
}

export interface AdvisoryResponse {
  report_id: string | null
  status: AdvisoryStatus
  extraction: ExtractResponse | null
  classification: ClassifyResponse | null
  triage: TriageResponse | null
  trace: TraceEntry[]
  report: string
}
