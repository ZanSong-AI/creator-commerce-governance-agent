# Threat Model

## Assets

- source identity and version history;
- exact source quotes and requirement lineage;
- human review decisions;
- synthetic media and generated test truth;
- model/rule versions and evaluation results;
- audit events and report manifests;
- local model and runtime configuration.

## Untrusted inputs

- public webpages and PDFs;
- manually supplied snapshots;
- captions, audio, frame text, EXIF and C2PA fields;
- model output;
- filenames, MIME declarations and archive contents;
- browser requests.

## Primary threats and controls

### Prompt injection

Threat: a source or media asset says to ignore policy, approve itself, use cloud, or take an action.

Controls:

- untrusted content is delimited as data;
- tool permissions do not include approval or external action;
- deterministic state guard rejects non-human approvals;
- model output is schema and exact-quote validated;
- all transitions emit audit events.

### SSRF and source substitution

Threat: a source URL points to private networks, redirects to an untrusted host, or silently changes publisher.

Controls:

- allowlist credential-free HTTPS hosts from the reviewed registry;
- reject userinfo and any host absent from that registry;
- disable redirects instead of following a challenge or substituted host;
- preserve canonical and exact retrieval URLs plus fetch metadata in snapshot lineage;
- use eCFR's first-party metadata and dated Versioner endpoints without automating its reader challenge;
- require human approval to register or change a source.

### Malicious media

Threat: oversized files, decompression bombs, malformed codecs, path traversal, or crafted C2PA data.

Implemented controls:

- declared MIME, extension, and ISO BMFF `ftyp` signature validation;
- project-root path confinement plus SHA-256 identity validation;
- file-size, FFprobe duration, resolution, video-frame-count, and subprocess time limits;
- isolated worker process and non-root container;
- runtime-only storage under generated IDs;
- no use of user filename as filesystem path;
- bounded OCR/ASR/C2PA timeouts;
- explicit unreadable/unsupported states;
- all 50 public MP4 fixtures pass the production admission gates in local and deterministic CI verification.

### XSS and report injection

Threat: caption or OCR text injects executable markup into UI or report.

Controls:

- React escapes displayed strings;
- requirement review receives only a bounded plain-text context excerpt, with no raw HTML rendering;
- report templates escape by default;
- no raw HTML from sources or model output;
- tests include script-like content.

### Secret or private-data publication

Threat: runtime snapshots, credentials, personal paths, private-workspace material, model caches, or real-user media enter Git.

Controls:

- separate repository;
- strict `.gitignore` and `.dockerignore`;
- synthetic-only fixture inventory;
- fixture-backed requirement approval attempts are blocked in the UI, API, and PostgreSQL;
- secret/path/email scans;
- public-release checklist and Song review;
- no automatic GitHub publication.

### Authority confusion

Threat: platform policy or regulator guidance is presented as statute, or a technical provenance result is presented as authenticity.

Controls:

- typed source authority;
- source-backed UI labels;
- banned legal-conclusion language;
- C2PA result shown as technical validation state only;
- report limitations generated alongside findings.

### Ceremonial human review

Threat: a UI presents one-click approval with a generic rationale, so a `human`
actor label exists without evidence that the reviewer considered the source,
control, test, or uncertainty.

Controls:

- no canned review rationale in requirement, mapping, or finding disposition UI;
- at least 20 trimmed rationale characters enforced by UI, API, and PostgreSQL;
- mapping and finding batch lineage includes the reviewed parents, evidence, and
  review history;
- the minimum length is documented as an anti-empty control, not proof of review
  quality or legal judgment.
