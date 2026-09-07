from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import IdempotencyRecord


def request_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def replay_or_conflict(
    session: Session,
    *,
    scope: str,
    key: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    record = session.scalar(
        select(IdempotencyRecord).where(IdempotencyRecord.scope == scope, IdempotencyRecord.key == key)
    )
    if record is None:
        return None
    if record.request_hash != request_digest(payload):
        raise HTTPException(
            status_code=409, detail="Idempotency key was already used for a different request"
        )
    return record.response_body


def remember(
    session: Session,
    *,
    scope: str,
    key: str,
    payload: dict[str, Any],
    response_body: dict[str, Any],
    response_status: int = 200,
) -> None:
    session.add(
        IdempotencyRecord(
            scope=scope,
            key=key,
            request_hash=request_digest(payload),
            response_status=response_status,
            response_body=response_body,
        )
    )
    session.commit()
