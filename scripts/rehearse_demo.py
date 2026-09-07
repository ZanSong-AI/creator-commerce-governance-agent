#!/usr/bin/env python3
"""Read-only preflight for the evidence-only 10-minute interview demo."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from typing import Any


class DemoPreflightError(RuntimeError):
    """Raised when the running demo no longer matches its documented evidence."""


def fetch_json(base_url: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DemoPreflightError(f"Could not read {url}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DemoPreflightError(message)


def evidence_with(
    evidence: list[dict[str, Any]], evidence_type: str, **observed: Any
) -> bool:
    return any(
        item.get("evidence_type") == evidence_type
        and all(item.get("observed_value", {}).get(key) == value for key, value in observed.items())
        for item in evidence
    )


def run(base_url: str) -> dict[str, Any]:
    health = fetch_json(base_url, "health")
    overview = fetch_json(base_url, "overview")
    sources = fetch_json(base_url, "sources")
    lineage = fetch_json(base_url, "requirements/lineage")
    mappings = fetch_json(base_url, "mappings/lineage")
    findings = fetch_json(base_url, "findings/lineage")
    cases = fetch_json(base_url, "cases")
    evaluations = fetch_json(base_url, "evaluations")
    reports = fetch_json(base_url, "reports")

    require(health.get("status") == "healthy", "API health is not healthy")
    require(
        health.get("dependencies", {}).get("cloud_enabled") is False,
        "Cloud must remain disabled for the evidence-only demo",
    )
    require(overview.get("review_backlog") == 9, "Overview review backlog is not nine")

    source_statuses = Counter(item.get("status") for item in sources)
    require(len(sources) == 9, f"Expected 9 registered sources, found {len(sources)}")
    require(
        source_statuses == {"current": 7, "changed": 2},
        f"Unexpected source status distribution: {dict(source_statuses)}",
    )
    changed_source_keys = {
        item.get("stable_key") for item in sources if item.get("status") == "changed"
    }
    require(
        changed_source_keys
        == {"us-ftc-disclosures-101", "us-ftc-endorsement-faq"},
        f"Unexpected changed sources: {sorted(changed_source_keys)}",
    )
    checked_at = [
        datetime.fromisoformat(str(item["last_checked_at"]).replace("Z", "+00:00"))
        for item in sources
    ]
    refresh_window_seconds = (max(checked_at) - min(checked_at)).total_seconds()
    require(
        refresh_window_seconds <= 60,
        f"Sources were not refreshed in one bounded window: {refresh_window_seconds}s",
    )

    authority = Counter(bool(item.get("authoritative_for_approval")) for item in lineage)
    requirement_statuses = Counter(item.get("requirement", {}).get("status") for item in lineage)
    require(len(lineage) == 9, f"Expected 9 requirements, found {len(lineage)}")
    require(authority == {False: 4, True: 5}, f"Unexpected authority split: {dict(authority)}")
    require(
        all(
            item.get("snapshot", {}).get("id")
            == item.get("latest_authoritative_snapshot_id")
            and not item.get("source_approval_blockers")
            for item in lineage
            if item.get("authoritative_for_approval")
        ),
        "An approval-eligible candidate is not bound to the latest authoritative snapshot",
    )
    require(
        all(
            item.get("source_approval_blockers")
            for item in lineage
            if not item.get("authoritative_for_approval")
        ),
        "A blocked requirement is missing explicit source approval blockers",
    )
    require(
        requirement_statuses == {"candidate": 9},
        f"Evidence-only demo requires nine candidates: {dict(requirement_statuses)}",
    )
    require(not mappings, "Evidence-only demo requires zero mappings")
    require(not findings, "Evidence-only demo requires zero findings")

    by_key = {item.get("stable_key"): item for item in cases}
    require(len(cases) == 50, f"Expected 50 media cases, found {len(cases)}")
    require(all(item.get("status") == "analyzed" for item in cases), "Not all media cases are analyzed")
    require("case-003" in by_key and "case-004" in by_key, "Demo cases 003/004 are missing")

    case_003_evidence = fetch_json(base_url, f"cases/{by_key['case-003']['id']}/evidence")
    case_004_evidence = fetch_json(base_url, f"cases/{by_key['case-004']['id']}/evidence")
    require(
        evidence_with(case_003_evidence, "c2pa", status="invalid", validation_state="Invalid"),
        "case-003 does not contain normalized invalid C2PA evidence",
    )
    require(
        evidence_with(case_004_evidence, "c2pa", status="present", validation_state="Valid"),
        "case-004 does not contain normalized test-signed C2PA evidence",
    )
    require(
        any(
            item.get("evidence_type") == "asr" and item.get("extractor") == "faster-whisper"
            for item in case_004_evidence
        ),
        "case-004 does not contain Faster-Whisper evidence",
    )
    for evidence_type in ("ocr", "caption", "platform_metadata", "relationship_metadata"):
        require(
            any(item.get("evidence_type") == evidence_type for item in case_004_evidence),
            f"case-004 is missing {evidence_type} evidence",
        )

    verified_evaluation = next(
        (
            item
            for item in evaluations
            if item.get("status") == "completed"
            and item.get("metrics", {}).get("asr_phrase_detection", {}).get("provider")
            == "faster-whisper"
            and item.get("metrics", {}).get("asr_phrase_detection", {}).get("evidence_selector")
            == "extractor_matches_provider"
        ),
        None,
    )
    require(verified_evaluation is not None, "No provider-isolated Faster-Whisper evaluation exists")
    metrics = verified_evaluation["metrics"]
    require(metrics.get("cases_total") == 50, "Verified evaluation does not cover 50 cases")
    require(metrics.get("cases_with_result") == 50, "Verified evaluation did not produce 50 results")
    require(metrics.get("cases_failed") == 0, "Verified evaluation contains failures")
    require(metrics.get("operational_rule_activation") is False, "Evaluation activated operational rules")
    require(
        metrics.get("approved_requirements") == 0,
        "Evaluation unexpectedly reports approved requirements",
    )
    require(metrics.get("approved_mappings") == 0, "Evaluation unexpectedly reports approved mappings")
    require(metrics.get("source_freshness_rate") == 1.0, "Source freshness is not 9/9")
    require(metrics.get("ocr_phrase_detection", {}).get("recall") == 0.8571, "Unexpected OCR recall")
    require(metrics.get("asr_phrase_detection", {}).get("recall") == 0.8571, "Unexpected ASR recall")
    require(metrics.get("provenance_parsing_success_rate") == 1.0, "Unexpected C2PA parsing rate")

    case_004_reports = [item for item in reports if item.get("case_id") == by_key["case-004"]["id"]]
    report_formats = {item.get("format") for item in case_004_reports}
    require(
        {"html", "pdf", "json", "csv"}.issubset(report_formats),
        f"case-004 is missing report formats: {sorted({'html', 'pdf', 'json', 'csv'} - report_formats)}",
    )
    require(
        all(
            item.get("lineage_manifest", {}).get("package_status")
            == "evidence_only_no_approved_rule_result"
            for item in case_004_reports
        ),
        "case-004 report package status is not evidence-only",
    )

    return {
        "status": "ready",
        "profile": "evidence_only_source_refresh_v2",
        "api": health.get("status"),
        "cloud_enabled": False,
        "sources": dict(source_statuses),
        "source_refresh_window_seconds": refresh_window_seconds,
        "requirements": dict(requirement_statuses),
        "authoritative_for_approval": {str(key).lower(): value for key, value in authority.items()},
        "mappings": len(mappings),
        "findings": len(findings),
        "media_cases": len(cases),
        "demo_cases": ["case-003", "case-004"],
        "evaluation_id": verified_evaluation["id"],
        "evaluation_provider": metrics["asr_phrase_detection"]["provider"],
        "ocr_recall": metrics["ocr_phrase_detection"]["recall"],
        "asr_recall": metrics["asr_phrase_detection"]["recall"],
        "report_formats": sorted(report_formats),
        "external_actions": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    args = parser.parse_args()
    try:
        result = run(args.base_url)
    except DemoPreflightError as exc:
        print(f"DEMO PREFLIGHT FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
