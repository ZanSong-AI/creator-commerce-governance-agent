from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ccg_agent.audit import record_event
from ccg_agent.database import Base
from ccg_agent.models import AuditEvent


def test_audit_event_preserves_actor_lineage() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        event = record_event(
            session,
            event_type="requirement.candidate_created",
            entity_type="requirement",
            entity_id="req-demo",
            actor_type="model",
            actor_id="deterministic-mock",
            correlation_id="11111111-1111-1111-1111-111111111111",
            payload={"status": "candidate", "external_actions": "none"},
        )
        stored = session.scalar(select(AuditEvent).where(AuditEvent.id == event.id))
        assert stored is not None
        assert stored.actor_type == "model"
        assert stored.payload["status"] == "candidate"
        assert stored.correlation_id == "11111111-1111-1111-1111-111111111111"
