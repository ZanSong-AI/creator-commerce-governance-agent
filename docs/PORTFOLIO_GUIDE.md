# Portfolio and Interview Guide

## Positioning

Lead with AI Backend / Forward Deployed Engineering. The differentiator is not “I used an LLM”; it is the end-to-end control plane around an uncertain model and changing external evidence.

Suggested resume bullet:

> Built a local-first creator-commerce governance system with FastAPI, React, PostgreSQL, Redis/Celery, Ollama, OCR/ASR, and C2PA; versioned official policy sources, enforced human-only approval boundaries, evaluated 50 synthetic MP4 cases, and idempotently processed 100k synthetic governance events with auditable lineage.

Suggested second bullet:

> Designed exact-quote, source-version, and deterministic control gates that prevent model self-approval and legal conclusions; achieved 100% quote validation and provenance parsing on the synthetic gold set while reporting retained Spanish OCR/ASR misses and source-access limitations.

## Role mapping

| Role | Evidence in this repository |
|---|---|
| AI Backend Engineer | typed APIs, Ollama JSON adapter, validation, jobs, evals, failure semantics |
| Forward Deployed Engineer | business workflow decomposition, human review UX, audit packages, staged rollout |
| TikTok Shop / E-commerce Governance | commercial relationships, platform disclosure flag, creator media evidence |
| Trust & Safety / Risk Engineering | candidate vs decision, abstention, evidence lineage, no external enforcement |
| Data Engineer | PostgreSQL grains, immutable versions, 100k deterministic stream, idempotency |
| Analytics Engineer | source freshness, review backlog, evaluation metrics, error breakdown |

## Claims that are safe

- “50 real synthetic MP4 files,” meaning actual playable generated files rather than 50 JSON rows;
- “real local Faster-Whisper/Tesseract/C2PA execution on synthetic media”;
- “100,000 deterministic synthetic events with verified control totals”;
- “human-only approval enforced at API and PostgreSQL layers”;
- “official-source metadata re-verified on 2026-08-28, with nine fresh authoritative
  source states, immutable hashes/diffs, and credential-free official adapters for eCFR and two TikTok Help Center FAQs.”

## Claims to avoid

- production deployment or production scale;
- real TikTok data or official TikTok affiliation;
- legal compliance detection;
- a real public-trust C2PA certificate;
- real business ROI, risk prevalence, revenue saved, or moderation impact;
- hosted GitHub CI success before the first public push actually runs.

## Likely interview questions

**Why not use one large prompt?** Because source identity, evidence existence, authorization, and product tests have different failure modes and must be independently reproducible.

**Why deterministic rules after an LLM?** The LLM structures candidate meaning; a versioned product control should give the same result for the same evidence bundle.

**Why PostgreSQL and Redis?** PostgreSQL owns durable business truth and constraints. Redis transports retryable work and can be replaced without losing approvals or evidence.

**What failed?** Source access, initial C2PA certificate construction, a stale Celery task registry, OCR substring matching, Spanish OCR/ASR, Alpine Playwright compatibility, and a test-isolation mistake. Each failure produced an explicit diagnosis and correction rather than a hidden success claim.

**How would you extend it?** Add a new rule pack with official source registry entries, gold cases, control taxonomy, human review, and separate evaluation. Minors protection remains roadmap-only because it would materially expand legal scope.
