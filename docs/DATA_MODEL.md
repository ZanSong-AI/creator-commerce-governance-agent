# Data Model

## Modeling principle

Do not place source claims, model interpretation, product controls, test observations, and human judgment in one mutable row. Each has a different grain, owner, and lifecycle.

## Audit grain

### `audit_events`

Grain: one state-relevant event by one actor against one entity.

| Field | Meaning |
|---|---|
| `id` | stable UUID string |
| `event_type` | namespaced action, such as `worker.heartbeat` |
| `entity_type` / `entity_id` | target entity pointer |
| `actor_type` / `actor_id` | human, model, worker, or system identity |
| `correlation_id` | groups a workflow across services |
| `payload` | non-secret structured context |
| `created_at` | UTC event time |

Audit events are append-only at the application layer. They do not replace domain tables; they explain how domain state changed.

## Implemented domain grains

- `sources`: one allowlisted publisher/URL identity.
- `source_snapshots`: one immutable retrieved representation of one source at one time.
- `requirement_candidates`: one source-backed interpretation of one exact passage.
- `requirement_reviews`: one human decision about one candidate/version.
- `controls`: one versioned deterministic product-control definition.
- `requirement_control_mappings`: one proposed or approved relationship between requirement and control versions.
- `mapping_reviews`: one human decision about one mapping candidate/version.
- `media_cases`: one synthetic promotional-content case plus declared relationship/platform metadata.
- `evidence_items`: one observation from caption, frame, transcript, platform metadata, or provenance inspection.
- `test_runs`: one control version evaluated against one case/evidence bundle.
- `findings`: one candidate issue from one test result.
- `finding_reviews`: one human disposition of one finding version.
- `report_exports`: one immutable local export manifest.
- `evaluation_runs`: one versioned execution over the fixed gold dataset.
- `idempotency_records`: one mutation scope/key and its request hash/result.
- `commerce_governance_events`: one synthetic event in the scale-test stream.

## Authorization relationships

```text
Source 1--N SourceSnapshot 1--N RequirementCandidate 1--N RequirementReview
RequirementCandidate N--N Control through RequirementControlMapping
MediaCase 1--N EvidenceItem
MediaCase + approved Mapping -> TestRun -> optional Finding -> FindingReview
MediaCase -> ReportExport(lineage manifest)
```

A test stores the exact `mapping_id`, `control_id`, `requirement_id`, `rule_version`, and `evidence_ids` used. A finding cannot exist without a test run. A report rebuilds the full upstream chain rather than copying a model narrative.

The requirement lineage response also computes a non-persisted review context from the immutable snapshot. Its grain is one bounded excerpt per requirement read: exact-quote match state, original line range, excerpt SHA-256, truncation flag, and plain-text excerpt. It is a review projection, not a new source-of-truth table; the snapshot hash remains authoritative.

PostgreSQL triggers reject review records whose `reviewer_type` is not `human`; reject requirement approval unless the parent snapshot is `current` or `manual_snapshot`, is the newest authoritative snapshot for that source, and the source is currently fresh; reject a requirement status transition without a matching human review row; and reject UPDATE or DELETE on `source_snapshots`. Check constraints require at least 20 trimmed characters for requirement, mapping, and finding review rationales and for mapping-candidate rationales. Application tests verify stale-snapshot, failed-refresh, fixture, bypass, and valid human paths against a migrated PostgreSQL database.

## State is versioned, not overwritten

When an official source changes, the old snapshot and approved requirement remain historical. A new snapshot creates a new candidate. Approval may supersede an old version but never erases it.

The same rule applies to mappings, controls, tests, findings, and report exports. A new reviewable interpretation is a new candidate rather than an edit to historical evidence.

## Redis is not a database

Redis carries Celery jobs and short-lived results. A Redis loss may require a retry; it must not lose an approval, source version, evidence item, review, or audit record.

Queue delivery is at-least-once for `media.analyze_case`, not exactly-once. Durable uniqueness is enforced at the business grains: evidence per case/stable extraction key, test run per case/mapping/rule version, and finding per test run. The local worker uses concurrency one; horizontal multi-worker media execution would require an additional case-scoped claim/lock before it is presented as supported.
