from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ServiceState(BaseModel):
    database: Literal["ok", "unavailable", "unchecked"]
    redis: Literal["ok", "unavailable", "unchecked"]
    worker: Literal["configured", "unchecked"]
    cloud_enabled: bool


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str
    environment: str
    dependencies: ServiceState


class AuditEventOut(ORMModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str
    actor_type: str
    actor_id: str
    correlation_id: str
    payload: dict[str, Any]
    created_at: datetime


class SourceCreate(BaseModel):
    stable_key: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9-]+$")
    publisher: str = Field(min_length=2, max_length=180)
    title: str = Field(min_length=3, max_length=300)
    official_url: HttpUrl
    source_type: str = Field(min_length=3, max_length=60)
    jurisdiction: str = Field(min_length=2, max_length=80)
    published_date: date | None = None
    effective_date: date | None = None
    version: str = Field(min_length=1, max_length=100)
    applicable_scope: str = Field(min_length=5)
    fetch_mode: str = Field(min_length=3, max_length=60)
    redistribution_note: str = Field(min_length=5)


class SourceOut(ORMModel):
    id: str
    stable_key: str
    publisher: str
    title: str
    official_url: str
    source_type: str
    jurisdiction: str
    published_date: date | None
    effective_date: date | None
    version: str
    applicable_scope: str
    fetch_mode: str
    redistribution_note: str
    status: str
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RegistrySyncOut(BaseModel):
    registry_version: str
    sources: int
    created: int
    updated: int
    freshness_invalidated: int
    changes: list[dict[str, Any]]
    note: str


class SnapshotManualCreate(BaseModel):
    content_text: str = Field(min_length=20, max_length=2_000_000)
    source_locator_note: str = Field(min_length=3, max_length=500)
    confirmed_official_url: HttpUrl


class SourceSnapshotOut(ORMModel):
    id: str
    source_id: str
    content_hash: str
    content_text: str
    retrieved_at: datetime
    locator_map: dict[str, Any]
    diff_from_snapshot_id: str | None
    diff_summary: dict[str, Any]
    fetch_status: str
    immutable: bool
    created_at: datetime


class SourceSnapshotSummaryOut(ORMModel):
    id: str
    source_id: str
    content_hash: str
    retrieved_at: datetime
    locator_map: dict[str, Any]
    diff_from_snapshot_id: str | None
    diff_summary: dict[str, Any]
    fetch_status: str
    immutable: bool
    created_at: datetime


class RequirementExtractRequest(BaseModel):
    provider: Literal["fixture", "ollama"] = "fixture"


class RequirementExtractionPayload(BaseModel):
    """Strict local-model contract before any candidate can be persisted."""

    model_config = ConfigDict(extra="forbid")

    exact_quote: str = Field(min_length=1, max_length=12_000)
    source_locator: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=500)
    trigger: str = Field(min_length=1, max_length=2_000)
    required_action: str = Field(min_length=1, max_length=2_000)
    exception: str | None
    jurisdiction: str = Field(min_length=1, max_length=120)
    effective_date: date | None
    scope: str = Field(min_length=1, max_length=2_000)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainties: list[str] = Field(max_length=20)


class RequirementOut(ORMModel):
    id: str
    source_snapshot_id: str
    exact_quote: str
    source_locator: str
    actor: str
    trigger: str
    required_action: str
    exception: str | None
    jurisdiction: str
    effective_date: date | None
    scope: str
    confidence: float
    uncertainties: list[Any]
    status: str
    model_provider: str
    model_version: str
    prompt_version: str
    validation: dict[str, Any]
    correlation_id: str
    created_at: datetime
    updated_at: datetime


class RequirementReviewOut(ORMModel):
    id: str
    requirement_id: str
    disposition: str
    reviewer_type: str
    reviewer_id: str
    rationale: str
    correlation_id: str
    created_at: datetime


class RequirementReviewContextOut(BaseModel):
    excerpt: str
    excerpt_sha256: str | None
    exact_quote_found: bool
    start_line: int | None
    end_line: int | None
    truncated: bool


class RequirementLineageOut(BaseModel):
    requirement: RequirementOut
    snapshot: SourceSnapshotSummaryOut
    source: SourceOut
    reviews: list[RequirementReviewOut]
    review_context: RequirementReviewContextOut
    authoritative_for_approval: bool
    latest_authoritative_snapshot_id: str | None
    source_approval_blockers: list[str]


class VerifiedExtractionOut(BaseModel):
    snapshot_id: str
    source_key: str
    candidates: list[RequirementOut]
    created: int
    note: str


class HumanReviewRequest(BaseModel):
    disposition: str = Field(min_length=3, max_length=60)
    rationale: str = Field(min_length=20, max_length=4000)

    @field_validator("rationale")
    @classmethod
    def trim_and_require_meaningful_rationale(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 20:
            raise ValueError("review rationale must contain at least 20 non-whitespace characters")
        return trimmed


class ControlCreate(BaseModel):
    stable_key: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=5)
    evidence_kind: str = Field(min_length=3, max_length=80)
    rule_version: str = Field(min_length=1, max_length=80)
    rule_config: dict[str, Any] = Field(default_factory=dict)


class ControlOut(ORMModel):
    id: str
    stable_key: str
    name: str
    description: str
    evidence_kind: str
    rule_type: str
    rule_version: str
    rule_config: dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: datetime


class MappingCreate(BaseModel):
    requirement_id: str
    control_id: str
    rationale: str = Field(min_length=20, max_length=4000)
    provider: Literal["human-authored", "ollama", "fixture"] = "human-authored"


class MappingOut(ORMModel):
    id: str
    requirement_id: str
    control_id: str
    rationale: str
    status: str
    model_provider: str
    model_version: str
    correlation_id: str
    created_at: datetime
    updated_at: datetime


class MappingReviewOut(ORMModel):
    id: str
    mapping_id: str
    disposition: str
    reviewer_type: str
    reviewer_id: str
    rationale: str
    correlation_id: str
    created_at: datetime


class MappingLineageOut(BaseModel):
    mapping: MappingOut
    requirement: RequirementOut
    control: ControlOut
    reviews: list[MappingReviewOut]


class MediaCaseCreate(BaseModel):
    stable_key: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9-]+$")
    asset_path: str = Field(min_length=3, max_length=1000)
    asset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    mime_type: Literal["video/mp4"] = "video/mp4"
    caption: str = Field(default="", max_length=20_000)
    jurisdiction: str = Field(min_length=2, max_length=80)
    relationship_type: Literal["own_brand", "paid", "affiliate", "free_product", "none"]
    platform_disclosure_flag: bool = False
    aigc_expected: bool = False
    visible_aigc_label: bool = False
    expected_outcomes: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class MediaCaseOut(ORMModel):
    id: str
    stable_key: str
    asset_path: str
    asset_sha256: str
    mime_type: str
    caption: str
    jurisdiction: str
    relationship_type: str
    platform_disclosure_flag: bool
    aigc_expected: bool
    visible_aigc_label: bool
    expected_outcomes: dict[str, Any]
    metadata_json: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class EvidenceOut(ORMModel):
    id: str
    case_id: str
    stable_key: str
    evidence_type: str
    observed_value: dict[str, Any]
    timestamp_ms: int | None
    frame_index: int | None
    transcript_span: dict[str, Any] | None
    extractor: str
    extractor_version: str
    confidence: float | None
    source_hash: str
    correlation_id: str
    created_at: datetime


class TestRunOut(ORMModel):
    id: str
    case_id: str
    mapping_id: str
    control_id: str
    requirement_id: str
    rule_version: str
    status: str
    result: dict[str, Any]
    evidence_ids: list[Any]
    correlation_id: str
    created_at: datetime
    updated_at: datetime


class FindingOut(ORMModel):
    id: str
    case_id: str
    test_run_id: str
    requirement_id: str
    control_id: str
    evidence_ids: list[Any]
    title: str
    explanation: str
    uncertainty: str
    status: str
    correlation_id: str
    created_at: datetime
    updated_at: datetime


class FindingReviewOut(ORMModel):
    id: str
    finding_id: str
    disposition: str
    reviewer_type: str
    reviewer_id: str
    rationale: str
    correlation_id: str
    created_at: datetime


class FindingLineageOut(BaseModel):
    finding: FindingOut
    test_run: TestRunOut
    requirement: RequirementOut
    control: ControlOut
    evidence: list[EvidenceOut]
    reviews: list[FindingReviewOut]


class EvaluationOut(ORMModel):
    id: str
    dataset_version: str
    rule_version: str
    status: str
    metrics: dict[str, Any]
    failures: list[Any]
    correlation_id: str
    created_at: datetime
    updated_at: datetime


class ReportExportRequest(BaseModel):
    formats: list[Literal["html", "pdf", "json", "csv"]] = Field(min_length=1)


class ReportExportOut(ORMModel):
    id: str
    case_id: str
    format: str
    file_path: str
    content_hash: str
    lineage_manifest: dict[str, Any]
    correlation_id: str
    created_at: datetime


class BootstrapResponse(BaseModel):
    sources: int
    snapshots: int
    requirement_candidates: int
    controls: int
    mappings: int
    note: str


class OverviewResponse(BaseModel):
    source_freshness: dict[str, int]
    candidate_queue: dict[str, int]
    review_backlog: int
    media_cases: int
    evaluation_status: str
    recent_audit_events: list[AuditEventOut]
