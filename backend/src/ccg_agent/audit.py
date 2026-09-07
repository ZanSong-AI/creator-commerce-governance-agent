from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import AuditEvent


def record_event(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_type: str,
    actor_id: str,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload or {},
    )
    if correlation_id:
        event.correlation_id = correlation_id
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
