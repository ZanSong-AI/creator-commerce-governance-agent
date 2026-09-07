# ADR 0002: PostgreSQL is authoritative; Redis is transport

- Status: Accepted
- Date: 2026-08-24

## Context

Asynchronous source, media, model, and report work needs a queue, but approval and lineage cannot disappear if queue state is lost.

## Decision

PostgreSQL stores domain state, versions, reviews, and audit events. Redis carries Celery messages and ephemeral task results only.

## Consequences

- Tasks must be idempotent and reconstructable from PostgreSQL.
- A Redis outage degrades processing but does not erase business truth.
- Worker task IDs remain operational metadata rather than domain identifiers.
