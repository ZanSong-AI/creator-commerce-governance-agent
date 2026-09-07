# 10-minute Interview Demo

## Read-only preflight

With the five local services running, execute:

```bash
make demo-rehearsal
```

The script makes GET requests only. It verifies the evidence-only demo profile:
9 fresh sources with the documented status distribution, 9 unapproved requirements,
0 mappings/findings, 50 analyzed media cases, the expected `case-003` and
`case-004` C2PA/evidence states, a provider-isolated Faster-Whisper evaluation,
and all four local case-004 report formats. A `ready` result is a rehearsal
precondition, not a legal, policy, publication, or production-readiness decision.

If a live local demo is unavailable, use the dated synthetic-only views in the
[Public Screenshot Inventory](SCREENSHOTS.md). State that they are capture-time
evidence and do not replace the read-only rehearsal or current source checks.

## 0:00–1:00 — Frame the problem

Open **Overview**. Explain that policy monitoring is not a legal chatbot: the product separates source authority, evidence, product controls, deterministic tests, and human decisions. Point to the non-negotiable boundary and the zero-external-action statement.

## 1:00–2:30 — Show source truthfulness

Open **Sources**. Compare the FTC eCFR lineage with either TikTok source. Explain that the system followed eCFR's official developer route and TikTok's own credential-free FAQ request instead of treating redirect shells, search snippets, or browser-only rendered text as snapshots. Show the canonical URL, actual retrieval URL, FAQ ID or eCFR as-of date, hash, and diff. Mention that full source text stays runtime-only.

## 2:30–4:00 — Review a requirement

Open **Requirements**. Read the exact quote, locator, actor, trigger, action, uncertainty, and model version side-by-side. Explain exact-quote validation and show that every item is still a candidate. Do not approve during a public demo unless Song has separately decided to create an operational local review record.

## 4:00–5:00 — Prove the double gate

Open **Controls**. With zero approved requirements, mapping creation is visibly blocked. Explain that an approved requirement would only unlock a mapping candidate; a second human review is needed before the deterministic rule engine can run.

## 5:00–7:00 — Inspect real media evidence

Open **Media Cases** and select `case-004`. Show the MP4 metadata, Faster-Whisper transcript, OCR frames, platform flag, relationship metadata, visible AIGC label state, and test-signed C2PA manifest. State explicitly that valid test-chain provenance is not proof of truth or legality.

Then select `case-003` to show invalid/tampered provenance and one low-confidence Spanish case to show why an extraction miss routes to review.

## 7:00–8:15 — Evaluation and failure story

Open **Evaluations**. Use the newest completed card whose ASR provider is
`faster-whisper` and whose evidence selector is `extractor_matches_provider`.
Explain the 50/50 completion, OCR/ASR precision and recall, and the word-boundary
bug. The strongest story is not perfect accuracy; it is that the first run
exposed a reproducible defect, the evaluator retained difficult cases, and the
report distinguishes real extraction latency from cached validation speed.
Fixture-provider cards are deterministic CI/regression evidence and must not be
presented as the real ASR benchmark.

## 8:15–9:15 — Audit package

Open **Audit Pack**, choose `case-004`, and generate all formats. Show `evidence_only_no_approved_rule_result`. Explain that this is the truthful package state until human-approved mappings create actual test lineage. Point to SHA-256 and the local-only path.

## 9:15–10:00 — Close with engineering relevance

Map the work to the job:

- AI backend: schemas, constrained model adapter, evals, evidence lineage;
- FDE: ambiguous customer workflow translated into staged controls and observable failure states;
- data engineering: immutable versions, event grain, idempotent 100k ingestion, control totals;
- governance/risk: authority separation, approval permissions, auditability, abstention;
- e-commerce platform: creator-brand relationships, product flags, multimodal disclosure, AIGC provenance.

Close with limitations: synthetic data, TikTok's unpublished article version numbers, nine unapproved requirement candidates, imperfect Spanish recognition, no external actions, and no claim of legal sufficiency.
