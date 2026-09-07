from __future__ import annotations

from celery import Celery

from .audit import record_event
from .database import SessionLocal
from .models import MediaCase
from .services.evaluation import run_gold_evaluation
from .services.media import extract_evidence, run_approved_controls
from .settings import get_settings

settings = get_settings()
celery_app = Celery(
    "creator-commerce-governance",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    # Media analysis is CPU-heavy and may be redelivered after a worker loss.
    # Keep only one reserved job per worker process; task-level late-ack options
    # below are enabled only for the idempotent media path.
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="system.record_worker_heartbeat")
def record_worker_heartbeat(correlation_id: str) -> dict[str, str]:
    with SessionLocal() as session:
        event = record_event(
            session,
            event_type="worker.heartbeat",
            entity_type="system",
            entity_id="worker",
            actor_type="worker",
            actor_id="celery",
            correlation_id=correlation_id,
            payload={"external_actions": "none", "cloud_used": False},
        )
    return {"status": "recorded", "audit_event_id": event.id}


@celery_app.task(
    bind=True,
    name="media.analyze_case",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    max_retries=2,
    acks_late=True,
    reject_on_worker_lost=True,
)
def analyze_media_case(task, case_id: str) -> dict[str, int | str]:
    with SessionLocal() as session:
        case = session.get(MediaCase, case_id)
        if case is None:
            return {"status": "not_found", "case_id": case_id}
        evidence = extract_evidence(session, settings, case)
        tests, findings = run_approved_controls(session, case)
        record_event(
            session,
            event_type="media.analysis_completed",
            entity_type="media_case",
            entity_id=case.id,
            actor_type="worker",
            actor_id="celery-media-worker",
            correlation_id=task.request.id,
            payload={
                "task_id": task.request.id,
                "retry_count": task.request.retries,
                "redelivered": bool((task.request.delivery_info or {}).get("redelivered")),
                "evidence_count": len(evidence),
                "test_count": len(tests),
                "finding_count": len(findings),
            },
        )
        return {
            "status": "analyzed",
            "case_id": case.id,
            "evidence_count": len(evidence),
            "test_count": len(tests),
            "finding_count": len(findings),
        }


@celery_app.task(name="evaluation.run_gold")
def run_gold_evaluation_task() -> dict[str, str]:
    with SessionLocal() as session:
        evaluation = run_gold_evaluation(session, settings)
        record_event(
            session,
            event_type="evaluation.completed",
            entity_type="evaluation",
            entity_id=evaluation.id,
            actor_type="worker",
            actor_id="celery-evaluation-worker",
            correlation_id=evaluation.correlation_id,
            payload={"status": evaluation.status, "metrics": evaluation.metrics},
        )
        return {"status": evaluation.status, "evaluation_id": evaluation.id}
