import { useCallback, useEffect, useState } from "react";
import type { JSX } from "react";

import { api } from "./api";
import type {
  AuditEvent,
  Control,
  Evaluation,
  Evidence,
  FindingLineage,
  HealthResponse,
  MappingLineage,
  MediaCase,
  Overview,
  ReportExport,
  Requirement,
  RequirementLineage,
  Source,
  SourceSnapshotSummary,
} from "./types";

const navItems = [
  "Overview",
  "Sources",
  "Requirements",
  "Controls",
  "Media Cases",
  "Review Queue",
  "Evaluations",
  "Audit Pack",
] as const;
type Page = (typeof navItems)[number];

function StatusPill({ value }: { value: string }) {
  const normal = ["ok", "healthy", "current", "approved", "completed", "analyzed"].includes(value);
  return <span className={`status status-${normal ? "normal" : "attention"}`}>{value}</span>;
}

function BoundaryCard() {
  return (
    <section className="boundary-card" aria-labelledby="boundary-heading">
      <p className="eyebrow">Non-negotiable boundary</p>
      <h2 id="boundary-heading">Evidence and candidates, never legal conclusions</h2>
      <p>
        Models and workers may propose requirements, mappings, and findings. Only Song may approve or
        disposition them. No takedowns, regulator submissions, reports to platforms, or enforcement actions
        exist in this product.
      </p>
    </section>
  );
}

function PageHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <header className="page-heading">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>{text}</p>
    </header>
  );
}

function ErrorNotice({ message }: { message: string | null }) {
  return message ? <p className="error-notice">{message}</p> : null;
}

interface ReviewAction {
  disposition: string;
  label: string;
  secondary?: boolean;
  disabled?: boolean;
  title?: string;
}

function HumanDecisionBox({
  label,
  placeholder,
  actions,
  onReview,
}: {
  label: string;
  placeholder: string;
  actions: ReviewAction[];
  onReview: (disposition: string, rationale: string) => Promise<void>;
}) {
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const meaningful = rationale.trim().length >= 20;
  async function submit(disposition: string) {
    if (!meaningful) return setError("Write at least 20 non-whitespace characters explaining the evidence and judgment.");
    setSubmitting(true);
    setError(null);
    try {
      await onReview(disposition, rationale.trim());
      setRationale("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Review failed");
    } finally {
      setSubmitting(false);
    }
  }
  return <div className="review-box"><label>{label}<textarea value={rationale} maxLength={4000} onChange={(event) => setRationale(event.target.value)} placeholder={placeholder} /></label><p className="review-count">{rationale.trim().length} / 20 minimum meaningful characters</p><div className="actions">{actions.map((action) => <button key={action.disposition} className={action.secondary ? "secondary" : undefined} disabled={submitting || !meaningful || action.disabled} title={action.title} onClick={() => void submit(action.disposition)}>{action.label}</button>)}</div><ErrorNotice message={error} /></div>;
}

function objectValue(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function rate(value: unknown): string {
  return typeof value === "number" ? value.toFixed(4) : "—";
}

function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([api.health(), api.overview()])
      .then(([healthValue, overviewValue]) => {
        setHealth(healthValue);
        setOverview(overviewValue);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unknown API error"));
  }, []);
  const metrics = [
    ["Registered sources", Object.values(overview?.source_freshness ?? {}).reduce((a, b) => a + b, 0)],
    ["Review backlog", overview?.review_backlog ?? "—"],
    ["Synthetic media cases", overview?.media_cases ?? "—"],
    ["Latest evaluation", overview?.evaluation_status ?? "not_run"],
  ];
  return (
    <>
      <div className="hero-row">
        <PageHeading
          eyebrow="Evidence-bound operating view"
          title="Governance work that can be traced"
          text="Every result keeps its source, version, model or rule version, evidence IDs, review state, and audit correlation ID."
        />
        <StatusPill value={health?.status ?? (error ? "offline" : "loading")} />
      </div>
      <BoundaryCard />
      <ErrorNotice message={error} />
      <section className="metric-grid" aria-label="Governance metrics">
        {metrics.map(([label, value]) => (
          <article className="metric-card" key={label}>
            <p>{label}</p>
            <strong>{String(value)}</strong>
          </article>
        ))}
      </section>
      <EventPanel events={overview?.recent_audit_events ?? []} />
    </>
  );
}

function EventPanel({ events }: { events: AuditEvent[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div><p className="eyebrow">Immutable operating trace</p><h2>Recent audit events</h2></div>
        <span>{events.length} shown</span>
      </div>
      {events.length === 0 ? <p className="empty-state">No audit events returned.</p> : (
        <ul className="event-list">
          {events.map((event) => (
            <li key={event.id}>
              <div><strong>{event.event_type}</strong><span>{event.actor_type} · {event.actor_id}</span></div>
              <time>{new Date(event.created_at).toLocaleString()}</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SourcesPage() {
  const [items, setItems] = useState<Source[]>([]);
  const [snapshots, setSnapshots] = useState<Record<string, SourceSnapshotSummary[]>>({});
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(
    () =>
      Promise.all([api.sources(), api.latestSourceSnapshots()])
        .then(([sources, latestSnapshots]) => {
          setItems(sources);
          setSnapshots(
            Object.fromEntries(latestSnapshots.map((snapshot) => [snapshot.source_id, [snapshot]])),
          );
        })
        .catch((e: Error) => setMessage(e.message)),
    [],
  );
  useEffect(() => { void load(); }, [load]);
  async function syncRegistry() {
    setMessage("Synchronizing approved registry metadata…");
    try {
      const result = await api.syncRegistry();
      setMessage(
        `Registry ${result.registry_version}: ${result.updated} updated, ` +
        `${result.freshness_invalidated} freshness state(s) invalidated. No requirements were created or approved.`,
      );
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Registry sync failed");
    }
  }
  async function refresh(item: Source) {
    setMessage(`Checking ${item.title}…`);
    try {
      await api.refreshSource(item.id);
      setMessage("A new immutable snapshot was recorded. Review the returned source state before use.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Refresh failed");
    }
  }
  async function extractVerified(snapshot: SourceSnapshotSummary) {
    setMessage("Validating reviewed exact quotes against the authoritative snapshot…");
    try {
      const result = await api.extractVerifiedRequirements(snapshot.id);
      setMessage(
        `${result.created} new requirement candidate(s) created from ${result.source_key}. ` +
        "Every candidate remains unapproved.",
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Verified extraction failed");
    }
  }
  const fixtureSources = new Set([
    "us-ftc-endorsement-guides-16-cfr-255",
    "tiktok-commercial-content-disclosure",
    "tiktok-aigc-labeling",
    "eu-ai-act-article-50",
  ]);
  return (
    <>
      <PageHeading eyebrow="Allowlisted primary sources" title="Source registry" text="Only official publishers enter the registry. A blocked or manual source is never presented as freshly fetched." />
      <ErrorNotice message={message} />
      <section className="panel"><div className="record-title"><div><h2>Registry metadata</h2><p>Sync the reviewed public JSON registry without creating candidates or reusing an old snapshot as current.</p></div><button onClick={() => void syncRegistry()}>Sync registry metadata</button></div></section>
      <section className="card-list">
        {items.map((item) => {
          const latest = snapshots[item.id]?.[0];
          const canExtract = latest && ["current", "manual_snapshot"].includes(latest.fetch_status) && fixtureSources.has(item.stable_key);
          return <article className="record-card" key={item.id}>
            <div className="record-title"><div><p>{item.publisher} · {item.jurisdiction}</p><h2>{item.title}</h2></div><StatusPill value={item.status} /></div>
            <dl className="detail-grid"><dt>Type</dt><dd>{item.source_type}</dd><dt>Version</dt><dd>{item.version}</dd><dt>Effective</dt><dd>{item.effective_date ?? "not published"}</dd><dt>Fetch mode</dt><dd>{item.fetch_mode}</dd></dl>
            <p className="muted">{item.applicable_scope}</p>
            {latest && <div className="compact-record"><strong>Latest immutable snapshot · {latest.content_hash.slice(0, 12)}</strong><span>{new Date(latest.retrieved_at).toLocaleString()} · {latest.fetch_status}</span><p>Diff: {String(latest.diff_summary.kind ?? "unknown")} · +{String(latest.diff_summary.added_lines ?? 0)} / -{String(latest.diff_summary.removed_lines ?? 0)}</p>{Boolean(latest.locator_map.retrieval_mode) && <p>Retrieval: {String(latest.locator_map.retrieval_mode)}{latest.locator_map.up_to_date_as_of ? ` · as of ${String(latest.locator_map.up_to_date_as_of)}` : ""}{latest.locator_map.faq_id ? ` · FAQ ${String(latest.locator_map.faq_id)} · ${String(latest.locator_map.locale ?? "unknown")}-${String(latest.locator_map.country ?? "unknown")}` : ""}</p>}{Boolean(latest.locator_map.article_title) && <p>Verified article identity: {String(latest.locator_map.article_title)}</p>}</div>}
            <div className="actions"><a href={item.official_url} target="_blank" rel="noreferrer">Open official source</a><button onClick={() => void refresh(item)}>Refresh snapshot</button>{canExtract && <button className="secondary" onClick={() => void extractVerified(latest)}>Create verified candidates</button>}</div>
          </article>;
        })}
      </section>
    </>
  );
}

function RequirementCard({ lineage, onChanged }: { lineage: RequirementLineage; onChanged: () => void }) {
  const { requirement: item, source, snapshot, reviews, review_context: context, authoritative_for_approval: authoritative, source_approval_blockers: sourceBlockers } = lineage;
  return (
    <article className="record-card">
      <div className="record-title"><div><p>{item.jurisdiction} · {item.source_locator}</p><h2>Requirement candidate</h2></div><StatusPill value={item.status} /></div>
      <div className="compact-record">
        <div className="record-title"><strong>{source.publisher} · {source.source_type}</strong><StatusPill value={snapshot.fetch_status} /></div>
        <a href={source.official_url} target="_blank" rel="noreferrer">Open official source</a>
        <dl className="detail-grid"><dt>Source version</dt><dd>{source.version}</dd><dt>Retrieved</dt><dd>{new Date(snapshot.retrieved_at).toLocaleString()}</dd><dt>Snapshot as-of</dt><dd>{String(snapshot.locator_map.up_to_date_as_of ?? "not published")}</dd><dt>Retrieval mode</dt><dd>{String(snapshot.locator_map.retrieval_mode ?? "bounded page fetch")}</dd><dt>Retrieval identity</dt><dd>{snapshot.locator_map.faq_id ? `FAQ ${String(snapshot.locator_map.faq_id)} · ${String(snapshot.locator_map.locale ?? "unknown")}-${String(snapshot.locator_map.country ?? "unknown")}` : "canonical URL + snapshot hash"}</dd><dt>Snapshot SHA-256</dt><dd className="mono">{snapshot.content_hash}</dd><dt>Exact quote</dt><dd>{String(item.validation.exact_quote_present ?? false)}</dd></dl>
      </div>
      {!authoritative && <p className="error-notice">Source authorization is blocked: {sourceBlockers.join("; ")}. Song may reject it or request more evidence.</p>}
      <blockquote>{item.exact_quote}</blockquote>
      {context.exact_quote_found ? <div className="compact-record"><strong>Bounded snapshot context · untrusted source text</strong><span>Lines {context.start_line}–{context.end_line} · excerpt SHA-256 {context.excerpt_sha256}{context.truncated ? " · bounded/truncated" : ""}</span><pre>{context.excerpt}</pre></div> : <p className="error-notice">The exact quote could not be located in the parent snapshot. Approval must remain blocked.</p>}
      <dl className="detail-grid"><dt>Actor</dt><dd>{item.actor}</dd><dt>Trigger</dt><dd>{item.trigger}</dd><dt>Required action</dt><dd>{item.required_action}</dd><dt>Exception</dt><dd>{item.exception ?? "none recorded"}</dd><dt>Scope</dt><dd>{item.scope}</dd><dt>Effective date</dt><dd>{item.effective_date ?? "not recorded"}</dd><dt>Model</dt><dd>{item.model_provider} / {item.model_version}</dd></dl>
      <p className="muted">Uncertainty: {item.uncertainties.length ? JSON.stringify(item.uncertainties) : "none recorded"}</p>
      {reviews.length > 0 && <div className="compact-record"><strong>Human review history</strong>{reviews.map((entry) => <p key={entry.id}>{entry.disposition} · {entry.reviewer_id} · {new Date(entry.created_at).toLocaleString()}<br />{entry.rationale}</p>)}</div>}
      {item.status === "candidate" && <HumanDecisionBox label="Song's review rationale" placeholder="What source, context, scope, exception, and uncertainty did you verify?" actions={[{ disposition: "approved", label: "Approve candidate", disabled: !authoritative || !context.exact_quote_found, title: authoritative && context.exact_quote_found ? "Approve this narrow interpretation for mapping work" : "Authoritative snapshot with verified quote context required" }, { disposition: "needs_more_evidence", label: "Needs evidence", secondary: true }, { disposition: "rejected", label: "Reject", secondary: true }]} onReview={async (disposition, rationale) => { await api.reviewRequirement(item.id, disposition, rationale, "Song"); onChanged(); }} />}
    </article>
  );
}

function RequirementsPage() {
  const [items, setItems] = useState<RequirementLineage[]>([]);
  const load = useCallback(() => api.requirementLineage().then(setItems), []);
  useEffect(() => { void load(); }, [load]);
  return <><PageHeading eyebrow="Quote-bound extraction" title="Requirement candidates" text="Compare official source authority, immutable snapshot, exact quote, scope, interpretation, uncertainty, and prior review. Approval authorizes mapping work—not a legal conclusion." /><section className="card-list">{items.map((item) => <RequirementCard key={item.requirement.id} lineage={item} onChanged={() => void load()} />)}</section></>;
}

function ControlsPage() {
  const [controls, setControls] = useState<Control[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [mappings, setMappings] = useState<MappingLineage[]>([]);
  const [requirementId, setRequirementId] = useState("");
  const [controlId, setControlId] = useState("");
  const [rationale, setRationale] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(
    () =>
      Promise.all([api.controls(), api.requirements(), api.mappingLineage()]).then(([c, r, m]) => {
        setControls(c);
        setRequirements(r);
        setMappings(m);
      }),
    [],
  );
  useEffect(() => { void load(); }, [load]);
  async function create() {
    try { await api.createMapping(requirementId, controlId, rationale); setMessage("Mapping candidate created; it still needs Song's approval."); await load(); }
    catch (e) { setMessage(e instanceof Error ? e.message : "Mapping failed"); }
  }
  const approved = requirements.filter((item) => item.status === "approved");
  return (
    <>
      <PageHeading eyebrow="Deterministic enforcement boundary" title="Controls and mappings" text="A control only runs when both its parent requirement and its mapping have separate human approval." />
      <ErrorNotice message={message} />
      <section className="panel"><h2>Create a mapping candidate</h2>{approved.length === 0 ? <p className="empty-state">No approved requirement exists yet. Mapping creation is intentionally blocked.</p> : <div className="form-row"><select aria-label="Approved requirement" value={requirementId} onChange={(e) => setRequirementId(e.target.value)}><option value="">Approved requirement…</option>{approved.map((item) => <option key={item.id} value={item.id}>{item.actor} · {item.jurisdiction}</option>)}</select><select aria-label="Control" value={controlId} onChange={(e) => setControlId(e.target.value)}><option value="">Control…</option>{controls.map((item) => <option key={item.id} value={item.id}>{item.stable_key}</option>)}</select><input aria-label="Mapping rationale" value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Explain why this requirement maps to this deterministic test" /><button disabled={!requirementId || !controlId || rationale.trim().length < 20} onClick={() => void create()}>Create candidate</button></div>}</section>
      <section className="split-grid"><div className="panel"><h2>Control catalog</h2>{controls.map((item) => <div className="compact-record" key={item.id}><strong>{item.stable_key}</strong><span>{item.evidence_kind} · {item.rule_version}</span><p>{item.description}</p></div>)}</div><div className="panel"><h2>Mapping reviews</h2>{mappings.length === 0 ? <p className="empty-state">No mappings yet.</p> : mappings.map(({ mapping, requirement, control, reviews }) => <div className="compact-record" key={mapping.id}><div className="record-title"><strong>{control.stable_key}</strong><StatusPill value={mapping.status} /></div><p>{mapping.rationale}</p><blockquote>{requirement.exact_quote}</blockquote><span>{control.evidence_kind} · {control.rule_version}</span>{reviews.length > 0 && <div className="compact-record"><strong>Human review history</strong>{reviews.map((review) => <p key={review.id}>{review.disposition} · {review.reviewer_id} · {new Date(review.created_at).toLocaleString()}<br />{review.rationale}</p>)}</div>}{mapping.status === "candidate" && <HumanDecisionBox label="Song's mapping-review rationale" placeholder="Which approved requirement fields, control definition, evidence type, and test behavior did you verify?" actions={[{ disposition: "approved", label: "Approve mapping" }, { disposition: "rejected", label: "Reject", secondary: true }]} onReview={async (disposition, reviewRationale) => { await api.reviewMapping(mapping.id, disposition, reviewRationale, "Song"); await load(); }} />}</div>)}</div></section>
    </>
  );
}

function MediaCasesPage() {
  const [cases, setCases] = useState<MediaCase[]>([]);
  const [selected, setSelected] = useState<MediaCase | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(() => api.cases().then(setCases), []);
  useEffect(() => { void load(); }, [load]);
  async function inspect(item: MediaCase) { setSelected(item); setEvidence(await api.evidence(item.id)); }
  async function analyze(item: MediaCase) { try { const result = await api.analyzeCase(item.id); setMessage(`Analysis queued: ${JSON.stringify(result)}`); } catch (e) { setMessage(e instanceof Error ? e.message : "Analysis failed"); } }
  return (
    <><PageHeading eyebrow="Real synthetic MP4 pipeline" title="Media cases" text="Inspect caption, frames, speech transcript, platform metadata, and C2PA state without using real creators or posts." /><ErrorNotice message={message} /><section className="case-grid"><div className="panel case-list">{cases.map((item) => <button className={selected?.id === item.id ? "case-button selected" : "case-button"} key={item.id} onClick={() => void inspect(item)}><strong>{item.stable_key}</strong><span>{item.jurisdiction} · {item.relationship_type}</span><StatusPill value={item.status} /></button>)}</div><div className="panel">{selected ? <><div className="record-title"><div><p>{selected.caption}</p><h2>{selected.stable_key}</h2></div><button onClick={() => void analyze(selected)}>Analyze again</button></div><dl className="detail-grid"><dt>Platform flag</dt><dd>{String(selected.platform_disclosure_flag)}</dd><dt>Visible AIGC label</dt><dd>{String(selected.visible_aigc_label)}</dd><dt>Asset hash</dt><dd className="mono">{selected.asset_sha256}</dd></dl><h3>Evidence bundle</h3>{evidence.map((item) => <div className="compact-record" key={item.id}><strong>{item.evidence_type} · {item.stable_key}</strong><span>{item.extractor} {item.extractor_version}</span><pre>{JSON.stringify(item.observed_value, null, 2)}</pre></div>)}</> : <p className="empty-state">Select a case to inspect evidence.</p>}</div></section></>
  );
}

function ReviewQueuePage() {
  const [items, setItems] = useState<FindingLineage[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(
    () => api.findingLineage().then(setItems).catch((reason: unknown) => {
      setMessage(reason instanceof Error ? reason.message : "Finding lineage failed to load");
    }),
    [],
  );
  useEffect(() => { void load(); }, [load]);
  return <><PageHeading eyebrow="Human disposition only" title="Finding review queue" text="A candidate represents a deterministic control-test result, not a statement that content or a company broke the law." /><ErrorNotice message={message} /><section className="card-list">{items.length === 0 ? <p className="empty-state">No findings exist because no mapping has human approval. This is the expected safe state.</p> : items.map(({ finding, test_run: testRun, requirement, control, evidence, reviews }) => <article className="record-card" key={finding.id}><div className="record-title"><div><p>{control.stable_key} · {testRun.rule_version}</p><h2>{finding.title}</h2></div><StatusPill value={finding.status} /></div><p>{finding.explanation}</p><p className="muted">Uncertainty: {finding.uncertainty}</p><blockquote>{requirement.exact_quote}</blockquote><dl className="detail-grid"><dt>Test status</dt><dd>{testRun.status}</dd><dt>Evidence items</dt><dd>{evidence.length}</dd><dt>Test result</dt><dd className="mono">{JSON.stringify(testRun.result)}</dd><dt>Evidence IDs</dt><dd className="mono">{finding.evidence_ids.join(", ")}</dd></dl>{reviews.length > 0 && <div className="compact-record"><strong>Human review history</strong>{reviews.map((review) => <p key={review.id}>{review.disposition} · {review.reviewer_id} · {new Date(review.created_at).toLocaleString()}<br />{review.rationale}</p>)}</div>}{finding.status === "candidate" && <HumanDecisionBox label="Song's finding-disposition rationale" placeholder="Which test output, linked evidence, uncertainty, and missing context support this disposition?" actions={[{ disposition: "confirmed_control_issue", label: "Confirm control issue" }, { disposition: "dismissed", label: "Dismiss", secondary: true }, { disposition: "needs_more_evidence", label: "Needs evidence", secondary: true }, { disposition: "not_applicable", label: "Not applicable", secondary: true }]} onReview={async (disposition, rationale) => { await api.reviewFinding(finding.id, disposition, rationale, "Song"); await load(); }} />}</article>)}</section></>;
}

function EvaluationsPage() {
  const [items, setItems] = useState<Evaluation[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(() => api.evaluations().then(setItems), []);
  useEffect(() => { void load(); }, [load]);
  async function run() { const result = await api.runEvaluation(); setMessage(`Queued job ${result.job_id}. Refresh this page after the worker completes.`); }
  return <><PageHeading eyebrow="Measured, not claimed" title="Gold-set evaluations" text="Metrics come from 50 fixed synthetic MP4 cases. They do not estimate real-world platform prevalence or business impact." /><div className="actions"><button onClick={() => void run().catch((e: Error) => setMessage(e.message))}>Run evaluation</button><button className="secondary" onClick={() => void load()}>Refresh results</button></div><ErrorNotice message={message} /><section className="card-list">{items.map((item) => {
    const asr = objectValue(item.metrics.asr_phrase_detection);
    const ocr = objectValue(item.metrics.ocr_phrase_detection);
    const provider = String(asr.provider ?? "not recorded");
    const selector = String(asr.evidence_selector ?? "legacy result — selector not recorded");
    const isVerifiedMedia = provider === "faster-whisper" && selector === "extractor_matches_provider";
    return <article className="record-card evaluation-card" key={item.id}><div className="record-title"><div><p>{new Date(item.created_at).toLocaleString()} · {item.id}</p><h2>{item.dataset_version}</h2></div><div className="status-stack"><StatusPill value={item.status} /><span className={`status status-${isVerifiedMedia ? "normal" : "attention"}`}>{isVerifiedMedia ? "Faster-Whisper evidence" : `${provider} evidence`}</span></div></div><section className="metric-grid" aria-label={`Evaluation metrics for ${item.id}`}><article className="metric-card"><p>Cases with result</p><strong>{String(item.metrics.cases_with_result ?? "—")} / {String(item.metrics.cases_total ?? "—")}</strong></article><article className="metric-card"><p>OCR precision / recall</p><strong>{rate(ocr.precision)} / {rate(ocr.recall)}</strong></article><article className="metric-card"><p>ASR precision / recall</p><strong>{rate(asr.precision)} / {rate(asr.recall)}</strong></article><article className="metric-card"><p>Source freshness</p><strong>{rate(item.metrics.source_freshness_rate)}</strong></article></section><dl className="detail-grid"><dt>ASR provider</dt><dd>{provider}</dd><dt>Evidence selector</dt><dd className="mono">{selector}</dd><dt>Operational rules</dt><dd>{String(item.metrics.operational_rule_activation)}</dd><dt>Failures</dt><dd>{String(item.metrics.cases_failed ?? item.failures.length)}</dd></dl><details><summary>Full metrics and retained errors</summary><pre>{JSON.stringify(item.metrics, null, 2)}</pre></details></article>;
  })}</section></>;
}

function AuditPackPage() {
  const [cases, setCases] = useState<MediaCase[]>([]);
  const [caseId, setCaseId] = useState("");
  const [exports, setExports] = useState<ReportExport[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(
    () =>
      Promise.all([api.cases(), api.reports()]).then(([c, r]) => {
        setCases(c);
        setExports(r);
      }),
    [],
  );
  useEffect(() => { void load(); }, [load]);
  async function generate() { try { await api.exportReport(caseId, ["html", "pdf", "json", "csv"]); setMessage("Four evidence-bound artifacts generated locally. Nothing was submitted externally."); await load(); } catch (e) { setMessage(e instanceof Error ? e.message : "Export failed"); } }
  return <><PageHeading eyebrow="Portable evidence with lineage" title="Audit package" text="Exports are local review artifacts with hashes and a lineage manifest. Generating one never sends it anywhere." /><section className="panel"><div className="form-row"><select aria-label="Media case" value={caseId} onChange={(e) => setCaseId(e.target.value)}><option value="">Choose a case…</option>{cases.map((item) => <option key={item.id} value={item.id}>{item.stable_key}</option>)}</select><button disabled={!caseId} onClick={() => void generate()}>Generate all formats</button></div><ErrorNotice message={message} /></section><section className="card-list">{exports.map((item) => <article className="record-card" key={item.id}><div className="record-title"><h2>{item.format.toUpperCase()} · {cases.find((c) => c.id === item.case_id)?.stable_key ?? item.case_id}</h2><StatusPill value={String(item.lineage_manifest.package_status ?? "generated")} /></div><dl className="detail-grid"><dt>Local path</dt><dd>{item.file_path}</dd><dt>SHA-256</dt><dd className="mono">{item.content_hash}</dd></dl></article>)}</section></>;
}

const pages: Record<Page, () => JSX.Element> = {
  Overview: OverviewPage,
  Sources: SourcesPage,
  Requirements: RequirementsPage,
  Controls: ControlsPage,
  "Media Cases": MediaCasesPage,
  "Review Queue": ReviewQueuePage,
  Evaluations: EvaluationsPage,
  "Audit Pack": AuditPackPage,
};

export default function App() {
  const [page, setPage] = useState<Page>("Overview");
  const ActivePage = pages[page];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">CC</div><p className="brand-title">Creator Commerce</p><p className="brand-subtitle">Governance Agent</p>
        <nav aria-label="Primary navigation">{navItems.map((item) => <button className={page === item ? "nav-item nav-active" : "nav-item"} key={item} onClick={() => setPage(item)}>{item}</button>)}</nav>
        <p className="sidebar-note">Independent portfolio project. Not affiliated with TikTok. Not legal advice.</p>
      </aside>
      <main><ActivePage /></main>
    </div>
  );
}
