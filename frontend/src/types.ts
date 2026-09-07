export type DependencyState = "ok" | "unavailable" | "unchecked" | "configured";

export interface HealthResponse {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  environment: string;
  dependencies: {
    database: DependencyState;
    redis: DependencyState;
    worker: DependencyState;
    cloud_enabled: boolean;
  };
}

export interface AuditEvent {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor_type: string;
  actor_id: string;
  correlation_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Overview {
  source_freshness: Record<string, number>;
  candidate_queue: Record<string, number>;
  review_backlog: number;
  media_cases: number;
  evaluation_status: string;
  recent_audit_events: AuditEvent[];
}

export interface Source {
  id: string;
  stable_key: string;
  publisher: string;
  title: string;
  official_url: string;
  source_type: string;
  jurisdiction: string;
  published_date: string | null;
  effective_date: string | null;
  version: string;
  applicable_scope: string;
  fetch_mode: string;
  redistribution_note: string;
  status: string;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegistrySync {
  registry_version: string;
  sources: number;
  created: number;
  updated: number;
  freshness_invalidated: number;
  changes: Array<Record<string, unknown>>;
  note: string;
}

export interface SourceSnapshotSummary {
  id: string;
  source_id: string;
  content_hash: string;
  retrieved_at: string;
  locator_map: Record<string, unknown>;
  diff_from_snapshot_id: string | null;
  diff_summary: Record<string, unknown>;
  fetch_status: string;
  immutable: boolean;
  created_at: string;
}

export interface Requirement {
  id: string;
  source_snapshot_id: string;
  exact_quote: string;
  source_locator: string;
  actor: string;
  trigger: string;
  required_action: string;
  exception: string | null;
  jurisdiction: string;
  effective_date: string | null;
  scope: string;
  confidence: number;
  uncertainties: unknown[];
  status: string;
  model_provider: string;
  model_version: string;
  prompt_version: string;
  validation: Record<string, unknown>;
  correlation_id: string;
  created_at: string;
  updated_at: string;
}

export interface RequirementReview {
  id: string;
  requirement_id: string;
  disposition: string;
  reviewer_type: string;
  reviewer_id: string;
  rationale: string;
  correlation_id: string;
  created_at: string;
}

export interface RequirementLineage {
  requirement: Requirement;
  snapshot: SourceSnapshotSummary;
  source: Source;
  reviews: RequirementReview[];
  review_context: {
    excerpt: string;
    excerpt_sha256: string | null;
    exact_quote_found: boolean;
    start_line: number | null;
    end_line: number | null;
    truncated: boolean;
  };
  authoritative_for_approval: boolean;
  latest_authoritative_snapshot_id: string | null;
  source_approval_blockers: string[];
}

export interface VerifiedExtraction {
  snapshot_id: string;
  source_key: string;
  candidates: Requirement[];
  created: number;
  note: string;
}

export interface Control {
  id: string;
  stable_key: string;
  name: string;
  description: string;
  evidence_kind: string;
  rule_type: string;
  rule_version: string;
  rule_config: Record<string, unknown>;
  active: boolean;
}

export interface Mapping {
  id: string;
  requirement_id: string;
  control_id: string;
  rationale: string;
  status: string;
  model_provider: string;
  model_version: string;
  correlation_id: string;
  created_at: string;
  updated_at: string;
}

export interface MappingReview {
  id: string;
  mapping_id: string;
  disposition: string;
  reviewer_type: string;
  reviewer_id: string;
  rationale: string;
  correlation_id: string;
  created_at: string;
}

export interface MappingLineage {
  mapping: Mapping;
  requirement: Requirement;
  control: Control;
  reviews: MappingReview[];
}

export interface MediaCase {
  id: string;
  stable_key: string;
  asset_path: string;
  asset_sha256: string;
  mime_type: string;
  caption: string;
  jurisdiction: string;
  relationship_type: string;
  platform_disclosure_flag: boolean;
  aigc_expected: boolean;
  visible_aigc_label: boolean;
  expected_outcomes: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  status: string;
}

export interface Evidence {
  id: string;
  case_id: string;
  stable_key: string;
  evidence_type: string;
  observed_value: Record<string, unknown>;
  timestamp_ms: number | null;
  frame_index: number | null;
  transcript_span: Record<string, unknown> | null;
  extractor: string;
  extractor_version: string;
  confidence: number | null;
  source_hash: string;
  correlation_id: string;
  created_at: string;
}

export interface Finding {
  id: string;
  case_id: string;
  test_run_id: string;
  requirement_id: string;
  control_id: string;
  evidence_ids: unknown[];
  title: string;
  explanation: string;
  uncertainty: string;
  status: string;
  correlation_id: string;
  created_at: string;
  updated_at: string;
}

export interface GovernanceTestRun {
  id: string;
  case_id: string;
  mapping_id: string;
  control_id: string;
  requirement_id: string;
  rule_version: string;
  status: string;
  result: Record<string, unknown>;
  evidence_ids: unknown[];
  correlation_id: string;
  created_at: string;
  updated_at: string;
}

export interface FindingReview {
  id: string;
  finding_id: string;
  disposition: string;
  reviewer_type: string;
  reviewer_id: string;
  rationale: string;
  correlation_id: string;
  created_at: string;
}

export interface FindingLineage {
  finding: Finding;
  test_run: GovernanceTestRun;
  requirement: Requirement;
  control: Control;
  evidence: Evidence[];
  reviews: FindingReview[];
}

export interface Evaluation {
  id: string;
  dataset_version: string;
  rule_version: string;
  status: string;
  metrics: Record<string, unknown>;
  failures: unknown[];
  correlation_id: string;
  created_at: string;
  updated_at: string;
}

export interface ReportExport {
  id: string;
  case_id: string;
  format: string;
  file_path: string;
  content_hash: string;
  lineage_manifest: Record<string, unknown>;
  correlation_id: string;
  created_at: string;
}
