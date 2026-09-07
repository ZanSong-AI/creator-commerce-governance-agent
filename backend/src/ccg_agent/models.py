from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

JsonValue = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_correlation", "correlation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    payload: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class Source(Timestamped, Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("stable_key", name="uq_sources_stable_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stable_key: Mapped[str] = mapped_column(String(120), nullable=False)
    publisher: Mapped[str] = mapped_column(String(180), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False, default="not_published")
    applicable_scope: Mapped[str] = mapped_column(Text, nullable=False)
    fetch_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    redistribution_note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="registered")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceSnapshot(Timestamped, Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_source_snapshot_hash"),
        Index("ix_source_snapshots_source", "source_id", "retrieved_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    locator_map: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    diff_from_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"), nullable=True
    )
    diff_summary: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    fetch_status: Mapped[str] = mapped_column(String(40), nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RequirementCandidate(Timestamped, Base):
    __tablename__ = "requirement_candidates"
    __table_args__ = (Index("ix_requirements_status", "status", "source_snapshot_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    exact_quote: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(String(250), nullable=False)
    actor: Mapped[str] = mapped_column(String(180), nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    required_action: Mapped[str] = mapped_column(Text, nullable=False)
    exception: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainties: Mapped[list[Any]] = mapped_column(JsonValue, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="candidate")
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    validation: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class RequirementReview(Base):
    __tablename__ = "requirement_reviews"
    __table_args__ = (
        UniqueConstraint("requirement_id", name="uq_requirement_review"),
        CheckConstraint(
            "length(trim(rationale)) >= 20",
            name="ck_requirement_reviews_rationale_min_20",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_candidates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    disposition: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(120), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Control(Timestamped, Base):
    __tablename__ = "controls"
    __table_args__ = (UniqueConstraint("stable_key", name="uq_controls_stable_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stable_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(60), nullable=False, default="deterministic")
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_config: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RequirementControlMapping(Timestamped, Base):
    __tablename__ = "requirement_control_mappings"
    __table_args__ = (
        UniqueConstraint("requirement_id", "control_id", "status", name="uq_mapping_version"),
        Index("ix_mappings_status", "status", "requirement_id"),
        CheckConstraint(
            "length(trim(rationale)) >= 20",
            name="ck_mapping_candidates_rationale_min_20",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_candidates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    control_id: Mapped[str] = mapped_column(
        ForeignKey("controls.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="candidate")
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class MappingReview(Base):
    __tablename__ = "mapping_reviews"
    __table_args__ = (
        UniqueConstraint("mapping_id", name="uq_mapping_review"),
        CheckConstraint(
            "length(trim(rationale)) >= 20",
            name="ck_mapping_reviews_rationale_min_20",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mapping_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_control_mappings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    disposition: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(120), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class MediaCase(Timestamped, Base):
    __tablename__ = "media_cases"
    __table_args__ = (UniqueConstraint("stable_key", name="uq_media_cases_stable_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stable_key: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_path: Mapped[str] = mapped_column(Text, nullable=False)
    asset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    jurisdiction: Mapped[str] = mapped_column(String(80), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False)
    platform_disclosure_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aigc_expected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    visible_aigc_label: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expected_outcomes: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready")


class EvidenceItem(Timestamped, Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        UniqueConstraint("case_id", "stable_key", name="uq_evidence_case_key"),
        Index("ix_evidence_case", "case_id", "evidence_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("media_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stable_key: Mapped[str] = mapped_column(String(180), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False)
    observed_value: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    timestamp_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript_span: Mapped[dict[str, Any] | None] = mapped_column(JsonValue, nullable=True)
    extractor: Mapped[str] = mapped_column(String(100), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class TestRun(Timestamped, Base):
    __tablename__ = "test_runs"
    __table_args__ = (UniqueConstraint("case_id", "mapping_id", "rule_version", name="uq_test_run"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("media_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mapping_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_control_mappings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    control_id: Mapped[str] = mapped_column(ForeignKey("controls.id", ondelete="RESTRICT"), nullable=False)
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    evidence_ids: Mapped[list[Any]] = mapped_column(JsonValue, nullable=False, default=list)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class Finding(Timestamped, Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("case_id", "test_run_id", name="uq_finding_test_run"),
        Index("ix_findings_status", "status", "case_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("media_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    test_run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id", ondelete="RESTRICT"), nullable=False)
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    control_id: Mapped[str] = mapped_column(ForeignKey("controls.id", ondelete="RESTRICT"), nullable=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JsonValue, nullable=False, default=list)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="candidate")
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False, default="deterministic-template")
    model_version: Mapped[str] = mapped_column(String(160), nullable=False, default="finding-v1")
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class FindingReview(Base):
    __tablename__ = "finding_reviews"
    __table_args__ = (
        UniqueConstraint("finding_id", name="uq_finding_review"),
        CheckConstraint(
            "length(trim(rationale)) >= 20",
            name="ck_finding_reviews_rationale_min_20",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    disposition: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(120), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class EvaluationRun(Timestamped, Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    failures: Mapped[list[Any]] = mapped_column(JsonValue, nullable=False, default=list)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class ReportExport(Timestamped, Base):
    __tablename__ = "report_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("media_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lineage_manifest: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope: Mapped[str] = mapped_column(String(120), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class CommerceGovernanceEvent(Base):
    __tablename__ = "commerce_governance_events"
    __table_args__ = (
        Index("ix_governance_events_timestamp", "event_timestamp"),
        Index("ix_governance_events_jurisdiction_type", "jurisdiction", "event_type"),
        Index("ix_governance_events_disposition", "review_disposition"),
    )

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    creator_id: Mapped[str] = mapped_column(String(36), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(40), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(40), nullable=False)
    disclosure_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    aigc_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(40), nullable=False)
    finding_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_disposition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
