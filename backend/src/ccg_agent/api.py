from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .audit import record_event
from .database import get_db
from .models import (
    AuditEvent,
    Control,
    EvaluationRun,
    EvidenceItem,
    Finding,
    FindingReview,
    MappingReview,
    MediaCase,
    ReportExport,
    RequirementCandidate,
    RequirementControlMapping,
    RequirementReview,
    Source,
    SourceSnapshot,
    TestRun,
)
from .schemas import (
    BootstrapResponse,
    ControlCreate,
    ControlOut,
    EvaluationOut,
    EvidenceOut,
    FindingLineageOut,
    FindingOut,
    HumanReviewRequest,
    MappingCreate,
    MappingLineageOut,
    MappingOut,
    MediaCaseCreate,
    MediaCaseOut,
    OverviewResponse,
    RegistrySyncOut,
    ReportExportOut,
    ReportExportRequest,
    RequirementExtractRequest,
    RequirementLineageOut,
    RequirementOut,
    SnapshotManualCreate,
    SourceCreate,
    SourceOut,
    SourceSnapshotOut,
    SourceSnapshotSummaryOut,
    VerifiedExtractionOut,
)
from .services.bootstrap import bootstrap_demo
from .services.governance import (
    create_fixture_candidates,
    create_mapping_candidate,
    extract_with_ollama,
    review_finding,
    review_mapping,
    review_requirement,
    source_approval_evidence,
)
from .services.idempotency import remember, replay_or_conflict
from .services.media import extract_evidence, load_media_cases, run_approved_controls
from .services.reports import export_report
from .services.sources import (
    load_registry,
    refresh_official_source,
    requirement_review_context,
    store_manual_snapshot,
    sync_registry_sources,
)
from .settings import get_settings
from .worker import analyze_media_case, run_gold_evaluation_task

router = APIRouter(prefix="/api/v1")
DatabaseSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)]
ReviewerId = Annotated[str, Header(alias="X-Reviewer-Id", min_length=2, max_length=120)]


def _get_or_404(session: Session, model: type, entity_id: str):
    value = session.get(model, entity_id)
    if value is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return value


@router.get("/overview", response_model=OverviewResponse)
def overview(db: DatabaseSession) -> dict:
    sources = dict(db.execute(select(Source.status, func.count()).group_by(Source.status)).all())
    requirements = dict(
        db.execute(
            select(RequirementCandidate.status, func.count()).group_by(RequirementCandidate.status)
        ).all()
    )
    mappings = dict(
        db.execute(
            select(RequirementControlMapping.status, func.count()).group_by(RequirementControlMapping.status)
        ).all()
    )
    review_backlog = int(requirements.get("candidate", 0)) + int(mappings.get("candidate", 0))
    media_cases = db.scalar(select(func.count()).select_from(MediaCase)) or 0
    evaluation = db.scalar(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1))
    events = list(db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10)))
    return {
        "source_freshness": {str(k): int(v) for k, v in sources.items()},
        "candidate_queue": {
            **{f"requirement_{k}": int(v) for k, v in requirements.items()},
            **{f"mapping_{k}": int(v) for k, v in mappings.items()},
        },
        "review_backlog": review_backlog,
        "media_cases": int(media_cases),
        "evaluation_status": evaluation.status if evaluation else "not_run",
        "recent_audit_events": events,
    }


@router.post("/demo/bootstrap", response_model=BootstrapResponse)
def bootstrap(db: DatabaseSession, idempotency_key: IdempotencyKey) -> dict:
    registry = load_registry(get_settings())
    payload = {
        "registry": registry["registry_version"],
        "fixture": "verified_requirements",
    }
    replay = replay_or_conflict(db, scope="demo.bootstrap", key=idempotency_key, payload=payload)
    if replay:
        return replay
    result = bootstrap_demo(db, get_settings())
    remember(db, scope="demo.bootstrap", key=idempotency_key, payload=payload, response_body=result)
    record_event(
        db,
        event_type="demo.bootstrapped",
        entity_type="system",
        entity_id="public-fixture",
        actor_type="human",
        actor_id="local-operator",
        payload=result,
    )
    return result


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: DatabaseSession) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.publisher, Source.title)))


@router.post("/sources/sync-registry", response_model=RegistrySyncOut)
def sync_source_registry(db: DatabaseSession, idempotency_key: IdempotencyKey) -> dict:
    registry = load_registry(get_settings())
    payload = {"registry_version": registry["registry_version"], "operation": "sync_registry"}
    replay = replay_or_conflict(db, scope="sources.sync_registry", key=idempotency_key, payload=payload)
    if replay:
        return replay
    _, result = sync_registry_sources(db, get_settings())
    remember(
        db,
        scope="sources.sync_registry",
        key=idempotency_key,
        payload=payload,
        response_body=result,
    )
    record_event(
        db,
        event_type="source.registry_synced",
        entity_type="source_registry",
        entity_id=str(result["registry_version"]),
        actor_type="human",
        actor_id="local-operator",
        payload=result,
    )
    return result


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(
    payload: SourceCreate, db: DatabaseSession, idempotency_key: IdempotencyKey
) -> Source | dict:
    body = payload.model_dump(mode="json")
    replay = replay_or_conflict(db, scope="sources.create", key=idempotency_key, payload=body)
    if replay:
        return replay
    if db.scalar(select(Source).where(Source.stable_key == payload.stable_key)):
        raise HTTPException(status_code=409, detail="Source stable_key already exists")
    source = Source(**payload.model_dump(), official_url=str(payload.official_url))
    db.add(source)
    db.commit()
    db.refresh(source)
    response = SourceOut.model_validate(source).model_dump(mode="json")
    remember(
        db,
        scope="sources.create",
        key=idempotency_key,
        payload=body,
        response_body=response,
        response_status=201,
    )
    record_event(
        db,
        event_type="source.registered",
        entity_type="source",
        entity_id=source.id,
        actor_type="human",
        actor_id="local-operator",
        payload={"stable_key": source.stable_key, "official_url": source.official_url},
    )
    return source


@router.get("/sources/{source_id}/snapshots", response_model=list[SourceSnapshotSummaryOut])
def list_source_snapshots(
    source_id: str,
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[SourceSnapshot]:
    _get_or_404(db, Source, source_id)
    return list(
        db.scalars(
            select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id)
            .order_by(SourceSnapshot.retrieved_at.desc())
            .limit(limit)
        )
    )


@router.post("/sources/{source_id}/refresh", response_model=SourceSnapshotOut)
def refresh_source(
    source_id: str, db: DatabaseSession, idempotency_key: IdempotencyKey
) -> SourceSnapshot | dict:
    payload = {"source_id": source_id, "operation": "refresh"}
    replay = replay_or_conflict(db, scope="sources.refresh", key=idempotency_key, payload=payload)
    if replay:
        return replay
    source = _get_or_404(db, Source, source_id)
    snapshot = refresh_official_source(db, get_settings(), source)
    response = SourceSnapshotOut.model_validate(snapshot).model_dump(mode="json")
    remember(db, scope="sources.refresh", key=idempotency_key, payload=payload, response_body=response)
    record_event(
        db,
        event_type="source.refreshed",
        entity_type="source_snapshot",
        entity_id=snapshot.id,
        actor_type="worker",
        actor_id="source-monitor",
        payload={"source_id": source.id, "hash": snapshot.content_hash, "status": snapshot.fetch_status},
    )
    return snapshot


@router.post("/sources/{source_id}/snapshots/manual", response_model=SourceSnapshotOut)
def manual_snapshot(
    source_id: str,
    payload: SnapshotManualCreate,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
    reviewer_id: ReviewerId,
) -> SourceSnapshot | dict:
    body = payload.model_dump(mode="json") | {"source_id": source_id}
    replay = replay_or_conflict(db, scope="sources.manual_snapshot", key=idempotency_key, payload=body)
    if replay:
        return replay
    source = _get_or_404(db, Source, source_id)
    snapshot = store_manual_snapshot(
        db,
        get_settings(),
        source=source,
        content=payload.content_text,
        confirmed_url=str(payload.confirmed_official_url),
        locator_note=payload.source_locator_note,
    )
    response = SourceSnapshotOut.model_validate(snapshot).model_dump(mode="json")
    remember(db, scope="sources.manual_snapshot", key=idempotency_key, payload=body, response_body=response)
    record_event(
        db,
        event_type="source.manual_snapshot_recorded",
        entity_type="source_snapshot",
        entity_id=snapshot.id,
        actor_type="human",
        actor_id=reviewer_id,
        payload={"source_id": source_id, "hash": snapshot.content_hash},
    )
    return snapshot


@router.get("/source-snapshots/latest", response_model=list[SourceSnapshotSummaryOut])
def list_latest_source_snapshots(db: DatabaseSession) -> list[SourceSnapshot]:
    snapshots = db.scalars(
        select(SourceSnapshot).order_by(
            SourceSnapshot.source_id,
            SourceSnapshot.retrieved_at.desc(),
            SourceSnapshot.created_at.desc(),
        )
    )
    latest: dict[str, SourceSnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.source_id, snapshot)
    return list(latest.values())


@router.get("/source-snapshots/{snapshot_id}", response_model=SourceSnapshotOut)
def get_snapshot(snapshot_id: str, db: DatabaseSession) -> SourceSnapshot:
    return _get_or_404(db, SourceSnapshot, snapshot_id)


@router.post(
    "/source-snapshots/{snapshot_id}/extract-verified-requirements",
    response_model=VerifiedExtractionOut,
)
def extract_verified_requirements(
    snapshot_id: str,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> dict:
    payload = {"snapshot_id": snapshot_id, "provider": "verified-fixture"}
    replay = replay_or_conflict(
        db, scope="requirements.extract_verified", key=idempotency_key, payload=payload
    )
    if replay:
        return replay
    snapshot = _get_or_404(db, SourceSnapshot, snapshot_id)
    if snapshot.fetch_status not in {"current", "manual_snapshot"}:
        raise HTTPException(
            status_code=409,
            detail="Verified extraction requires an authoritative current or manual snapshot",
        )
    source = _get_or_404(db, Source, snapshot.source_id)
    before_ids = set(
        db.scalars(
            select(RequirementCandidate.id).where(
                RequirementCandidate.source_snapshot_id == snapshot.id
            )
        )
    )
    candidates = create_fixture_candidates(
        db,
        get_settings(),
        snapshots_by_source_key={source.stable_key: snapshot},
    )
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="No reviewed public requirement fixture is registered for this source",
        )
    serialized = [RequirementOut.model_validate(item).model_dump(mode="json") for item in candidates]
    created = sum(item.id not in before_ids for item in candidates)
    response = {
        "snapshot_id": snapshot.id,
        "source_key": source.stable_key,
        "candidates": serialized,
        "created": created,
        "note": "Candidates remain unapproved and require Song review.",
    }
    remember(
        db,
        scope="requirements.extract_verified",
        key=idempotency_key,
        payload=payload,
        response_body=response,
    )
    for candidate in candidates:
        if candidate.id not in before_ids:
            record_event(
                db,
                event_type="requirement.candidate_created",
                entity_type="requirement",
                entity_id=candidate.id,
                actor_type="system",
                actor_id="verified-fixture-extractor",
                correlation_id=candidate.correlation_id,
                payload={
                    "status": candidate.status,
                    "source_snapshot_id": snapshot.id,
                    "validation": candidate.validation,
                },
            )
    return response


@router.post("/source-snapshots/{snapshot_id}/extract-requirement", response_model=RequirementOut)
def extract_requirement(
    snapshot_id: str,
    payload: RequirementExtractRequest,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> RequirementCandidate | dict:
    body = payload.model_dump(mode="json") | {"snapshot_id": snapshot_id}
    replay = replay_or_conflict(db, scope="requirements.extract", key=idempotency_key, payload=body)
    if replay:
        return replay
    if payload.provider != "ollama":
        raise HTTPException(
            status_code=422, detail="Fixture extraction is available only through demo bootstrap"
        )
    snapshot = _get_or_404(db, SourceSnapshot, snapshot_id)
    source = _get_or_404(db, Source, snapshot.source_id)
    candidate = extract_with_ollama(db, get_settings(), snapshot=snapshot, source=source)
    response = RequirementOut.model_validate(candidate).model_dump(mode="json")
    remember(db, scope="requirements.extract", key=idempotency_key, payload=body, response_body=response)
    record_event(
        db,
        event_type="requirement.candidate_created",
        entity_type="requirement",
        entity_id=candidate.id,
        actor_type="model",
        actor_id=candidate.model_version,
        correlation_id=candidate.correlation_id,
        payload={"status": candidate.status, "validation": candidate.validation},
    )
    return candidate


@router.get("/requirements", response_model=list[RequirementOut])
def list_requirements(
    db: DatabaseSession,
    status: Annotated[str | None, Query(max_length=40)] = None,
) -> list[RequirementCandidate]:
    statement = select(RequirementCandidate).order_by(RequirementCandidate.created_at.desc())
    if status:
        statement = statement.where(RequirementCandidate.status == status)
    return list(db.scalars(statement))


@router.get("/requirements/lineage", response_model=list[RequirementLineageOut])
def list_requirement_lineage(
    db: DatabaseSession,
    status: Annotated[str | None, Query(max_length=40)] = None,
) -> list[dict]:
    statement = select(RequirementCandidate).order_by(RequirementCandidate.created_at.desc())
    if status:
        statement = statement.where(RequirementCandidate.status == status)
    requirements = list(db.scalars(statement))
    if not requirements:
        return []

    snapshots = {
        item.id: item
        for item in db.scalars(
            select(SourceSnapshot).where(
                SourceSnapshot.id.in_([item.source_snapshot_id for item in requirements])
            )
        )
    }
    sources = {
        item.id: item
        for item in db.scalars(
            select(Source).where(
                Source.id.in_([snapshot.source_id for snapshot in snapshots.values()])
            )
        )
    }
    reviews_by_requirement: dict[str, list[RequirementReview]] = {}
    for review in db.scalars(
        select(RequirementReview)
        .where(RequirementReview.requirement_id.in_([item.id for item in requirements]))
        .order_by(RequirementReview.created_at)
    ):
        reviews_by_requirement.setdefault(review.requirement_id, []).append(review)

    result = []
    for requirement in requirements:
        snapshot = snapshots.get(requirement.source_snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=409, detail="Requirement source snapshot is missing")
        source = sources.get(snapshot.source_id)
        if source is None:
            raise HTTPException(status_code=409, detail="Requirement source is missing")
        approval_evidence = source_approval_evidence(db, snapshot)
        result.append(
            {
                "requirement": requirement,
                "snapshot": snapshot,
                "source": source,
                "reviews": reviews_by_requirement.get(requirement.id, []),
                "review_context": requirement_review_context(
                    snapshot.content_text, requirement.exact_quote
                ),
                **approval_evidence,
            }
        )
    return result


@router.post("/requirements/{requirement_id}/review", response_model=RequirementOut)
def requirement_review(
    requirement_id: str,
    payload: HumanReviewRequest,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
    reviewer_id: ReviewerId,
) -> RequirementCandidate | dict:
    body = payload.model_dump() | {"requirement_id": requirement_id, "reviewer_id": reviewer_id}
    replay = replay_or_conflict(db, scope="requirements.review", key=idempotency_key, payload=body)
    if replay:
        return replay
    requirement = _get_or_404(db, RequirementCandidate, requirement_id)
    requirement = review_requirement(
        db,
        requirement=requirement,
        disposition=payload.disposition,
        reviewer_id=reviewer_id,
        rationale=payload.rationale,
    )
    response = RequirementOut.model_validate(requirement).model_dump(mode="json")
    remember(db, scope="requirements.review", key=idempotency_key, payload=body, response_body=response)
    record_event(
        db,
        event_type="requirement.reviewed",
        entity_type="requirement",
        entity_id=requirement.id,
        actor_type="human",
        actor_id=reviewer_id,
        correlation_id=requirement.correlation_id,
        payload={"disposition": payload.disposition, "rationale": payload.rationale},
    )
    return requirement


@router.get("/controls", response_model=list[ControlOut])
def list_controls(db: DatabaseSession) -> list[Control]:
    return list(db.scalars(select(Control).order_by(Control.stable_key)))


@router.post("/controls", response_model=ControlOut, status_code=201)
def create_control(
    payload: ControlCreate, db: DatabaseSession, idempotency_key: IdempotencyKey
) -> Control | dict:
    body = payload.model_dump(mode="json")
    replay = replay_or_conflict(db, scope="controls.create", key=idempotency_key, payload=body)
    if replay:
        return replay
    if db.scalar(select(Control).where(Control.stable_key == payload.stable_key)):
        raise HTTPException(status_code=409, detail="Control stable_key already exists")
    control = Control(**payload.model_dump())
    db.add(control)
    db.commit()
    db.refresh(control)
    response = ControlOut.model_validate(control).model_dump(mode="json")
    remember(
        db,
        scope="controls.create",
        key=idempotency_key,
        payload=body,
        response_body=response,
        response_status=201,
    )
    return control


@router.post("/mappings", response_model=MappingOut, status_code=201)
def create_mapping(
    payload: MappingCreate, db: DatabaseSession, idempotency_key: IdempotencyKey
) -> RequirementControlMapping | dict:
    body = payload.model_dump(mode="json")
    replay = replay_or_conflict(db, scope="mappings.create", key=idempotency_key, payload=body)
    if replay:
        return replay
    requirement = _get_or_404(db, RequirementCandidate, payload.requirement_id)
    control = _get_or_404(db, Control, payload.control_id)
    mapping = create_mapping_candidate(
        db,
        requirement=requirement,
        control=control,
        rationale=payload.rationale,
        provider=payload.provider,
    )
    response = MappingOut.model_validate(mapping).model_dump(mode="json")
    remember(
        db,
        scope="mappings.create",
        key=idempotency_key,
        payload=body,
        response_body=response,
        response_status=201,
    )
    record_event(
        db,
        event_type="mapping.candidate_created",
        entity_type="mapping",
        entity_id=mapping.id,
        actor_type="human" if payload.provider == "human-authored" else "model",
        actor_id=payload.provider,
        correlation_id=mapping.correlation_id,
        payload={"requirement_id": requirement.id, "control_id": control.id},
    )
    return mapping


@router.get("/mappings", response_model=list[MappingOut])
def list_mappings(db: DatabaseSession) -> list[RequirementControlMapping]:
    return list(
        db.scalars(select(RequirementControlMapping).order_by(RequirementControlMapping.created_at.desc()))
    )


@router.get("/mappings/lineage", response_model=list[MappingLineageOut])
def list_mapping_lineage(db: DatabaseSession) -> list[dict]:
    mappings = list(
        db.scalars(
            select(RequirementControlMapping).order_by(
                RequirementControlMapping.created_at.desc()
            )
        )
    )
    if not mappings:
        return []
    requirements = {
        item.id: item
        for item in db.scalars(
            select(RequirementCandidate).where(
                RequirementCandidate.id.in_({item.requirement_id for item in mappings})
            )
        )
    }
    controls = {
        item.id: item
        for item in db.scalars(
            select(Control).where(Control.id.in_({item.control_id for item in mappings}))
        )
    }
    reviews_by_mapping: dict[str, list[MappingReview]] = {}
    for review in db.scalars(
        select(MappingReview)
        .where(MappingReview.mapping_id.in_([item.id for item in mappings]))
        .order_by(MappingReview.created_at)
    ):
        reviews_by_mapping.setdefault(review.mapping_id, []).append(review)
    result = []
    for mapping in mappings:
        requirement = requirements.get(mapping.requirement_id)
        control = controls.get(mapping.control_id)
        if requirement is None or control is None:
            raise HTTPException(status_code=409, detail="Mapping lineage is incomplete")
        result.append(
            {
                "mapping": mapping,
                "requirement": requirement,
                "control": control,
                "reviews": reviews_by_mapping.get(mapping.id, []),
            }
        )
    return result


@router.post("/mappings/{mapping_id}/review", response_model=MappingOut)
def mapping_review(
    mapping_id: str,
    payload: HumanReviewRequest,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
    reviewer_id: ReviewerId,
) -> RequirementControlMapping | dict:
    body = payload.model_dump() | {"mapping_id": mapping_id, "reviewer_id": reviewer_id}
    replay = replay_or_conflict(db, scope="mappings.review", key=idempotency_key, payload=body)
    if replay:
        return replay
    mapping = _get_or_404(db, RequirementControlMapping, mapping_id)
    mapping = review_mapping(
        db,
        mapping=mapping,
        disposition=payload.disposition,
        reviewer_id=reviewer_id,
        rationale=payload.rationale,
    )
    response = MappingOut.model_validate(mapping).model_dump(mode="json")
    remember(db, scope="mappings.review", key=idempotency_key, payload=body, response_body=response)
    record_event(
        db,
        event_type="mapping.reviewed",
        entity_type="mapping",
        entity_id=mapping.id,
        actor_type="human",
        actor_id=reviewer_id,
        correlation_id=mapping.correlation_id,
        payload={"disposition": payload.disposition, "rationale": payload.rationale},
    )
    return mapping


@router.post("/demo/load-media-cases")
def load_demo_media(db: DatabaseSession, idempotency_key: IdempotencyKey) -> dict:
    payload = {"dataset": "media-gold-2026-08-27.v1", "count": 50}
    replay = replay_or_conflict(db, scope="demo.load_media", key=idempotency_key, payload=payload)
    if replay:
        return replay
    cases = load_media_cases(db, get_settings())
    response = {"cases": len(cases), "dataset_version": payload["dataset"]}
    remember(db, scope="demo.load_media", key=idempotency_key, payload=payload, response_body=response)
    record_event(
        db,
        event_type="media.dataset_loaded",
        entity_type="dataset",
        entity_id=payload["dataset"],
        actor_type="human",
        actor_id="local-operator",
        payload=response,
    )
    return response


@router.get("/cases", response_model=list[MediaCaseOut])
def list_cases(db: DatabaseSession) -> list[MediaCase]:
    return list(db.scalars(select(MediaCase).order_by(MediaCase.stable_key)))


@router.post("/cases", response_model=MediaCaseOut, status_code=201)
def create_case(
    payload: MediaCaseCreate,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> MediaCase | dict:
    body = payload.model_dump(mode="json")
    replay = replay_or_conflict(db, scope="cases.create", key=idempotency_key, payload=body)
    if replay:
        return replay
    if db.scalar(select(MediaCase).where(MediaCase.stable_key == payload.stable_key)):
        raise HTTPException(status_code=409, detail="Media case stable_key already exists")
    case = MediaCase(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    response = MediaCaseOut.model_validate(case).model_dump(mode="json")
    remember(
        db,
        scope="cases.create",
        key=idempotency_key,
        payload=body,
        response_body=response,
        response_status=201,
    )
    return case


@router.post("/cases/{case_id}/analyze")
def analyze_case(
    case_id: str,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
    mode: Annotated[str, Query(pattern="^(async|sync)$")] = "async",
) -> dict:
    payload = {"case_id": case_id, "mode": mode, "pipeline": "media-evidence-v1"}
    replay = replay_or_conflict(db, scope="cases.analyze", key=idempotency_key, payload=payload)
    if replay:
        return replay
    case = _get_or_404(db, MediaCase, case_id)
    if mode == "async":
        task = analyze_media_case.delay(case.id)
        case.status = "queued"
        db.commit()
        response = {"status": "queued", "job_id": task.id, "case_id": case.id}
    else:
        evidence = extract_evidence(db, get_settings(), case)
        tests, findings = run_approved_controls(db, case)
        response = {
            "status": "analyzed",
            "case_id": case.id,
            "evidence_count": len(evidence),
            "test_count": len(tests),
            "finding_count": len(findings),
        }
    remember(db, scope="cases.analyze", key=idempotency_key, payload=payload, response_body=response)
    record_event(
        db,
        event_type="media.analysis_queued" if mode == "async" else "media.analysis_completed",
        entity_type="media_case",
        entity_id=case.id,
        actor_type="worker" if mode == "sync" else "human",
        actor_id="media-evidence-worker" if mode == "sync" else "local-operator",
        payload=response,
    )
    return response


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceOut])
def case_evidence(case_id: str, db: DatabaseSession) -> list[EvidenceItem]:
    _get_or_404(db, MediaCase, case_id)
    return list(
        db.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.case_id == case_id)
            .order_by(EvidenceItem.evidence_type, EvidenceItem.stable_key)
        )
    )


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    db: DatabaseSession,
    status: Annotated[str | None, Query(max_length=50)] = None,
) -> list[Finding]:
    statement = select(Finding).order_by(Finding.created_at.desc())
    if status:
        statement = statement.where(Finding.status == status)
    return list(db.scalars(statement))


@router.get("/findings/lineage", response_model=list[FindingLineageOut])
def list_finding_lineage(
    db: DatabaseSession,
    status: Annotated[str | None, Query(max_length=50)] = None,
) -> list[dict]:
    statement = select(Finding).order_by(Finding.created_at.desc())
    if status:
        statement = statement.where(Finding.status == status)
    findings = list(db.scalars(statement))
    if not findings:
        return []
    tests = {
        item.id: item
        for item in db.scalars(
            select(TestRun).where(TestRun.id.in_({item.test_run_id for item in findings}))
        )
    }
    requirements = {
        item.id: item
        for item in db.scalars(
            select(RequirementCandidate).where(
                RequirementCandidate.id.in_({item.requirement_id for item in findings})
            )
        )
    }
    controls = {
        item.id: item
        for item in db.scalars(
            select(Control).where(Control.id.in_({item.control_id for item in findings}))
        )
    }
    evidence_ids = {
        str(evidence_id)
        for finding in findings
        for evidence_id in finding.evidence_ids
    }
    evidence = (
        {
            item.id: item
            for item in db.scalars(
                select(EvidenceItem).where(EvidenceItem.id.in_(evidence_ids))
            )
        }
        if evidence_ids
        else {}
    )
    reviews_by_finding: dict[str, list[FindingReview]] = {}
    for review in db.scalars(
        select(FindingReview)
        .where(FindingReview.finding_id.in_([item.id for item in findings]))
        .order_by(FindingReview.created_at)
    ):
        reviews_by_finding.setdefault(review.finding_id, []).append(review)
    result = []
    for finding in findings:
        test_run = tests.get(finding.test_run_id)
        requirement = requirements.get(finding.requirement_id)
        control = controls.get(finding.control_id)
        if test_run is None or requirement is None or control is None:
            raise HTTPException(status_code=409, detail="Finding lineage is incomplete")
        result.append(
            {
                "finding": finding,
                "test_run": test_run,
                "requirement": requirement,
                "control": control,
                "evidence": [
                    evidence[str(evidence_id)]
                    for evidence_id in finding.evidence_ids
                    if str(evidence_id) in evidence
                ],
                "reviews": reviews_by_finding.get(finding.id, []),
            }
        )
    return result


@router.post("/findings/{finding_id}/review", response_model=FindingOut)
def finding_review(
    finding_id: str,
    payload: HumanReviewRequest,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
    reviewer_id: ReviewerId,
) -> Finding | dict:
    body = payload.model_dump() | {"finding_id": finding_id, "reviewer_id": reviewer_id}
    replay = replay_or_conflict(db, scope="findings.review", key=idempotency_key, payload=body)
    if replay:
        return replay
    finding = _get_or_404(db, Finding, finding_id)
    finding = review_finding(
        db,
        finding=finding,
        disposition=payload.disposition,
        reviewer_id=reviewer_id,
        rationale=payload.rationale,
    )
    response = FindingOut.model_validate(finding).model_dump(mode="json")
    remember(db, scope="findings.review", key=idempotency_key, payload=body, response_body=response)
    record_event(
        db,
        event_type="finding.reviewed",
        entity_type="finding",
        entity_id=finding.id,
        actor_type="human",
        actor_id=reviewer_id,
        correlation_id=finding.correlation_id,
        payload={"disposition": payload.disposition, "rationale": payload.rationale},
    )
    return finding


@router.post("/evaluations/run")
def run_evaluation(
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> dict:
    payload = {"dataset": "media-gold-2026-08-27.v1", "provider": get_settings().asr_provider}
    replay = replay_or_conflict(db, scope="evaluations.run", key=idempotency_key, payload=payload)
    if replay:
        return replay
    task = run_gold_evaluation_task.delay()
    response = {"status": "queued", "job_id": task.id, "dataset_version": payload["dataset"]}
    remember(db, scope="evaluations.run", key=idempotency_key, payload=payload, response_body=response)
    record_event(
        db,
        event_type="evaluation.queued",
        entity_type="dataset",
        entity_id=payload["dataset"],
        actor_type="human",
        actor_id="local-operator",
        payload=response,
    )
    return response


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: str, db: DatabaseSession) -> EvaluationRun:
    return _get_or_404(db, EvaluationRun, evaluation_id)


@router.get("/evaluations", response_model=list[EvaluationOut])
def list_evaluations(db: DatabaseSession) -> list[EvaluationRun]:
    return list(db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc())))


@router.post("/reports/{case_id}/export", response_model=list[ReportExportOut])
def create_report_export(
    case_id: str,
    payload: ReportExportRequest,
    db: DatabaseSession,
    idempotency_key: IdempotencyKey,
) -> list[ReportExport] | list[dict]:
    body = payload.model_dump(mode="json") | {"case_id": case_id}
    replay = replay_or_conflict(db, scope="reports.export", key=idempotency_key, payload=body)
    if replay:
        return replay
    case = _get_or_404(db, MediaCase, case_id)
    exports = export_report(db, get_settings(), case=case, formats=payload.formats)
    response = [ReportExportOut.model_validate(item).model_dump(mode="json") for item in exports]
    remember(db, scope="reports.export", key=idempotency_key, payload=body, response_body=response)
    record_event(
        db,
        event_type="report.exported",
        entity_type="media_case",
        entity_id=case.id,
        actor_type="human",
        actor_id="local-operator",
        correlation_id=exports[0].correlation_id,
        payload={"formats": payload.formats, "export_ids": [item.id for item in exports]},
    )
    return exports


@router.get("/reports", response_model=list[ReportExportOut])
def list_report_exports(db: DatabaseSession) -> list[ReportExport]:
    return list(db.scalars(select(ReportExport).order_by(ReportExport.created_at.desc())))


@router.get("/reports/{report_id}", response_model=ReportExportOut)
def get_report_export(report_id: str, db: DatabaseSession) -> ReportExport:
    return _get_or_404(db, ReportExport, report_id)
