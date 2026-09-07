# v0.1.0 — Local Release Candidate

`v0.1.0` is the first complete local release candidate of Creator Commerce
Governance Agent. It demonstrates an evidence-bound governance workflow for
commercial disclosure and AI-generated promotional content using only public
official sources and synthetic product data.

## Included

- nine-source official registry with immutable runtime snapshots, hashes, diffs,
  freshness states, and manual-snapshot handling;
- local-model requirement candidates with exact-quote and legal-language guards;
- human-only requirement, mapping, and finding transitions backed by PostgreSQL
  triggers, including rejection of fixture-only approval and direct status bypass;
- typed non-template rationale for all three review layers, with mapping/finding
  evidence lineage and matching UI, API, and PostgreSQL minimum-content gates;
- bounded source-context excerpts with line numbers and hashes for requirement review;
- 50 real synthetic MP4 cases with FFmpeg, Tesseract, Faster-Whisper, platform
  metadata, and C2PA evidence;
- deterministic controls that cannot run until both the requirement and mapping
  have separate human approval;
- 100,000 deterministic governance events with idempotent PostgreSQL ingestion;
- eight-page React review UI and versioned FastAPI endpoints;
- real 50-case evaluation, error analysis, audit events, and local HTML, PDF,
  JSON, and CSV evidence packages;
- offline CI paths for backend, frontend, migrations, PostgreSQL boundaries,
  Docker builds, Playwright, secret scanning, dependency audits, and licenses.
- at-least-once media delivery with late acknowledgement, bounded retry,
  worker-loss requeue, and PostgreSQL business-record idempotency; evaluation
  reruns remain explicit new provenance records.

## Measured local results

- 50 of 50 media cases produced a result or explicit abstention;
- OCR disclosure precision/recall: 1.0000 / 0.8571;
- ASR disclosure precision/recall: 1.0000 / 0.8571;
- C2PA parsing success: 1.0000;
- candidate-finding precision/recall on the gold fixture: 0.9355 / 1.0000;
- 100,000 events loaded once; identical re-ingestion inserted zero rows;
- backend: 64 tests passed (plus one retained upstream Starlette/httpx warning);
- frontend component tests: 5 passed;
- Playwright: 3 passed, 1 intentional desktop skip for a mobile-only assertion.

## Known limitations

- all media, users, brands, merchants, campaigns, and business events are
  synthetic;
- the system does not estimate real TikTok risk, prevalence, revenue, or ROI;
- TikTok does not publish version numbers for the two registered Help Center
  articles; credential-free official FAQ API snapshots therefore retain
  `version: not_published` and use immutable hashes/diffs. eCFR is retrieved
  through its official dated Versioner XML API;
- two difficult Spanish OCR cases and two difficult Spanish ASR cases remain
  misses and are reported rather than removed;
- C2PA test signatures establish only test-chain verification, not truth,
  authenticity, legality, or public trust;
- operational requirements and mappings remain unapproved until Song reviews
  them; consequently the public demo begins with no active rule findings;
- four historical requirements are backed only by deterministic public fixtures
  and cannot be approved; five current candidates have authoritative EU/eCFR/
  TikTok snapshot lineage but still require Song's substantive review;
- the local reviewer header is a development adapter, not production identity
  or access management;
- media retry/redelivery is verified for the single-worker local topology;
  horizontal concurrent processing of the same case still requires a
  case-scoped claim/lock and is not presented as supported;
- both distinct Dockerfiles rebuild successfully through the normal local
  Compose/BuildKit path. The backend image installs through the Python 3.11
  constraints lock and passes `pip check`; the web image installs through the
  frozen pnpm lock. Hosted CI is a separate release gate and must be checked after the initial push;
- no external submission, platform action, enforcement action, cloud-model call,
  or scheduled source monitor exists in this release.

## Publication gate

This file is a release draft, not evidence that a GitHub release exists. Public
repository creation and the initial push were approved on 2026-09-06; the tag
still requires a separate review of the repository, screenshots, wording, Git
history, and hosted CI result.
Scheduled source monitoring remains disabled and requires a separate later
approval.
