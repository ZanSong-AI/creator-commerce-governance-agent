# Evaluation

## Evaluation contract

The evaluation set contains 50 deterministic synthetic MP4 cases generated with seed `20260827`. It measures whether the implemented evidence pipeline behaves as expected on the repository fixtures. It does not estimate real-platform prevalence, creator behavior, legal risk, revenue, or enforcement impact.

The gold metadata declares commercial relationship, visual/audio disclosure expectation, language, platform flag, AIGC label expectation, C2PA fixture state, and intentional ambiguity. The evaluator never activates an operational control mapping and never changes approval state.

## Real local run

The first full run used FFmpeg, Tesseract, Faster-Whisper 1.2.1, and `c2pa-python` 0.37.7 over all 50 MP4 files. It completed every case without silent loss.

| Metric | First pass | Corrected evaluation |
|---|---:|---:|
| Cases with result | 50 / 50 | 50 / 50 |
| OCR precision | 0.8750 | 1.0000 |
| OCR recall | 1.0000 | 0.8571 |
| ASR precision | 1.0000 | 1.0000 |
| ASR recall | 0.8571 | 0.8571 |
| Provenance parse success | 1.0000 | 1.0000 |
| Candidate-finding precision | 0.9655 | 0.9355 |
| Candidate-finding recall | 0.9655 | 1.0000 |
| Abstention rate | 0.1000 | 0.1000 |
| Source freshness | initially misreported | 1.0000 current rerun |

The first pass took 85.35 seconds end-to-end. Case p50 was 1,280.24 ms and p95 was 4,115.12 ms. The corrected evaluator reused already verified evidence for all 50 unchanged asset hashes, so its speed is a cached-evidence validation number—not a media throughput benchmark.

## Provider-isolation regression

A later deterministic fixture run added fixture ASR evidence to the same media
hashes. The evaluator previously gathered every ASR row and selected the last
created row, which could make a future Faster-Whisper evaluation read a fixture
transcript. The evaluator now filters evidence by
`extractor == configured ASR provider` before prediction and records
`evidence_selector=extractor_matches_provider` in its metrics.

The post-fix Faster-Whisper regression completed 50/50 cases with zero failures
and retained the real `1.0000 / 0.8571` precision/recall plus the two Spanish ASR
misses. A separate fixture-provider run returned its own deterministic metrics.
The two evidence classes can coexist without changing one another's result.

## Local-model structured extraction

A 2026-08-28 no-persistence run used `song-local:latest` against the current TikTok commercial-content snapshot. The first full-page attempt timed out. A later full-page response violated the schema by returning an array for `required_action`, and Pydantic rejected it. The first bounded response was schema-valid but combined `GLOBAL_PLATFORM` with FTC guidance in the jurisdiction field, exposing an authority-separation validator gap.

After requiring exact source-jurisdiction equality and scanning every interpretation field, two anchor-assisted 4,000-character current-snapshot runs passed in 6.31 and 5.37 seconds. Their exact quote remained validated against the full 5,773-character immutable snapshot, while scope and uncertainty wording varied slightly. These results measure constrained interpretation of a reviewed passage, not autonomous discovery, deterministic semantics, approval, or production throughput. Full evidence and model digest are in [the local model report](../reports/LOCAL_MODEL_EXTRACTION_REPORT.md).

## Error analysis

The first OCR implementation searched for disclosure phrases as arbitrary substrings. Therefore `ad` could match inside unrelated words such as `generated`, causing two false positives. The production rule and evaluator now require Unicode word boundaries. This removed those false positives.

The stricter match reveals four genuine extraction misses:

- `case-020`, OCR: low-confidence Spanish `COLABORACION PAGADA` loses its initial characters;
- `case-030`, OCR: the same deliberately degraded Spanish text fails;
- `case-025`, ASR: Faster-Whisper mistranscribes the Spanish synthetic disclosure;
- `case-030`, ASR: Faster-Whisper mistranscribes the Spanish synthetic disclosure.

These misses are intentionally retained. They demonstrate why “not detected” is not the same as “not present” and why ambiguous evidence must route to human review.

Candidate-finding precision decreases after the bug fix because extraction misses can still produce a missing-evidence candidate where the gold case declares that a disclosure exists. This is the correct downstream consequence of imperfect OCR/ASR and is not hidden.

## Source freshness correction

The initial evaluator counted registry-loaded test fixtures as current sources. That was incorrect. Source state now distinguishes `registered`, `fixture_only`, `current`, `changed`, and `manual_snapshot_required`. Freshness counts both `current` and `changed` when either state is backed by a successful authoritative snapshot: `changed` means the new evidence differs from its predecessor, not that it is stale. After the EU/`c2pa-python` refresh the truthful rate was `6/9 = 0.6667`. The official eCFR Versioner API refresh moved Part 255 from manual to current, producing `7/9 = 0.7778`. The subsequent TikTok public FAQ API adapters produced authoritative snapshots for both remaining sources, so evaluation `80f1763e-c2bf-4d02-8941-3d544d0d8b84` reports `9/9 = 1.0000`. Historical evaluation records retain their earlier values.

## Hard-gate results

- Unapproved requirement cannot create a mapping: passed.
- Unapproved mapping cannot enter a rule run: passed.
- Model/worker review row rejected by PostgreSQL: passed.
- Source snapshot mutation rejected by PostgreSQL: passed.
- Exact quote validator on reviewable fixtures: 100%.
- 50 cases have a result or explicit abstention: passed.
- Missing C2PA does not create a legal conclusion: passed.
- Report HTML escapes untrusted caption content: passed.
- CI path does not require live sources, Ollama, or Whisper: passed by design; first hosted run pending publication.

## Scale stream

The deterministic generator produced 100,000 events with logical SHA-256 `c73895e21b86bf7ea57ef9e89899d5a26cc0d30c34347383ee8bb0cf9e48ceb7`. PostgreSQL stored exactly 100,000 rows and a total processing latency field of 46,882,618 ms. Re-ingestion inserted zero additional rows and control totals remained equal.

## Reproduction policy

CI evaluates schemas, rules, review boundaries, reports, UI, and fixed fixtures without live network or model calls. Real media dependencies are exercised locally and their actual measurements are recorded in [the public report](../reports/EVALUATION_REPORT.md). Any future model or extractor version creates a new evaluation record; historical results are not overwritten.
