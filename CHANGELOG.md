# Changelog

All notable changes will be documented in this file.

## Unreleased

- Upgraded the GitHub secret-scan step from `gitleaks/gitleaks-action@v2` to the official Node 24-based `v3` release after verifying its no-behavior-change migration note.

### Added

- Five-service Docker Compose topology and complete v0.1 local workflow.
- FastAPI health endpoints and append-only audit-event model.
- Human-only API transitions plus PostgreSQL review, authoritative-snapshot approval, status-bypass, and immutability triggers.
- Nine-source official registry, immutable snapshots, hashes, diffs, and manual states.
- Official eCFR Versioner API retrieval that resolves the Title 16 as-of date and
  stores a dated Part 255 XML locator instead of bypassing reader-page controls.
- Official TikTok public FAQ retrieval for two registry-fixed Help Center IDs,
  with response identity, title, locale, completeness, hash, and diff validation.
- Local Ollama requirement extraction with Pydantic JSON-schema output,
  application-side type validation, exact source-jurisdiction binding, complete
  interpretation-language guards, and a no-persistence real-model verifier.
- Four-week implementation audit and a failure-retaining local-model extraction
  report with model digest, source snapshot identity, and measured runtime.
- Requirement lineage review with source authority, snapshot hash, validation, review history, and fixture-backed approval blocking across eight React pages.
- Bounded quote-adjacent review context with original line range, excerpt hash,
  whitespace-tolerant matching, truncation state, and escaped plain-text UI.
- Meaningful-rationale gates for mapping candidates and all three human review
  layers, enforced in React, Pydantic, PostgreSQL migration `0006`, and tests.
- Latest-authoritative-source approval gates across React, API, and PostgreSQL
  migration `0007`; superseded candidates and non-fresh source states expose
  explicit blockers and cannot authorize a new mapping.
- Python 3.11 runtime/dev/media constraints lock used by Docker and GitHub CI,
  plus `pip check` and lock-targeted vulnerability auditing; compatible frontend
  patches for Vite React plugin 6.1.1 and Testing Library React 16.3.3.
- Batched mapping/finding lineage APIs and UI review histories covering approved
  requirement, control, deterministic test, linked evidence, and disposition.
- Fifty real synthetic MP4 cases with FFmpeg, OCR, Faster-Whisper, and C2PA evidence.
- Production MP4 admission gates for project-root confinement, declared MIME,
  ISO BMFF signature, size, SHA-256, FFprobe duration/resolution/frame limits,
  plus a 50-fixture no-write verifier in deterministic CI.
- At-least-once media worker delivery with Celery late acknowledgement,
  worker-loss requeue, bounded RuntimeError backoff, single-job prefetch/local
  concurrency, task-attempt audit metadata, and duplicate business-record tests.
- Deterministic control runner gated by approved requirement and mapping records.
- 100,000-event reproducible ingestion stream with idempotent PostgreSQL loading.
- Real 50-case evaluation with error analysis and corrected word-boundary matching.
- Provider-isolated ASR evaluation selection so later CI fixtures cannot replace
  Faster-Whisper evidence for the same media asset.
- Read-only interview-demo rehearsal checker covering source state, approval
  gates, named media evidence, verified evaluation provenance, and report formats.
- Local HTML, PDF, JSON, and CSV audit-evidence packages with hashes and lineage.
- Pytest, Vitest, PostgreSQL boundary tests, Playwright desktop/mobile tests, and CI.

### Pending human gates

- Song review of the nine current requirement candidates and any later mappings.
- First successful GitHub-hosted CI run and `v0.1.0` release.
- Any scheduled source refresh.
