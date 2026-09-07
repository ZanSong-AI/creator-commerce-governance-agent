# Public Release Checklist

This checklist must be completed by Song before making the repository public.

## Data and privacy

- [x] No keys, tokens, cookies, sessions, certificates, or `.env` files.
- [x] No personal paths, email addresses, account identifiers, or private notes.
- [x] No real creator, merchant, user, post, or platform data.
- [x] No private workspace, employer, course, or community material.
- [x] All published media and events are synthetic and reproducible.

## Claims and boundaries

- [x] README says the project is independent and not affiliated with TikTok.
- [x] README says outputs are not legal advice or legal conclusions.
- [x] Platform policy, regulatory guidance, and law remain distinct source types.
- [x] Benchmarks are copied from a real reproducible run without cherry-picking.
- [x] Limitations and failure categories are visible.

## Engineering and licensing

- [x] Backend, frontend, migration, integration, and E2E checks pass.
- [x] Both distinct Dockerfiles build from the public tree with digest-verified
  official-equivalent base images and pass image-internal smoke checks.
- [x] Secret scan and dependency/license checks pass.
- [x] Docker and CI install Python runtime/dev/media dependencies through the
  resolved Python 3.11 constraints lock, run `pip check`, and audit that lock;
  the pnpm lock passes its supply-chain policy and production vulnerability scan.
- [x] Documentation links and commands have been tested.
- [x] Third-party notices and the MIT license are complete.
- [x] Generated reports contain complete lineage and escaped untrusted content.
- [x] Public screenshots use only official-source metadata and synthetic demo
  data; file format, visible content, and OCR privacy checks pass.
- [x] Local Ollama structured extraction has a reproducible no-write command;
  timeout, schema-drift, authority-conflation, and final pass are disclosed.
- [x] All 50 synthetic MP4 files pass the same path, MIME, magic-byte, size,
  hash, duration, resolution, and frame-count gates used by the worker.
- [x] Media late-ack/retry settings, one transient eager retry, repeat-run
  TestRun/Finding reuse, and the live single-worker prefetch/concurrency values
  are verified; horizontal same-case concurrency remains an explicit limit.
- [x] Requirement approval is blocked for fixture, superseded, or non-fresh
  source evidence in UI, API, and PostgreSQL migration `0007`.

## Human release gate

- [x] Song reviewed and approved the public-safe project scope and GitHub publication.
- [x] Song approved repository creation and public visibility on 2026-09-06.
- [x] The corrected hosted GitHub Actions release gate passes after the approved initial push.
- [x] `v0.1.0` release notes state actual scope and known limitations.
- [x] Scheduled source monitoring remains disabled.
- [ ] A separate human approval exists before enabling any weekly schedule.
