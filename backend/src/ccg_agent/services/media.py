from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import subprocess
import uuid
from fractions import Fraction
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Control,
    EvidenceItem,
    Finding,
    MediaCase,
    RequirementCandidate,
    RequirementControlMapping,
    TestRun,
)
from ..settings import Settings

DISCLOSURE_PHRASES = {
    "ad",
    "sponsored",
    "paid partnership",
    "free product",
    "affiliate",
    "publicidad",
    "patrocinado",
    "colaboracion pagada",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_media_cases(session: Session, settings: Settings) -> list[MediaCase]:
    manifest_path = settings.project_root / "fixtures" / "media" / "cases.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: list[MediaCase] = []
    for item in manifest["cases"]:
        case = session.scalar(select(MediaCase).where(MediaCase.stable_key == item["stable_key"]))
        if case is None:
            case = MediaCase(
                stable_key=item["stable_key"],
                asset_path=item["asset_path"],
                asset_sha256=item["asset_sha256"],
                mime_type=item["mime_type"],
                caption=item["caption"],
                jurisdiction=item["jurisdiction"],
                relationship_type=item["relationship_type"],
                platform_disclosure_flag=item["platform_disclosure_flag"],
                aigc_expected=item["aigc_expected"],
                visible_aigc_label=item["visible_aigc_label"],
                expected_outcomes=item["expected_outcomes"],
                metadata_json={
                    key: value
                    for key, value in item.items()
                    if key
                    not in {
                        "asset_path",
                        "asset_sha256",
                        "mime_type",
                        "caption",
                        "jurisdiction",
                        "relationship_type",
                        "platform_disclosure_flag",
                        "aigc_expected",
                        "visible_aigc_label",
                        "expected_outcomes",
                    }
                },
            )
            session.add(case)
        elif case.asset_sha256 != item["asset_sha256"]:
            case.asset_sha256 = item["asset_sha256"]
            case.status = "ready"
            case.metadata_json = case.metadata_json | {"c2pa_fixture_state": item["c2pa_fixture_state"]}
        cases.append(case)
    session.commit()
    for case in cases:
        session.refresh(case)
    return cases


def _asset_path(case: MediaCase, settings: Settings) -> Path:
    path = (settings.project_root / case.asset_path).resolve()
    root = settings.project_root.resolve()
    if root not in path.parents:
        raise HTTPException(status_code=400, detail="Media path escapes the project root")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media asset is missing")
    if path.stat().st_size > settings.max_media_bytes:
        raise HTTPException(status_code=413, detail="Media exceeds configured size limit")
    if (
        case.mime_type != "video/mp4"
        or path.suffix.lower() != ".mp4"
        or mimetypes.guess_type(path.name)[0] != "video/mp4"
    ):
        raise HTTPException(status_code=415, detail="Only MP4 fixtures are supported")
    with path.open("rb") as stream:
        header = stream.read(32)
    if b"ftyp" not in header[4:32]:
        raise HTTPException(status_code=415, detail="Media does not contain an ISO BMFF ftyp signature")
    actual_hash = sha256_file(path)
    if actual_hash != case.asset_sha256:
        raise HTTPException(status_code=409, detail="Media hash does not match the registered case")
    return path


def _run(command: list[str], *, timeout: int = 120) -> str:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise RuntimeError(f"media tool failed: {command[0]} ({type(exc).__name__})") from exc


def _probe(path: Path) -> dict[str, Any]:
    raw = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,nb_frames,r_frame_rate",
            "-of",
            "json",
            str(path),
        ]
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=415, detail="FFprobe returned invalid media metadata") from exc


def _validate_probe(probe: dict[str, Any], settings: Settings) -> None:
    try:
        duration = float(probe["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=415, detail="Media duration is missing or invalid") from exc
    if duration <= 0:
        raise HTTPException(status_code=415, detail="Media duration must be positive")
    if duration > settings.max_media_duration_seconds:
        raise HTTPException(status_code=413, detail="Media exceeds configured duration limit")

    video_streams = [
        stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"
    ]
    if not video_streams:
        raise HTTPException(status_code=415, detail="Media does not contain a video stream")
    for stream in video_streams:
        try:
            width = int(stream["width"])
            height = int(stream["height"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=415, detail="Video dimensions are missing or invalid") from exc
        if width <= 0 or height <= 0:
            raise HTTPException(status_code=415, detail="Video dimensions must be positive")
        if width > settings.max_video_width or height > settings.max_video_height:
            raise HTTPException(status_code=413, detail="Video exceeds configured resolution limit")

        frames: int | None = None
        try:
            if stream.get("nb_frames") not in {None, "N/A"}:
                frames = int(stream["nb_frames"])
            elif stream.get("r_frame_rate") not in {None, "0/0"}:
                frames = int(float(Fraction(str(stream["r_frame_rate"]))) * duration)
        except (ValueError, ZeroDivisionError):
            frames = None
        if frames is None or frames <= 0:
            raise HTTPException(status_code=415, detail="Video frame count is missing or invalid")
        if frames > settings.max_video_frames:
            raise HTTPException(status_code=413, detail="Video exceeds configured frame limit")


def _ocr(path: Path, output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for previous in output_dir.glob("frame-*.png"):
        previous.unlink()
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(path),
            "-vf",
            "fps=1",
            str(output_dir / "frame-%03d.png"),
        ]
    )
    frames: list[dict[str, Any]] = []
    for index, frame in enumerate(sorted(output_dir.glob("frame-*.png"))):
        try:
            text = _run(["tesseract", str(frame), "stdout", "-l", "eng+spa"], timeout=30).strip()
            status = "ok"
        except RuntimeError:
            text = ""
            status = "error"
        frames.append(
            {
                "frame_index": index,
                "timestamp_ms": index * 1000,
                "text": text,
                "status": status,
                "frame_sha256": sha256_file(frame),
            }
        )
    return frames


def _asr(path: Path, case: MediaCase, settings: Settings) -> dict[str, Any]:
    if settings.asr_provider == "fixture":
        expected = bool(case.metadata_json.get("audio_disclosure_expected"))
        language = str(case.metadata_json.get("language", "en"))
        if expected and language == "es":
            text = "Este video es patrocinado por la marca ficticia NovaGlow Labs."
        elif expected:
            text = "This video is sponsored by fictional NovaGlow Labs."
        elif language == "es":
            text = "Esta es una demostracion de producto ficticio."
        else:
            text = "This is a fictional product demonstration."
        return {
            "status": "fixture",
            "provider": "fixture",
            "text": text,
            "language": language,
            "segments": [{"start_ms": 0, "end_ms": 2600, "text": text}],
        }
    if settings.asr_provider != "faster-whisper":
        return {"status": "unavailable", "provider": settings.asr_provider, "text": "", "segments": []}
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "tiny",
            device="cpu",
            compute_type="int8",
            download_root=str(settings.runtime_root / "models" / "faster-whisper"),
        )
        segments, info = model.transcribe(str(path), beam_size=1, vad_filter=False)
        values = [
            {"start_ms": int(segment.start * 1000), "end_ms": int(segment.end * 1000), "text": segment.text}
            for segment in segments
        ]
        return {
            "status": "ok",
            "provider": "faster-whisper",
            "model": "tiny",
            "language": info.language,
            "language_probability": info.language_probability,
            "text": " ".join(segment["text"].strip() for segment in values).strip(),
            "segments": values,
        }
    except Exception as exc:
        return {
            "status": "error",
            "provider": "faster-whisper",
            "error_type": type(exc).__name__,
            "text": "",
            "segments": [],
        }


def _c2pa(path: Path) -> dict[str, Any]:
    try:
        import c2pa
    except ImportError:
        return {"status": "unavailable", "sdk": "c2pa-python", "manifest_present": None}
    try:
        with c2pa.Context() as context, c2pa.Reader(str(path), context=context) as reader:
            raw = reader.detailed_json()
        payload = json.loads(raw)
        validation_state = payload.get("validation_state", "unknown")
        return {
            "status": "invalid" if str(validation_state).lower() == "invalid" else "present",
            "sdk": "c2pa-python",
            "sdk_version": getattr(c2pa, "__version__", "unknown"),
            "manifest_present": True,
            "validation_state": validation_state,
            "validation_status": payload.get("validation_status", []),
            "active_manifest": payload.get("active_manifest"),
        }
    except Exception as exc:
        message = str(exc)
        absent = "manifest" in message.lower() and (
            "not found" in message.lower() or "notfound" in message.lower() or "no claim" in message.lower()
        )
        return {
            "status": "absent" if absent else "invalid",
            "sdk": "c2pa-python",
            "sdk_version": getattr(c2pa, "__version__", "unknown"),
            "manifest_present": False if absent else None,
            "error_type": type(exc).__name__,
            "error_summary": message[:500],
        }


def _upsert_evidence(
    session: Session,
    *,
    case: MediaCase,
    stable_key: str,
    evidence_type: str,
    observed_value: dict[str, Any],
    extractor: str,
    extractor_version: str,
    correlation_id: str,
    timestamp_ms: int | None = None,
    frame_index: int | None = None,
    transcript_span: dict[str, Any] | None = None,
    confidence: float | None = None,
) -> EvidenceItem:
    versioned_key = f"{stable_key}@{case.asset_sha256[:12]}"
    existing = session.scalar(
        select(EvidenceItem).where(
            EvidenceItem.case_id == case.id,
            EvidenceItem.stable_key == versioned_key,
        )
    )
    if existing:
        return existing
    evidence = EvidenceItem(
        case_id=case.id,
        stable_key=versioned_key,
        evidence_type=evidence_type,
        observed_value=observed_value,
        extractor=extractor,
        extractor_version=extractor_version,
        source_hash=case.asset_sha256,
        correlation_id=correlation_id,
        timestamp_ms=timestamp_ms,
        frame_index=frame_index,
        transcript_span=transcript_span,
        confidence=confidence,
    )
    session.add(evidence)
    return evidence


def extract_evidence(session: Session, settings: Settings, case: MediaCase) -> list[EvidenceItem]:
    correlation_id = str(uuid.uuid4())
    path = _asset_path(case, settings)
    probe = _probe(path)
    _validate_probe(probe, settings)
    output_dir = settings.runtime_root / "media" / case.id / "frames"
    frames = _ocr(path, output_dir)
    asr = _asr(path, case, settings)
    provenance = _c2pa(path)
    evidence = [
        _upsert_evidence(
            session,
            case=case,
            stable_key="asset-probe",
            evidence_type="asset",
            observed_value=probe,
            extractor="ffprobe",
            extractor_version="runtime",
            correlation_id=correlation_id,
        ),
        _upsert_evidence(
            session,
            case=case,
            stable_key="caption",
            evidence_type="caption",
            observed_value={"text": case.caption},
            extractor="platform-metadata",
            extractor_version="fixture-v1",
            correlation_id=correlation_id,
        ),
        _upsert_evidence(
            session,
            case=case,
            stable_key="relationship-metadata",
            evidence_type="relationship_metadata",
            observed_value={"relationship_type": case.relationship_type},
            extractor="platform-metadata",
            extractor_version="fixture-v1",
            correlation_id=correlation_id,
        ),
        _upsert_evidence(
            session,
            case=case,
            stable_key="platform-disclosure-metadata",
            evidence_type="platform_metadata",
            observed_value={"platform_disclosure_flag": case.platform_disclosure_flag},
            extractor="platform-metadata",
            extractor_version="fixture-v1",
            correlation_id=correlation_id,
        ),
        _upsert_evidence(
            session,
            case=case,
            stable_key="aigc-label-metadata",
            evidence_type="aigc_label",
            observed_value={
                "aigc_expected": case.aigc_expected,
                "visible_aigc_label": case.visible_aigc_label,
            },
            extractor="platform-metadata",
            extractor_version="fixture-v1",
            correlation_id=correlation_id,
        ),
        _upsert_evidence(
            session,
            case=case,
            stable_key=f"asr-transcript-{settings.asr_provider}",
            evidence_type="asr",
            observed_value=asr,
            extractor=asr.get("provider", settings.asr_provider),
            extractor_version=str(asr.get("model", "fixture-v1")),
            correlation_id=correlation_id,
            transcript_span={"segments": asr.get("segments", [])},
            confidence=asr.get("language_probability"),
        ),
        _upsert_evidence(
            session,
            case=case,
            stable_key="c2pa-validation-v2",
            evidence_type="c2pa",
            observed_value=provenance,
            extractor="c2pa-python",
            extractor_version=(f"{provenance.get('sdk_version', 'unavailable')}-normalization-v2"),
            correlation_id=correlation_id,
        ),
    ]
    for frame in frames:
        evidence.append(
            _upsert_evidence(
                session,
                case=case,
                stable_key=f"ocr-frame-{frame['frame_index']:03d}",
                evidence_type="ocr",
                observed_value={"text": frame["text"], "status": frame["status"]},
                extractor="tesseract",
                extractor_version="runtime",
                correlation_id=correlation_id,
                timestamp_ms=frame["timestamp_ms"],
                frame_index=frame["frame_index"],
                confidence=None,
            )
        )
    case.status = "analyzed"
    session.commit()
    for item in evidence:
        session.refresh(item)
    return evidence


def _contains_phrase(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    return any(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", lowered) for phrase in DISCLOSURE_PHRASES)


def _control_result(
    control: Control, case: MediaCase, evidence: list[EvidenceItem]
) -> tuple[str, dict, list[str]]:
    by_type: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        by_type.setdefault(item.evidence_type, []).append(item)
    key = control.stable_key
    evidence_ids: list[str] = []
    if key == "commercial_relationship_recorded":
        values = by_type.get("relationship_metadata", [])
        evidence_ids = [item.id for item in values]
        passed = case.relationship_type in {"none", "own_brand", "paid", "affiliate", "free_product"}
        return (
            "pass" if passed else "needs_more_evidence",
            {"observed": case.relationship_type},
            evidence_ids,
        )
    if key == "platform_disclosure_flag_present":
        values = by_type.get("platform_metadata", [])
        evidence_ids = [item.id for item in values]
        if case.relationship_type == "none":
            return (
                "not_applicable",
                {"reason": "no commercial relationship in synthetic metadata"},
                evidence_ids,
            )
        return (
            "pass" if case.platform_disclosure_flag else "issue_candidate",
            {"observed": case.platform_disclosure_flag},
            evidence_ids,
        )
    if key == "visual_disclosure_detected":
        values = by_type.get("ocr", [])
        evidence_ids = [item.id for item in values]
        detected = any(_contains_phrase(str(item.observed_value.get("text", ""))) for item in values)
        return ("pass" if detected else "issue_candidate", {"detected": detected}, evidence_ids)
    if key == "audio_disclosure_detected":
        values = by_type.get("asr", [])
        evidence_ids = [item.id for item in values]
        if not values or values[0].observed_value.get("status") in {"error", "unavailable"}:
            return "needs_more_evidence", {"reason": "ASR unavailable"}, evidence_ids
        detected = _contains_phrase(str(values[0].observed_value.get("text", "")))
        return ("pass" if detected else "issue_candidate", {"detected": detected}, evidence_ids)
    if key == "aigc_visible_label_present":
        values = by_type.get("aigc_label", [])
        evidence_ids = [item.id for item in values]
        if not case.aigc_expected:
            return (
                "not_applicable",
                {"reason": "case is not marked AIGC in synthetic gold data"},
                evidence_ids,
            )
        return (
            "pass" if case.visible_aigc_label else "issue_candidate",
            {"observed": case.visible_aigc_label},
            evidence_ids,
        )
    if key in {"c2pa_manifest_present", "c2pa_validation_status_recorded"}:
        values = by_type.get("c2pa", [])
        evidence_ids = [item.id for item in values]
        observed = values[-1].observed_value if values else {"status": "unavailable"}
        if key == "c2pa_validation_status_recorded":
            return "pass", {"recorded": bool(values), "provenance": observed}, evidence_ids
        if not case.aigc_expected:
            return "not_applicable", {"reason": "case is not marked AIGC"}, evidence_ids
        if observed.get("status") in {"unavailable", "invalid"}:
            return "needs_more_evidence", {"provenance": observed}, evidence_ids
        return "pass", {"provenance": observed}, evidence_ids
    return "needs_more_evidence", {"reason": "control requires human contextual review"}, evidence_ids


def run_approved_controls(session: Session, case: MediaCase) -> tuple[list[TestRun], list[Finding]]:
    mappings = list(
        session.scalars(
            select(RequirementControlMapping).where(RequirementControlMapping.status == "approved")
        )
    )
    eligible: list[tuple[RequirementControlMapping, RequirementCandidate, Control]] = []
    for mapping in mappings:
        requirement = session.get(RequirementCandidate, mapping.requirement_id)
        control = session.get(Control, mapping.control_id)
        if requirement and requirement.status == "approved" and control and control.active:
            eligible.append((mapping, requirement, control))
    if not eligible:
        raise HTTPException(
            status_code=409, detail="No human-approved requirement-control mappings are active"
        )
    evidence = list(
        session.scalars(
            select(EvidenceItem)
            .where(
                EvidenceItem.case_id == case.id,
                EvidenceItem.source_hash == case.asset_sha256,
            )
            .order_by(EvidenceItem.created_at)
        )
    )
    tests: list[TestRun] = []
    findings: list[Finding] = []
    for mapping, requirement, control in eligible:
        existing = session.scalar(
            select(TestRun).where(
                TestRun.case_id == case.id,
                TestRun.mapping_id == mapping.id,
                TestRun.rule_version == control.rule_version,
            )
        )
        if existing:
            tests.append(existing)
            existing_finding = session.scalar(select(Finding).where(Finding.test_run_id == existing.id))
            if existing_finding:
                findings.append(existing_finding)
            continue
        status, result, evidence_ids = _control_result(control, case, evidence)
        correlation_id = str(uuid.uuid4())
        test = TestRun(
            case_id=case.id,
            mapping_id=mapping.id,
            control_id=control.id,
            requirement_id=requirement.id,
            rule_version=control.rule_version,
            status=status,
            result=result,
            evidence_ids=evidence_ids,
            correlation_id=correlation_id,
        )
        session.add(test)
        session.flush()
        tests.append(test)
        if status in {"issue_candidate", "needs_more_evidence"}:
            finding = Finding(
                case_id=case.id,
                test_run_id=test.id,
                requirement_id=requirement.id,
                control_id=control.id,
                evidence_ids=evidence_ids,
                title=(
                    f"Evidence needs review for control: {control.name}"
                    if status == "needs_more_evidence"
                    else f"Control issue candidate: {control.name}"
                ),
                explanation=(
                    "A deterministic test did not find the configured evidence. This is a review candidate, "
                    "not a legal or platform-policy conclusion."
                ),
                uncertainty="Applicability, context, prominence, and extraction errors require human review.",
                status="candidate",
                correlation_id=correlation_id,
            )
            session.add(finding)
            findings.append(finding)
    session.commit()
    for item in [*tests, *findings]:
        session.refresh(item)
    return tests, findings
