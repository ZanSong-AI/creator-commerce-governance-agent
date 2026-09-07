# Evidence-only interview demo rehearsal — 2026-08-28

Status: `ready` for the documented local evidence-only profile.

This report records a read-only rehearsal against the running local application.
It is not a legal, policy, production, publication, or hosted-CI approval.

## Command

```bash
make demo-rehearsal
```

The checker uses only GET endpoints, including the batched requirement, mapping,
and finding lineage views. It does not create reviews, mappings,
findings, evaluations, reports, source snapshots, schedules, cloud calls, or
external actions.

## Verified state

| Check | Result |
|---|---:|
| API health | healthy |
| Cloud enabled | false |
| Demo profile | evidence_only_source_refresh_v2 |
| Source states | 7 current / 2 changed (9/9 fresh) |
| Source refresh window | 8.98 seconds across all nine sources |
| Changed-source identity | FTC Disclosures 101 / FTC Endorsement FAQ; inspected diffs are navigation/footer only |
| Requirements | 9 candidates |
| Approval authority | 5 latest-authoritative / 4 explicitly blocked historical fixtures |
| Mappings / findings | 0 / 0 |
| Analyzed media cases | 50 / 50 |
| Named evidence cases | case-003 invalid C2PA / case-004 test-signed valid chain |
| Verified evaluation | `80f1763e-c2bf-4d02-8941-3d544d0d8b84` |
| ASR provider / selector | faster-whisper / extractor_matches_provider |
| OCR recall / ASR recall | 0.8571 / 0.8571 |
| case-004 report formats | HTML / PDF / JSON / CSV |
| Report package state | evidence_only_no_approved_rule_result |

## Visual and responsive QA

The Evaluations page was inspected in the local browser after the summary-card
update. The newest provider-isolated run visibly shows 50/50 results, OCR and ASR
precision/recall, source freshness, provider, evidence selector, zero failures,
and `operational rules=false`; fixture runs use a separate label. Full metrics
and retained errors remain available in a collapsed audit section.

Playwright passed three workflow/responsive assertions with one intentional
desktop skip for the mobile-only overflow assertion.

## Important transition note

This checker intentionally describes the current evidence-only release
candidate. After Song creates an explicit requirement or mapping review, its
zero-approval assertions should fail rather than silently relabel a changed
governance state as the same demo profile. A later approved-workflow demo must
use a new named profile and preserve this report as historical evidence.

The v2 profile additionally requires all nine sources to have been checked in
one bounded refresh window, fixes the identity of the two representation-level
`changed` sources, verifies that every approval-eligible candidate points to its
source's latest authoritative snapshot with zero blockers, and verifies that
every ineligible candidate exposes at least one blocker. It does not infer that
the FTC changed policy from navigation/footer diffs.
