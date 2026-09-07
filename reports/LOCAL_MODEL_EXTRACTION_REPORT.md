# Local Ollama Structured-Extraction Report

Run date: 2026-08-28
Runtime: local Ollama `0.32.0` on the Mac host
Model: `song-local:latest`
Model digest: `537ba19b64712ce02edf7b25f457746e772f65df9fe95fdcbaa89fa227685ae3`
Cloud routing: disabled

## Result

Two final no-persistence dry runs passed the strict `requirement-extraction-v1` schema and deterministic evidence guards. Neither created a requirement candidate, review, mapping, finding, report export, or external action.

| Check | Result |
|---|---:|
| Pydantic schema valid | pass |
| Exact quote present in full immutable snapshot | pass |
| Snapshot hash checked | pass |
| Quote legal-language guard | pass |
| Interpretation legal-language guard | pass |
| Model jurisdiction exactly matches source metadata | pass |
| Database writes | 0 |
| Human approvals | 0 |
| External actions | 0 |

## Evidence identity

- source: TikTok `tiktok-commercial-content-disclosure`;
- source type: `platform_policy_help`, not law;
- source row state: `changed`; this does not by itself prove publisher policy change;
- immutable snapshot ID: `95e1af51-02f7-4641-b139-706d12a78934`;
- snapshot fetch status: `current`;
- snapshot SHA-256: `065d922d7a6947d8f3f6a0414cfb693188b54ff4bdd060cec5570728384fefe7`;
- full snapshot length: 5,773 characters;
- model input: a 4,000-character bounded window centered on a reviewed public exact-quote anchor that was revalidated against the current snapshot;
- autonomous requirement discovery: false for this run.

The bounded run tests structured interpretation of a known source passage. It must not be presented as autonomous discovery across an unseen policy corpus.

## Candidate preview

The model copied this exact quote:

> When posting content that promotes a brand, product, or service on TikTok, you must turn on the content disclosure setting.

It returned:

- actor: user posting content promoting a brand, product, or service;
- trigger: posting that promotional content on TikTok;
- required action: turn on the content disclosure setting;
- jurisdiction: `GLOBAL_PLATFORM`;
- effective date: `null`;
- confidence: `1.0`;
- uncertainties: UI steps vary by posting route and TikTok One participation; the reproduction also mentioned possible post restriction described in the source.

This is a model candidate preview, not Song's interpretation, an approved requirement, a statement of FTC sufficiency, or a legal conclusion.

The exact quote, actor, trigger, action, jurisdiction, and null effective date were stable across the two passing runs. Scope wording and uncertainties varied slightly even with temperature 0. Deterministic validators bound evidence and authority, but they do not make model interpretation bit-for-bit deterministic; human review remains necessary.

## Measured local runtime

| Metric | First passing run | Reproduction via `make verify-local-model` |
|---|---:|---:|
| Total duration | 6,306.473 ms | 5,371.352 ms |
| Load duration | 41.031 ms | 42.417 ms |
| Prompt evaluation | 1,263.850 ms / 1,662 tokens | 99.477 ms / 1,662 tokens |
| Generation | 4,945.809 ms / 214 tokens | 5,215.396 ms / 226 tokens |

These are two warm-model runs, not a throughput, capacity, or production SLA benchmark.

## Failures retained during implementation

1. The first host-Python command failed before inference because the system interpreter did not contain project dependencies. The supported command now runs inside the API container.
2. A full-snapshot run exceeded the original response wait and failed with `ReadTimeout`; it was not counted as success.
3. With thinking disabled and generation bounded, the full-snapshot model response returned `required_action` as an array even though the schema requires a string. Pydantic rejected it with `ValidationError`.
4. The first bounded response was schema-valid but wrote `GLOBAL_PLATFORM including FTC guidance` in the jurisdiction field. That exposed an authority-conflation gap in the validator.
5. The prompt and deterministic validator now require exact equality with the source jurisdiction and scan actor, trigger, action, exception, jurisdiction, scope, and uncertainties for prohibited legal conclusions. The final bounded rerun passed those controls.

These failures matter more than a polished one-shot demo: Ollama's schema request improves generation reliability, but application-side Pydantic and evidence validators remain authoritative.

## Reproduce

With Docker Compose and host Ollama running:

```bash
make verify-local-model
```

The command reads current local source state and prints JSON to stdout. It has no persistence path. CI continues to use deterministic mocks and never calls Ollama or live policy sites.

Ollama's official documentation recommends passing a JSON schema in `format` and validating the response with Pydantic. The implementation follows that pattern while retaining separate evidence guards: [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs).
