# Open-source design benchmark

Verified: 2026-08-28 against the current official default branches
Purpose: explain which public engineering patterns influenced this portfolio and which were deliberately not adopted.

This project does not treat repository popularity as proof that a design is correct. A reference is useful only when its official repository or documentation is available, its maintenance and license are visible, its pattern fits this product's authority boundary, and the resulting choice can be tested locally.

No source code from the projects below was copied into this repository. `c2pa-python` is the only item below used as a runtime dependency; it remains under its upstream Apache-2.0/MIT licenses. The other projects are architectural references.

The verification used the official GitHub repositories and pinned search results where available: OPA commit `8e733384254aa0211f0464852f2881f83d700bf1`, ComplianceAsCode commit `2e61ce1e2e9c0492348c212749b75bc2c52eafdd`, and `c2pa-python` commit `cf3f5fb6c78da3e1ea508df288668a5b8328d0fa`. NIST's official OSCAL repository README was checked directly. These commits document what was reviewed; they are not new runtime dependencies or claims that the projects endorse this portfolio.

## Comparison

| Public project | Relevant upstream pattern | What this project adopts | What this project does not claim or adopt |
|---|---|---|---|
| [Open Policy Agent](https://github.com/open-policy-agent/opa) | Separate policy/rules and input data; produce an explicit policy decision; support decision logging | Versioned deterministic controls consume evidence-shaped input and produce a `TestRun`; audit events preserve the decision path | OPA/Rego is not currently embedded. Nine small controls do not justify a sixth runtime service, and a test failure is still only a finding candidate—not enforcement |
| [NIST OSCAL](https://github.com/usnistgov/OSCAL) | Structured JSON/YAML/XML models for publishing, implementing, and assessing controls | Stable IDs, explicit control definitions, evidence/observation records, assessment results, links, timestamps, versions, and separate human disposition | The audit package is OSCAL-inspired, not OSCAL-conformant. Creator-commerce policy is not silently represented as NIST SP 800-53, and no authorization package claim is made |
| [ComplianceAsCode/content](https://github.com/ComplianceAsCode/content) | Author rule metadata once, preserve identifiers/rationale/applicability, and generate several test/output forms | Public requirement fixtures provide one source of reviewed quote metadata; controls keep stable keys, versions, evidence kinds, and applicability boundaries; exports share one lineage manifest | No Bash/Ansible remediation is generated. This product has no run-mode enforcement, takedown, penalty, or external modification path |
| [c2pa-python](https://github.com/contentauth/c2pa-python) | Official bindings read/validate manifests and can create/sign test assets | The media worker uses the official SDK for present/absent/invalid/test-signed evidence and records SDK/asset provenance | A valid manifest is not truth, authenticity, legality, or disclosure sufficiency; an absent manifest is not deception |

## Pattern 1: OPA-style separation without premature OPA deployment

OPA's core architecture separates data supplied by an application from rules evaluated by the policy engine and returns a decision to the caller. This project keeps the same conceptual separation:

```text
approved requirement + approved mapping + control version
                         ↓
evidence bundle ──> deterministic control function ──> TestRun
                                                        ↓
                                             finding candidate only
```

The current implementation intentionally keeps deterministic functions inside the FastAPI/Celery codebase because:

- there are nine small controls;
- each control has a narrow evidence type;
- Python unit tests already provide deterministic replay;
- adding OPA would add deployment and policy-language complexity without removing the need for Song's approval gates.

Reconsider OPA when rule packs become independently deployed, multiple services need the same decisions, or policy authors need a declarative review workflow. Even then, OPA would return a product decision such as `issue_candidate`; it would not receive authority to declare legality or enforce externally.

## Pattern 2: OSCAL-inspired lineage

OSCAL separates control publication, implementation description, assessment planning, assessment results, and follow-up. The domain here is different, but the separation helps prevent one row from becoming both policy text and assessment conclusion.

| This project | OSCAL-inspired role |
|---|---|
| `SourceSnapshot` + `RequirementCandidate` | addressable source/control statement context |
| `Control` + approved `RequirementControlMapping` | versioned implementation/control definition |
| `MediaCase` + planned tests | assessment subject and assessment plan input |
| `EvidenceItem` | observation/evidence |
| `TestRun` | executed assessment activity/result |
| `Finding` | reviewable result that still needs human disposition |
| `ReportExport.lineage_manifest` | portable assessment-result-style package |

The mapping is conceptual, not a schema certification. A future optional export may implement a formally validated OSCAL assessment-results profile, but only if an actual consumer needs interoperability. Adding OSCAL-shaped field names without schema validation would be résumé theater.

## Pattern 3: ComplianceAsCode-style single-source rule metadata

ComplianceAsCode demonstrates the value of keeping title, description, rationale, identifiers, applicability, checks, and generated outputs connected. This project applies that idea at a smaller governance grain:

- a reviewed fixture keeps the source key, locator, exact quote, actor, trigger, action, exception, jurisdiction, date, scope, and proposed controls together;
- exact quote validation runs against an authoritative immutable snapshot;
- `Control.stable_key` and `rule_version` separate logical identity from implementation revision;
- HTML, PDF, JSON, and CSV reports render from the same lineage manifest;
- applicability uncertainty routes to `human_review_required` rather than a guessed platform check.

The crucial difference is enforcement. ComplianceAsCode can generate remediations. Creator Commerce Governance Agent cannot change platform or creator state, so it borrows content organization but rejects remediation/run-mode behavior.

## Pattern 4: C2PA as provenance evidence

The official SDK boundary is kept narrow:

1. validate file type, path, size, and asset hash;
2. call the SDK reader;
3. normalize manifest presence and validation state;
4. store the raw status with SDK and asset versions;
5. let an approved product control reference that evidence;
6. keep truth, intent, applicability, and legal interpretation outside the SDK result.

Test signing uses runtime-generated test-only certificates. Keys and trust material stay outside Git.

## Public-project adoption checklist

Before introducing another public project, record:

1. official repository and documentation URL;
2. retrieved date and current release/maintenance evidence;
3. license and whether code, dependency, or only an idea is used;
4. exact problem it solves in this architecture;
5. new service, data, security, and operational costs;
6. failure semantics and human-approval impact;
7. deterministic tests proving the integration;
8. what the integration must not be used to claim.

This prevents “uses many open-source tools” from replacing a defensible product design.
