# API Guide

All business endpoints use `/api/v1`. Mutation endpoints require an `Idempotency-Key` of at least eight characters. Review endpoints additionally require `X-Reviewer-Id`; the API always writes `reviewer_type=human`, and PostgreSQL independently enforces that value. Requirement, mapping, and finding reviews require a trimmed rationale of at least 20 characters. The minimum is an anti-empty-record control, not proof that the judgment is correct.

## System and bootstrap

- `GET /health/live`: process liveness only.
- `GET /health`: PostgreSQL, Redis, worker configuration, and cloud flag.
- `GET /overview`: source states, queues, media count, evaluation state, recent audit events.
- `POST /demo/bootstrap`: register sources, short public fixtures, candidates, and controls; approves nothing.
- `POST /sources/sync-registry`: idempotently synchronize reviewed source metadata; invalidates freshness on material metadata drift but creates no snapshot, candidate, or approval.
- `GET /source-snapshots/latest`: return at most one newest immutable snapshot summary per source for the registry UI without N+1 requests.
- `GET /sources/{id}/snapshots`: list immutable snapshot summaries and diffs without returning full page text.
- `POST /source-snapshots/{id}/extract-verified-requirements`: validate reviewed fixture quotes against an authoritative snapshot and create unapproved candidates only.
- `POST /demo/load-media-cases`: load the 50-case metadata manifest idempotently.

## Sources and requirements

- `GET/POST /sources`
- `POST /sources/{id}/refresh`: use bounded HTML retrieval, the registered official eCFR metadata + dated Versioner XML adapter, or a registry-fixed TikTok public FAQ adapter. It never follows a bot challenge, uses account state, or trusts an unvalidated redirect shell.
- `POST /sources/{id}/snapshots/manual`
- `GET /source-snapshots/{id}`
- `POST /source-snapshots/{id}/extract-requirement`
- `GET /requirements`
- `GET /requirements/lineage`: batch requirement, source, immutable snapshot summary, authority gate, latest authoritative snapshot ID, source-approval blockers, bounded quote-adjacent source context, and review history for the review UI. Context is plain untrusted text with line numbers, excerpt hash, and truncation state; the endpoint does not send the full snapshot for each card.
- `POST /requirements/{id}/review`

Automated extraction supports the local Ollama adapter. Fixture extraction is only available through the deterministic demo bootstrap. A quote not found in its immutable snapshot, an interpretation containing guarded legal-conclusion language, a candidate whose parent is only `public_test_fixture`, a superseded authoritative snapshot, or a source whose latest refresh is not fresh cannot be approved. Such candidates may still be rejected or marked `needs_more_evidence`.

## Controls and mappings

- `GET/POST /controls`
- `GET/POST /mappings`
- `GET /mappings/lineage`: batch mapping, approved requirement, control definition, and human review history.
- `POST /mappings/{id}/review`

Mapping creation requires an already approved requirement and a meaningful candidate rationale. Rule execution requires both an approved requirement and an approved mapping.

## Media and findings

- `GET/POST /cases`
- `POST /cases/{id}/analyze?mode=async|sync`
- `GET /cases/{id}/evidence`
- `GET /findings`
- `GET /findings/lineage`: batch finding, triggering test, requirement, control, linked evidence, and human review history.
- `POST /findings/{id}/review`

`sync` is useful for local diagnosis. `async` is the product path. Evidence extraction can complete even when rule activation returns 409 because the evidence and authorization layers are intentionally separate.

## Evaluation, reports, and audit

- `POST /evaluations/run`
- `GET /evaluations`
- `GET /evaluations/{id}`
- `POST /reports/{case_id}/export`
- `GET /reports`
- `GET /reports/{id}`
- `GET /audit-events?limit=50`

Report export accepts `html`, `pdf`, `json`, and `csv`. It writes local files and a database record with content hash and lineage manifest. There is no download-to-third-party, email, platform, or regulator endpoint.

## Idempotency behavior

Reusing a key with the same normalized request returns the stored response. Reusing it in the same scope with a different request returns HTTP 409. This prevents duplicate snapshots, jobs, reviews, findings, and exports under ordinary retry behavior.

The OpenAPI UI at `/docs` is the authoritative executable schema for the current build.
