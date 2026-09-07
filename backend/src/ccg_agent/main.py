from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .api import router as governance_router
from .database import get_db
from .models import AuditEvent
from .schemas import AuditEventOut, HealthResponse, ServiceState
from .settings import get_settings

DatabaseSession = Annotated[Session, Depends(get_db)]
PageLimit = Annotated[int, Query(ge=1, le=200)]

settings = get_settings()
app = FastAPI(
    title="Creator Commerce Governance Agent API",
    version=settings.app_version,
    description="Evidence-bound candidate, control, review, and audit orchestration. Not legal advice.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-Reviewer-Id"],
)
app.include_router(governance_router)


@app.get("/api/v1/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/api/v1/health", response_model=HealthResponse)
def readiness(db: DatabaseSession) -> HealthResponse:
    database_state = "ok"
    redis_state = "ok"
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_state = "unavailable"
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
    except Exception:
        redis_state = "unavailable"
    status = "healthy" if database_state == "ok" and redis_state == "ok" else "degraded"
    return HealthResponse(
        status=status,
        service="creator-commerce-governance-api",
        version=settings.app_version,
        environment=settings.app_env,
        dependencies=ServiceState(
            database=database_state,
            redis=redis_state,
            worker="configured",
            cloud_enabled=settings.allow_cloud,
        ),
    )


@app.get("/api/v1/audit-events", response_model=list[AuditEventOut])
def list_audit_events(
    db: DatabaseSession,
    limit: PageLimit = 50,
) -> list[AuditEvent]:
    statement = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    return list(db.scalars(statement))
