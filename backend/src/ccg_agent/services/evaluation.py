from __future__ import annotations

import re
import time
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    Control,
    EvaluationRun,
    EvidenceItem,
    MediaCase,
    RequirementCandidate,
    RequirementControlMapping,
    Source,
)
from ..settings import Settings
from .media import DISCLOSURE_PHRASES, extract_evidence

FRESH_SOURCE_STATUSES = ("current", "changed")


def count_fresh_sources(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(Source)
            .where(Source.status.in_(FRESH_SOURCE_STATUSES))
        )
        or 0
    )


def _detected(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized) for phrase in DISCLOSURE_PHRASES)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(ordered[index], 2)


def _asr_evidence_for_provider(
    values: list[EvidenceItem], provider: str
) -> list[EvidenceItem]:
    """Keep evaluation evidence isolated to the configured ASR provider.

    A case may retain both real Faster-Whisper evidence and deterministic CI
    fixture evidence. Creation time must never decide which provider an
    evaluation measures.
    """
    return [
        item
        for item in values
        if item.evidence_type == "asr" and item.extractor == provider
    ]


def run_gold_evaluation(session: Session, settings: Settings) -> EvaluationRun:
    started = time.perf_counter()
    evaluation = EvaluationRun(
        dataset_version="media-gold-2026-08-27.v1",
        rule_version="evaluation-only-rule-pack-2026-08-27.v1",
        status="running",
        metrics={},
        failures=[],
        correlation_id=str(uuid.uuid4()),
    )
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    cases = list(session.scalars(select(MediaCase).order_by(MediaCase.stable_key)))
    failures: list[dict[str, Any]] = []
    latencies: list[float] = []
    ocr_tp = ocr_fp = ocr_fn = 0
    asr_tp = asr_fp = asr_fn = 0
    finding_tp = finding_fp = finding_fn = 0
    provenance_correct = 0
    completed = 0
    abstained = 0
    evidence_reused = 0
    detection_errors: list[dict[str, Any]] = []
    for case in cases:
        case_started = time.perf_counter()
        try:
            values = list(
                session.scalars(
                    select(EvidenceItem)
                    .where(
                        EvidenceItem.case_id == case.id,
                        EvidenceItem.source_hash == case.asset_sha256,
                    )
                    .order_by(EvidenceItem.created_at)
                )
            )
            has_current_pipeline = (
                any(item.evidence_type == "ocr" for item in values)
                and any(
                    item.evidence_type == "asr" and item.extractor == settings.asr_provider for item in values
                )
                and any(
                    item.evidence_type == "c2pa" and "normalization-v2" in item.extractor_version
                    for item in values
                )
            )
            if has_current_pipeline:
                evidence_reused += 1
            else:
                extract_evidence(session, settings, case)
                values = list(
                    session.scalars(
                        select(EvidenceItem)
                        .where(
                            EvidenceItem.case_id == case.id,
                            EvidenceItem.source_hash == case.asset_sha256,
                        )
                        .order_by(EvidenceItem.created_at)
                    )
                )
            ocr_text = " ".join(
                str(item.observed_value.get("text", "")) for item in values if item.evidence_type == "ocr"
            )
            asr_values = _asr_evidence_for_provider(values, settings.asr_provider)
            c2pa_values = [item for item in values if item.evidence_type == "c2pa"]
            ocr_prediction = _detected(ocr_text)
            asr_prediction = (
                _detected(str(asr_values[-1].observed_value.get("text", ""))) if asr_values else False
            )
            ocr_expected = bool(case.metadata_json.get("visual_disclosure_expected"))
            asr_expected = bool(case.metadata_json.get("audio_disclosure_expected"))
            asr_text = str(asr_values[-1].observed_value.get("text", "")) if asr_values else ""
            if ocr_prediction != ocr_expected:
                detection_errors.append(
                    {
                        "case": case.stable_key,
                        "modality": "ocr",
                        "expected": ocr_expected,
                        "predicted": ocr_prediction,
                        "observed_text": ocr_text[:500],
                    }
                )
            if asr_prediction != asr_expected:
                detection_errors.append(
                    {
                        "case": case.stable_key,
                        "modality": "asr",
                        "expected": asr_expected,
                        "predicted": asr_prediction,
                        "observed_text": asr_text[:500],
                    }
                )
            ocr_tp += int(ocr_prediction and ocr_expected)
            ocr_fp += int(ocr_prediction and not ocr_expected)
            ocr_fn += int(not ocr_prediction and ocr_expected)
            asr_tp += int(asr_prediction and asr_expected)
            asr_fp += int(asr_prediction and not asr_expected)
            asr_fn += int(not asr_prediction and asr_expected)
            expected_c2pa = str(case.metadata_json.get("c2pa_fixture_state", "absent"))
            actual_c2pa = c2pa_values[-1].observed_value.get("status") if c2pa_values else "unavailable"
            if expected_c2pa in {"present", "test_signed"}:
                provenance_correct += int(actual_c2pa == "present")
            else:
                provenance_correct += int(actual_c2pa == expected_c2pa)
            if case.relationship_type != "none":
                for expected, predicted in (
                    (not ocr_expected, not ocr_prediction),
                    (not asr_expected, not asr_prediction),
                ):
                    finding_tp += int(expected and predicted)
                    finding_fp += int(not expected and predicted)
                    finding_fn += int(expected and not predicted)
            if bool(case.metadata_json.get("ambiguous_evidence")):
                abstained += 1
            completed += 1
        except Exception as exc:
            failures.append(
                {"case": case.stable_key, "error_type": type(exc).__name__, "error": str(exc)[:300]}
            )
            abstained += 1
        latencies.append((time.perf_counter() - case_started) * 1000)
    requirements = list(session.scalars(select(RequirementCandidate)))
    schema_valid = sum(
        1
        for item in requirements
        if all(
            [
                item.exact_quote,
                item.source_locator,
                item.actor,
                item.trigger,
                item.required_action,
                item.scope,
            ]
        )
    )
    quote_valid = sum(1 for item in requirements if item.validation.get("exact_quote_present") is True)
    total_sources = session.scalar(select(func.count()).select_from(Source)) or 0
    fresh_sources = count_fresh_sources(session)
    approved_requirements = (
        session.scalar(
            select(func.count())
            .select_from(RequirementCandidate)
            .where(RequirementCandidate.status == "approved")
        )
        or 0
    )
    approved_mappings = (
        session.scalar(
            select(func.count())
            .select_from(RequirementControlMapping)
            .where(RequirementControlMapping.status == "approved")
        )
        or 0
    )
    controls = session.scalar(select(func.count()).select_from(Control)) or 0
    total_seconds = time.perf_counter() - started
    predicted_findings = finding_tp + finding_fp
    expected_findings = finding_tp + finding_fn
    metrics = {
        "evaluation_mode": "isolated_gold_fixture",
        "operational_rule_activation": False,
        "evidence_reused_from_verified_run": evidence_reused,
        "cases_total": len(cases),
        "cases_with_result": completed,
        "cases_failed": len(failures),
        "schema_valid_output_rate": _ratio(schema_valid, len(requirements)),
        "exact_quote_validation_rate": _ratio(quote_valid, len(requirements)),
        "ocr_phrase_detection": {
            "precision": _ratio(ocr_tp, ocr_tp + ocr_fp),
            "recall": _ratio(ocr_tp, ocr_tp + ocr_fn),
            "true_positive": ocr_tp,
            "false_positive": ocr_fp,
            "false_negative": ocr_fn,
        },
        "asr_phrase_detection": {
            "provider": settings.asr_provider,
            "evidence_selector": "extractor_matches_provider",
            "precision": _ratio(asr_tp, asr_tp + asr_fp),
            "recall": _ratio(asr_tp, asr_tp + asr_fn),
            "true_positive": asr_tp,
            "false_positive": asr_fp,
            "false_negative": asr_fn,
        },
        "provenance_parsing_success_rate": _ratio(provenance_correct, len(cases)),
        "candidate_finding_precision": _ratio(finding_tp, predicted_findings),
        "candidate_finding_recall": _ratio(finding_tp, expected_findings),
        "candidate_finding_false_positive_rate": _ratio(finding_fp, predicted_findings),
        "abstention_rate": _ratio(abstained, len(cases)),
        "source_freshness_rate": _ratio(int(fresh_sources), int(total_sources)),
        "approved_requirement_control_coverage": _ratio(int(approved_mappings), int(approved_requirements)),
        "approved_requirements": int(approved_requirements),
        "approved_mappings": int(approved_mappings),
        "defined_controls": int(controls),
        "review_backlog": sum(
            1 for item in requirements if item.status in {"candidate", "needs_more_evidence"}
        ),
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "batch_throughput_cases_per_second": round(len(cases) / total_seconds, 2) if total_seconds else 0.0,
        "detection_errors": detection_errors,
        "limitations": [
            "Synthetic gold data is not an estimate of real platform prevalence.",
            "Prominence and legal applicability remain human review tasks.",
            "Evaluation rules do not authorize operational mappings.",
        ],
    }
    evaluation.metrics = metrics
    evaluation.failures = failures
    evaluation.status = "completed" if completed == len(cases) else "completed_with_failures"
    session.commit()
    session.refresh(evaluation)
    return evaluation
