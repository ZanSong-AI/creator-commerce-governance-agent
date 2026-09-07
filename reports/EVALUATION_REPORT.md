# 50-case evaluation report — 2026-08-27

Status: completed, 50/50 cases, zero processing failures.

This report records a real local run on synthetic fixtures. It is not a measurement of TikTok, creators, merchants, legal risk, platform prevalence, revenue, or ROI.

## Corrected metrics

- requirement schema-valid output rate: `1.0000`
- exact-quote validation rate: `1.0000`
- OCR precision / recall: `1.0000 / 0.8571` (`TP=12`, `FP=0`, `FN=2`)
- Faster-Whisper precision / recall: `1.0000 / 0.8571` (`TP=12`, `FP=0`, `FN=2`)
- provenance parsing success: `1.0000`
- candidate-finding precision / recall: `0.9355 / 1.0000`
- candidate-finding false-positive rate: `0.0645`
- abstention rate: `0.1000`
- source freshness: `1.0000` (`9/9` fresh runtime source states; latest rerun)
- approved requirements / mappings: `0 / 0`
- operational rule activation: `false`

The corrected run reused real evidence previously extracted for the same 50 asset hashes. Its cached latency and throughput are excluded from performance claims. The real extraction pass measured p50 `1,280.24 ms`, p95 `4,115.12 ms`, maximum `4,554.85 ms`, and `0.59 cases/second` end-to-end.

## 2026-08-28 source-freshness regression rerun

After synchronizing reviewed registry metadata and refreshing the consolidated EU and `c2pa-python` sources, the evaluation was rerun to verify source-status aggregation and governance backlog counts. This regression used the deterministic `fixture` ASR provider and cached evidence; it is not comparable to, and does not replace, the Faster-Whisper media benchmark above.

- status: completed with 50/50 cases and zero processing failures;
- source freshness: `0.6667` (`4 current + 2 changed + 3 manual_snapshot_required`);
- requirement backlog: `6` candidates, `0` approved;
- approved mappings: `0`;
- schema-valid requirement fixtures / exact-quote validation: `1.0000 / 1.0000`;
- operational rule activation: `false`.

The first regression task was consumed by a Celery worker that still held the previous evaluator code and therefore repeated the obsolete `0.4444` value. After restarting the worker and verifying its registered task set, a new evaluation record returned `0.6667`. The stale-worker run is retained as diagnostic history and is not presented as a valid corrected result.

## 2026-08-28 ASR provider-isolation regression

Evaluation record `93def3e2-49fd-4de9-aae3-2140a1607056` explicitly selected
evidence whose extractor matched `faster-whisper`, even though later fixture ASR
rows also existed for the same 50 media hashes. It completed 50/50 cases with
zero failures and reproduced ASR precision/recall `1.0000 / 0.8571`, including
the retained `case-025` and `case-030` misses. Metrics now record
`evidence_selector=extractor_matches_provider` so the provenance of each ASR
score is machine-visible.

## 2026-08-28 official eCFR API freshness rerun

Evaluation record `bbe98b81-b177-4139-83a0-0269b7c5ea3a` followed a successful official eCFR Versioner API refresh for Part 255. It reused all 50 immutable Faster-Whisper evidence bundles, completed with zero failures, retained OCR/ASR precision and recall `1.0000 / 0.8571`, and reported source freshness `0.7778` (`5 current + 2 changed + 2 manual_snapshot_required`). Requirement backlog is seven candidates; approved requirements, mappings, and operational rule activation remain zero.

## 2026-08-28 official TikTok FAQ API freshness rerun

Evaluation record `80f1763e-c2bf-4d02-8941-3d544d0d8b84` followed credential-free authoritative refreshes of the commercial-disclosure and AIGC TikTok Help Center articles. The monitor retained canonical support URLs while storing TikTok's public FAQ API retrieval URLs, fixed FAQ IDs, article identity checks, hashes, and diffs. This evaluation selected existing Faster-Whisper evidence by extractor, covered all 50 cases with zero processing failures, retained OCR/ASR precision and recall `1.0000 / 0.8571`, and reported source freshness `1.0000` (`5 current + 4 changed`). The two TikTok `changed` statuses include a same-session text-normalization correction and are not evidence of a publisher policy change. The requirement backlog is nine candidates: five authoritative and four historical fixture-backed candidates. Approved requirements, mappings, findings, and operational rule activation remain zero. Because all 50 media hashes already had verified Faster-Whisper evidence, the sub-millisecond cached validation latency is not a new media-throughput benchmark.

## Retained errors

| Case | Modality | Expected | Observed failure |
|---|---|---:|---|
| case-020 | OCR | disclosure present | degraded Spanish text lost initial characters |
| case-025 | ASR | disclosure present | synthetic Spanish phrase mistranscribed |
| case-030 | OCR | disclosure present | degraded Spanish text lost initial characters |
| case-030 | ASR | disclosure present | synthetic Spanish phrase mistranscribed |

The initial evaluator also found two OCR false positives caused by matching `ad` as a substring. The implementation now uses word boundaries. Both the original result and correction are preserved in the development log.

## Operational interpretation

The project is engineering-complete locally but intentionally not authorized for operational findings. Song must first approve each requirement candidate, create and approve its control mapping, and then run the deterministic control against evidence. A report generated before those approvals is labeled `evidence_only_no_approved_rule_result`.
