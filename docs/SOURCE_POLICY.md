# Source Policy

## Allowed sources

Only public, official, allowlisted sources are eligible for real source snapshots. Initial source families are:

- U.S. Federal Trade Commission guidance;
- TikTok public support/policy pages;
- EUR-Lex legal text;
- European Commission implementation guidance;
- C2PA specification and official Content Authenticity Initiative SDK documentation.

External commentary may inform research but cannot become a requirement source.

## Source types remain distinct

- `legal_text`
- `regulator_guidance`
- `platform_policy`
- `technical_standard`
- `official_sdk_documentation`

The product does not infer equal legal weight across types.

## Fetch modes

- `http`: bounded public HTTP retrieval after allowlist and network validation.
- `ecfr_api`: dated Part XML through the official eCFR Versioner API after resolving the current Title metadata date.
- `tiktok_faq_api`: one fixed TikTok Help Center FAQ ID through TikTok's credential-free public JSON endpoint, with response identity and completeness validation.
- `pdf`: bounded official PDF retrieval.
- `manual_snapshot`: Song supplies a public snapshot when automated access is unavailable or inappropriate.
- `metadata_only`: registry tracks URL/version but no text is ingested.

Robots, login, paywall, CAPTCHA, or access-control failure produces a blocked/manual state. It never authorizes a workaround.

## Current runtime status semantics

- `registered`: metadata exists but no authoritative snapshot has been retrieved;
- `fixture_only`: public test excerpts exist, but they are not a fresh official-page snapshot;
- `current`: an official HTTP or human-confirmed manual snapshot was recorded;
- `changed`: a newly retrieved authoritative representation differs from the previous authoritative version;
- `manual_snapshot_required`: safe automatic retrieval was blocked, redirected, dynamic, or incomplete;
- `fetch_error`: an ordinary eligible fetch failed and no new snapshot was created.

`last_checked_at` is updated by a real fetch attempt, not by loading a fixture. An unsuccessful attempt never relabels an old snapshot as current.

Approval authority follows the current source lineage, not the apparent plausibility of the excerpt. `public_test_fixture` supports deterministic extraction and CI but cannot authorize requirement approval. A successful `current` snapshot or human-confirmed `manual_snapshot` is eligible only while it remains the newest authoritative snapshot and the source's latest refresh state remains fresh (`current` or `changed`). The API and PostgreSQL both enforce this gate. A source change does not rewrite an older requirement, but it prevents that historical candidate from newly authorizing mapping work.

Registry metadata sync is a separate idempotent operation. If a source URL, version, jurisdiction, effective date, scope, or fetch mode changes, the source returns to `registered` and `last_checked_at` is cleared until a new authoritative snapshot is retrieved. Historical snapshots retain their original URL in immutable `locator_map` data. Registry sync never creates or approves a requirement.

## Verification history

### 2026-08-28

A same-day manual refresh rechecked all nine allowlisted sources. All requests succeeded without account state or redirect bypass. The resulting source rows are seven `current` and two `changed`; the two changed rows are FTC staff-guidance pages. Full immutable diffs show only FTC global navigation/footer links changed—no article-body line changed—so this is recorded as a presentation-shell change, not publisher-policy intent. The snapshots and hashes are retained because the monitor versions the retrieved representation; reviewers must inspect diffs rather than treating `changed` as a semantic label.

The refresh also prompted a stronger approval rule: a historically authoritative snapshot can no longer authorize a new requirement approval after a newer authoritative snapshot exists or while the source is in `fetch_error`, `manual_snapshot_required`, or another non-fresh state. Lineage now returns the latest authoritative snapshot ID and explicit source blockers. Migration `0007` enforces the same rule in PostgreSQL.

EUR-Lex now exposes a 2026-07-27 consolidated Regulation (EU) 2024/1689. The registry points to that version and records the Article 111(4) transition context separately from Article 50(2). On 2026-08-28 an explicit registry sync invalidated the older source's freshness, an authoritative refresh created a new immutable snapshot, and exact-quote validation created two unapproved candidates. Older snapshots and candidates remain historical; none were rewritten or approved.

The eCFR reader page explicitly directed automated clients to its developer API. The monitor now resolves Title 16's current `up_to_date_as_of` value from the official Versioner metadata endpoint and then fetches Part 255 from a dated official XML endpoint. The immutable snapshot records the canonical reader URL, exact API retrieval URL, as-of date, latest-amended metadata, title, part, content type, and hash. It produced one new unapproved FTC candidate; the earlier fixture-backed candidate remains historical and non-authoritative.

TikTok's two registered support URLs redirected to `www.tiktok.com/support/faq_detail` pages with stable FAQ IDs. Read-only browser inspection confirmed the rendered article text. Inspection of TikTok's own current frontend bundle identified its public `/feedback/1/faq_detail_by_id/` request, which was then reproduced without login, Cookie, token, or session state. This is first-party public web infrastructure observed in the current client, not a documented developer API, contractual schema, or availability promise. The internal locator enum `official_tiktok_public_faq_api` records first-party provenance; it must not be described as a supported TikTok developer integration. The adapter fixes the retrieval host and FAQ IDs in the registry; it validates response success, returned FAQ ID, exact article title, locale/country request, minimum body size, and a reviewed marker before storing anything. Any endpoint or schema drift fails closed and may return the source to a manual/error state. Locator metadata preserves the canonical support URL and the actual retrieval URL. HTML is converted to plain text, whitespace around inline links and punctuation is normalized, and the full snapshot remains runtime-only. Both sources now have authoritative immutable snapshots and new unapproved candidates. Because TikTok publishes no version number on either article, both retain `version: not_published`; hashes and diffs, not invented dates, represent change.

The first successful TikTok snapshots were immediately followed by a normalizer correction for punctuation split across inline links. Therefore the current source rows are `changed`, but that specific diff is a representation-pipeline revision, not evidence that TikTok changed policy between the two retrievals. Future locator metadata includes `normalizer_version=tiktok-faq-html-v1`; reviewers must inspect every diff rather than infer publisher intent from the status label.

### 2026-08-27

Fresh runtime snapshots were obtained from the FTC sources, both TikTok Help Center articles, EUR-Lex AI Act text, European Commission Article 50 guidance page, C2PA 2.4 specification, and the official `c2pa-python` repository. The eCFR and TikTok adapter improvements above supersede the earlier manual-source limitations while preserving those failures in audit history.

Official platform pages without a published version retain `version: not_published`. The project does not infer dates or version numbers from URL structure or page appearance.

## GitHub boundary

Full snapshots live under `.runtime/sources/` and are excluded from Git. The public repository stores source registry metadata and synthetic fixtures. Any attributed excerpt committed for demonstration must be minimal and pass release review.
