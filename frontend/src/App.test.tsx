import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});
test("renders the human-review boundary and service state", async () => {
  const health = {
      status: "healthy",
      service: "creator-commerce-governance-api",
      version: "0.1.0-dev",
      environment: "test",
      dependencies: { database: "ok", redis: "ok", worker: "configured", cloud_enabled: false },
    };
  const overview = {
    source_freshness: { current: 9 },
    candidate_queue: { requirement_candidate: 4 },
    review_backlog: 4,
    media_cases: 50,
    evaluation_status: "completed",
    recent_audit_events: [],
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(health), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(overview), { status: 200 }));

  render(<App />);

  expect(screen.getByText("Evidence and candidates, never legal conclusions")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("healthy")).toBeInTheDocument());
  expect(screen.getByText("No audit events returned.")).toBeInTheDocument();
  expect(screen.getByText("50")).toBeInTheDocument();
});

test("shows verified extraction only for an authoritative fixture-backed snapshot", async () => {
  const health = {
    status: "healthy",
    service: "creator-commerce-governance-api",
    version: "0.1.0-dev",
    environment: "test",
    dependencies: { database: "ok", redis: "ok", worker: "configured", cloud_enabled: false },
  };
  const overview = {
    source_freshness: { current: 1 },
    candidate_queue: {},
    review_backlog: 0,
    media_cases: 0,
    evaluation_status: "not_run",
    recent_audit_events: [],
  };
  const source = {
    id: "source-tiktok",
    stable_key: "tiktok-aigc-labeling",
    publisher: "TikTok",
    title: "About AI-generated content",
    official_url: "https://support.tiktok.com/en/example",
    source_type: "platform_policy_help",
    jurisdiction: "GLOBAL_PLATFORM",
    published_date: null,
    effective_date: null,
    version: "not_published",
    applicable_scope: "Creator AIGC labeling",
    fetch_mode: "tiktok_faq_api",
    redistribution_note: "Runtime snapshot only",
    status: "changed",
    last_checked_at: "2026-08-28T00:00:00Z",
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  const snapshot = {
    id: "snapshot-tiktok",
    source_id: source.id,
    content_hash: "a".repeat(64),
    retrieved_at: "2026-08-28T00:00:00Z",
    locator_map: {
      retrieval_mode: "official_tiktok_public_faq_api",
      faq_id: "7636670084747893268",
      article_title: "About AI-generated content",
      locale: "en",
      country: "US",
    },
    diff_from_snapshot_id: "snapshot-old",
    diff_summary: { kind: "changed", added_lines: 3, removed_lines: 1 },
    fetch_status: "current",
    immutable: true,
    created_at: "2026-08-28T00:00:00Z",
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(health), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(overview), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify([source]), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify([snapshot]), { status: 200 }));

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));

  await waitFor(() => expect(screen.getByText("About AI-generated content")).toBeInTheDocument());
  expect(screen.getByText(/Latest immutable snapshot/)).toBeInTheDocument();
  expect(screen.getByText(/FAQ 7636670084747893268 · en-US/)).toBeInTheDocument();
  expect(screen.getByText(/Verified article identity: About AI-generated content/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Create verified candidates" })).toBeInTheDocument();
});

test("blocks requirement approval when lineage only has a public test fixture", async () => {
  const health = {
    status: "healthy",
    service: "creator-commerce-governance-api",
    version: "0.1.0-dev",
    environment: "test",
    dependencies: { database: "ok", redis: "ok", worker: "configured", cloud_enabled: false },
  };
  const overview = {
    source_freshness: { fixture_only: 1 },
    candidate_queue: { requirement_candidate: 1 },
    review_backlog: 1,
    media_cases: 0,
    evaluation_status: "not_run",
    recent_audit_events: [],
  };
  const source = {
    id: "source-fixture",
    stable_key: "us-ftc-endorsement-guides-16-cfr-255",
    publisher: "Federal Trade Commission",
    title: "FTC Endorsement Guides",
    official_url: "https://www.ecfr.gov/example",
    source_type: "administrative_guide",
    jurisdiction: "US",
    published_date: null,
    effective_date: "2023-07-26",
    version: "test",
    applicable_scope: "Synthetic review test",
    fetch_mode: "manual_if_blocked",
    redistribution_note: "Test only",
    status: "manual_snapshot_required",
    last_checked_at: null,
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  const snapshot = {
    id: "snapshot-fixture",
    source_id: source.id,
    content_hash: "b".repeat(64),
    retrieved_at: "2026-08-28T00:00:00Z",
    locator_map: {},
    diff_from_snapshot_id: null,
    diff_summary: { kind: "initial" },
    fetch_status: "public_test_fixture",
    immutable: true,
    created_at: "2026-08-28T00:00:00Z",
  };
  const requirement = {
    id: "requirement-fixture",
    source_snapshot_id: snapshot.id,
    exact_quote: "Exact fixture quote",
    source_locator: "16 CFR 255.0(f)",
    actor: "advertiser or endorser",
    trigger: "a multimodal representation requires disclosure",
    required_action: "provide visual and audible disclosure",
    exception: null,
    jurisdiction: "US",
    effective_date: "2023-07-26",
    scope: "Synthetic promotional video",
    confidence: 1,
    uncertainties: [],
    status: "candidate",
    model_provider: "fixture",
    model_version: "test",
    prompt_version: "test",
    validation: { exact_quote_present: true, legal_language_guard_passed: true },
    correlation_id: "fixture-lineage",
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  const lineage = [{
    requirement,
    source,
    snapshot,
    reviews: [],
    review_context: {
      excerpt: "Previous context.\nExact fixture quote\nFollowing context.",
      excerpt_sha256: "context-hash",
      exact_quote_found: true,
      start_line: 1,
      end_line: 3,
      truncated: false,
    },
    authoritative_for_approval: false,
    latest_authoritative_snapshot_id: null,
    source_approval_blockers: ["parent snapshot is not current or human-confirmed"],
  }];
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(health), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(overview), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(lineage), { status: 200 }));

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Requirements" }));

  await waitFor(() => expect(screen.getByText("Exact fixture quote")).toBeInTheDocument());
  expect(screen.getByText(/Previous context/)).toBeInTheDocument();
  expect(screen.getByText(/Source authorization is blocked/)).toBeInTheDocument();
  expect(screen.getByText(/parent snapshot is not current or human-confirmed/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Approve candidate" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Needs evidence" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Song's review rationale"), {
    target: { value: "The current source snapshot still requires authoritative evidence." },
  });
  expect(screen.getByRole("button", { name: "Approve candidate" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Needs evidence" })).toBeEnabled();
});

test("labels a provider-isolated Faster-Whisper evaluation for the demo", async () => {
  const health = {
    status: "healthy",
    service: "creator-commerce-governance-api",
    version: "0.1.0-dev",
    environment: "test",
    dependencies: { database: "ok", redis: "ok", worker: "configured", cloud_enabled: false },
  };
  const overview = {
    source_freshness: { current: 4, changed: 2, manual_snapshot_required: 3 },
    candidate_queue: { requirement_candidate: 6 },
    review_backlog: 6,
    media_cases: 50,
    evaluation_status: "completed",
    recent_audit_events: [],
  };
  const evaluation = {
    id: "evaluation-real-asr",
    dataset_version: "media-gold-2026-08-27.v1",
    rule_version: "evaluation-only-rule-pack-2026-08-27.v1",
    status: "completed",
    metrics: {
      cases_total: 50,
      cases_with_result: 50,
      cases_failed: 0,
      source_freshness_rate: 0.6667,
      operational_rule_activation: false,
      ocr_phrase_detection: { precision: 1, recall: 0.8571 },
      asr_phrase_detection: {
        provider: "faster-whisper",
        evidence_selector: "extractor_matches_provider",
        precision: 1,
        recall: 0.8571,
      },
    },
    failures: [],
    correlation_id: "evaluation-correlation",
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(health), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(overview), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify([evaluation]), { status: 200 }));

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Evaluations" }));

  await waitFor(() => expect(screen.getByText("Faster-Whisper evidence")).toBeInTheDocument());
  expect(screen.getByText("50 / 50")).toBeInTheDocument();
  expect(screen.getByText("extractor_matches_provider")).toBeInTheDocument();
  expect(screen.getAllByText("1.0000 / 0.8571")).toHaveLength(2);
});

test("requires a typed rationale before a finding disposition", async () => {
  const health = {
    status: "healthy",
    service: "creator-commerce-governance-api",
    version: "0.1.0-dev",
    environment: "test",
    dependencies: { database: "ok", redis: "ok", worker: "configured", cloud_enabled: false },
  };
  const overview = {
    source_freshness: { current: 1 },
    candidate_queue: { finding_candidate: 1 },
    review_backlog: 1,
    media_cases: 1,
    evaluation_status: "completed",
    recent_audit_events: [],
  };
  const requirement = {
    id: "requirement-approved",
    source_snapshot_id: "snapshot-current",
    exact_quote: "The exact approved requirement quote.",
    source_locator: "Section 1",
    actor: "provider",
    trigger: "test trigger",
    required_action: "test action",
    exception: null,
    jurisdiction: "US",
    effective_date: null,
    scope: "Synthetic test scope",
    confidence: 1,
    uncertainties: [],
    status: "approved",
    model_provider: "fixture",
    model_version: "test",
    prompt_version: "test",
    validation: { exact_quote_present: true },
    correlation_id: "requirement-correlation",
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  const control = {
    id: "control-one",
    stable_key: "visual_disclosure_detected",
    name: "Visual disclosure detected",
    description: "Checks extracted visual disclosure evidence.",
    evidence_kind: "ocr",
    rule_type: "deterministic",
    rule_version: "test-v1",
    rule_config: {},
    active: true,
  };
  const finding = {
    id: "finding-one",
    case_id: "case-one",
    test_run_id: "test-one",
    requirement_id: requirement.id,
    control_id: control.id,
    evidence_ids: ["evidence-one"],
    title: "Visual disclosure evidence issue candidate",
    explanation: "The deterministic test did not detect the expected phrase.",
    uncertainty: "OCR may have missed degraded text.",
    status: "candidate",
    correlation_id: "finding-correlation",
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  const testRun = {
    id: "test-one",
    case_id: "case-one",
    mapping_id: "mapping-one",
    control_id: control.id,
    requirement_id: requirement.id,
    rule_version: "test-v1",
    status: "issue_candidate",
    result: { detected: false },
    evidence_ids: ["evidence-one"],
    correlation_id: "test-correlation",
    created_at: "2026-08-28T00:00:00Z",
    updated_at: "2026-08-28T00:00:00Z",
  };
  const evidence = {
    id: "evidence-one",
    case_id: "case-one",
    stable_key: "ocr-frame-one",
    evidence_type: "ocr",
    observed_value: { text: "degraded text" },
    timestamp_ms: 0,
    frame_index: 0,
    transcript_span: null,
    extractor: "tesseract",
    extractor_version: "test",
    confidence: null,
    source_hash: "a".repeat(64),
    correlation_id: "evidence-correlation",
    created_at: "2026-08-28T00:00:00Z",
  };
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(health), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(overview), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify([{
      finding,
      test_run: testRun,
      requirement,
      control,
      evidence: [evidence],
      reviews: [],
    }]), { status: 200 }));

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Review Queue" }));

  await waitFor(() => expect(screen.getByText(finding.title)).toBeInTheDocument());
  expect(screen.getByRole("button", { name: "Confirm control issue" })).toBeDisabled();
  expect(screen.getByText("issue_candidate")).toBeInTheDocument();
  expect(screen.getByText("1", { exact: true })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Song's finding-disposition rationale"), {
    target: { value: "The linked OCR evidence is insufficient and needs human context." },
  });
  expect(screen.getByRole("button", { name: "Confirm control issue" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Needs evidence" })).toBeEnabled();
});
