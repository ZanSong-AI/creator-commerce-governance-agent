from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Control,
    EvidenceItem,
    Finding,
    FindingReview,
    MediaCase,
    ReportExport,
    RequirementCandidate,
    RequirementControlMapping,
    Source,
    SourceSnapshot,
    TestRun,
)
from ..settings import Settings


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def build_lineage_manifest(session: Session, case: MediaCase) -> dict[str, Any]:
    evidence = list(
        session.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.case_id == case.id, EvidenceItem.source_hash == case.asset_sha256)
            .order_by(EvidenceItem.evidence_type, EvidenceItem.stable_key)
        )
    )
    tests = list(session.scalars(select(TestRun).where(TestRun.case_id == case.id)))
    findings = list(session.scalars(select(Finding).where(Finding.case_id == case.id)))
    lineage: list[dict[str, Any]] = []
    for finding in findings:
        test = session.get(TestRun, finding.test_run_id)
        mapping = session.get(RequirementControlMapping, test.mapping_id) if test else None
        control = session.get(Control, finding.control_id)
        requirement = session.get(RequirementCandidate, finding.requirement_id)
        snapshot = session.get(SourceSnapshot, requirement.source_snapshot_id) if requirement else None
        source = session.get(Source, snapshot.source_id) if snapshot else None
        reviews = list(
            session.scalars(
                select(FindingReview)
                .where(FindingReview.finding_id == finding.id)
                .order_by(FindingReview.created_at)
            )
        )
        lineage.append(
            {
                "finding": {
                    "id": finding.id,
                    "title": finding.title,
                    "status": finding.status,
                    "explanation": finding.explanation,
                    "uncertainty": finding.uncertainty,
                },
                "human_reviews": [
                    {
                        "disposition": review.disposition,
                        "reviewer_id": review.reviewer_id,
                        "rationale": review.rationale,
                        "created_at": review.created_at,
                    }
                    for review in reviews
                ],
                "test": {
                    "id": test.id,
                    "status": test.status,
                    "rule_version": test.rule_version,
                    "result": test.result,
                }
                if test
                else None,
                "mapping": {
                    "id": mapping.id,
                    "status": mapping.status,
                    "rationale": mapping.rationale,
                }
                if mapping
                else None,
                "control": {
                    "id": control.id,
                    "stable_key": control.stable_key,
                    "name": control.name,
                    "rule_version": control.rule_version,
                }
                if control
                else None,
                "requirement": {
                    "id": requirement.id,
                    "status": requirement.status,
                    "exact_quote": requirement.exact_quote,
                    "source_locator": requirement.source_locator,
                }
                if requirement
                else None,
                "source_snapshot": {
                    "id": snapshot.id,
                    "content_hash": snapshot.content_hash,
                    "retrieved_at": snapshot.retrieved_at,
                    "fetch_status": snapshot.fetch_status,
                }
                if snapshot
                else None,
                "source": {
                    "id": source.id,
                    "publisher": source.publisher,
                    "title": source.title,
                    "official_url": source.official_url,
                    "jurisdiction": source.jurisdiction,
                    "version": source.version,
                }
                if source
                else None,
            }
        )
    manifest = {
        "manifest_version": "audit-lineage-2026-08-27.v1",
        "generated_at": datetime.now().astimezone(),
        "legal_conclusion": None,
        "external_action": None,
        "case": {
            "id": case.id,
            "stable_key": case.stable_key,
            "asset_sha256": case.asset_sha256,
            "jurisdiction": case.jurisdiction,
            "relationship_type": case.relationship_type,
            "status": case.status,
        },
        "package_status": ("reviewed_control_results" if tests else "evidence_only_no_approved_rule_result"),
        "warnings": [
            "This package records evidence and governance workflow state; it is not legal advice.",
            "Candidate findings are not compliance or legal determinations.",
            "C2PA validity does not establish that media is true, lawful, or compliant.",
        ],
        "evidence": [
            {
                "id": item.id,
                "stable_key": item.stable_key,
                "type": item.evidence_type,
                "observed_value": item.observed_value,
                "timestamp_ms": item.timestamp_ms,
                "frame_index": item.frame_index,
                "extractor": item.extractor,
                "extractor_version": item.extractor_version,
                "source_hash": item.source_hash,
            }
            for item in evidence
        ],
        "lineage": lineage,
    }
    return json.loads(json.dumps(manifest, ensure_ascii=False, default=_json_default))


def _as_html(manifest: dict[str, Any]) -> bytes:
    case = manifest["case"]
    evidence_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item['type']))}</td>"
        f"<td>{html.escape(str(item['stable_key']))}</td>"
        f"<td><pre>{html.escape(json.dumps(item['observed_value'], ensure_ascii=False))}</pre></td>"
        f"<td>{html.escape(str(item['extractor']))}</td>"
        "</tr>"
        for item in manifest["evidence"]
    )
    finding_rows = (
        "".join(
            "<tr>"
            f"<td>{html.escape(str(item['finding']['title']))}</td>"
            f"<td>{html.escape(str(item['finding']['status']))}</td>"
            f"<td>{html.escape(str(item['finding']['uncertainty']))}</td>"
            "</tr>"
            for item in manifest["lineage"]
        )
        or '<tr><td colspan="3">No approved-rule finding exists for this case.</td></tr>'
    )
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in manifest["warnings"])
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Audit evidence package</title>
<style>
body{{font:14px system-ui;margin:40px;color:#17202a}}
table{{border-collapse:collapse;width:100%;margin:16px 0}}
th,td{{border:1px solid #ccd2d8;padding:8px;text-align:left;vertical-align:top}}
pre{{white-space:pre-wrap;max-width:720px}}
.notice{{background:#fff5d6;padding:12px;border-left:4px solid #c58b00}}
</style></head>
<body><h1>Creator Commerce Governance — Audit Evidence Package</h1>
<div class="notice">Evidence-bound review artifact. Not legal advice and not an external submission.</div>
<h2>Case</h2><dl><dt>Stable key</dt><dd>{html.escape(str(case["stable_key"]))}</dd>
<dt>Asset SHA-256</dt><dd>{html.escape(str(case["asset_sha256"]))}</dd>
<dt>Package status</dt><dd>{html.escape(str(manifest["package_status"]))}</dd></dl>
<h2>Findings and review state</h2>
<table><thead><tr><th>Finding</th><th>Status</th><th>Uncertainty</th></tr></thead>
<tbody>{finding_rows}</tbody></table>
<h2>Current evidence</h2>
<table><thead><tr><th>Type</th><th>Key</th><th>Observed value</th><th>Extractor</th></tr></thead>
<tbody>{evidence_rows}</tbody></table>
<h2>Boundaries</h2><ul>{warnings}</ul>
</body></html>"""
    return document.encode("utf-8")


def _as_csv(manifest: dict[str, Any]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_stable_key",
            "evidence_id",
            "evidence_type",
            "stable_key",
            "observed_value_json",
            "timestamp_ms",
            "frame_index",
            "extractor",
            "extractor_version",
            "source_hash",
        ],
    )
    writer.writeheader()
    for item in manifest["evidence"]:
        writer.writerow(
            {
                "case_stable_key": manifest["case"]["stable_key"],
                "evidence_id": item["id"],
                "evidence_type": item["type"],
                "stable_key": item["stable_key"],
                "observed_value_json": json.dumps(item["observed_value"], ensure_ascii=False),
                "timestamp_ms": item["timestamp_ms"],
                "frame_index": item["frame_index"],
                "extractor": item["extractor"],
                "extractor_version": item["extractor_version"],
                "source_hash": item["source_hash"],
            }
        )
    return output.getvalue().encode("utf-8")


def _as_pdf(manifest: dict[str, Any]) -> bytes:
    """Render the review manifest as a human-readable evidence package."""
    case = manifest["case"]
    output = io.BytesIO()
    navy = colors.HexColor("#14213D")
    blue = colors.HexColor("#2563EB")
    pale_blue = colors.HexColor("#EFF6FF")
    pale_amber = colors.HexColor("#FFF7E6")
    border = colors.HexColor("#CBD5E1")
    ink = colors.HexColor("#172033")
    muted = colors.HexColor("#566174")

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "AuditTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=navy,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    kicker = ParagraphStyle(
        "Kicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=blue,
        spaceAfter=7,
    )
    subtitle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=muted,
        spaceAfter=14,
    )
    heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=navy,
        spaceBefore=12,
        spaceAfter=7,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
        textColor=ink,
    )
    small = ParagraphStyle(
        "Small",
        parent=body,
        fontSize=7.3,
        leading=9.4,
    )
    label = ParagraphStyle(
        "Label",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=muted,
    )
    notice = ParagraphStyle(
        "Notice",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#7C4A03"),
    )

    doc = BaseDocTemplate(
        output,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title="Creator Commerce Governance Audit Evidence Package",
        author="Creator Commerce Governance Agent",
        subject="Evidence-bound human review artifact",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")

    def page_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(border)
        canvas.line(doc.leftMargin, 0.44 * inch, letter[0] - doc.rightMargin, 0.44 * inch)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(muted)
        canvas.drawString(doc.leftMargin, 0.27 * inch, "Evidence-bound review artifact · Not legal advice")
        canvas.drawRightString(
            letter[0] - doc.rightMargin,
            0.27 * inch,
            f"{case['stable_key']}  ·  Page {document.page}",
        )
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="audit", frames=[frame], onPage=page_footer)])

    def p(value: Any, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(html.escape(str(value)), style)

    generated = str(manifest.get("generated_at", "unknown"))
    story: list[Any] = [
        Paragraph("CREATOR COMMERCE GOVERNANCE", kicker),
        Paragraph("Audit Evidence Package", title),
        Paragraph(
            "A reviewable record of extracted media evidence, deterministic test state, "
            "and human governance lineage.",
            subtitle,
        ),
    ]

    notice_table = Table(
        [[Paragraph("REVIEW BOUNDARY", label), p(manifest["warnings"][0], notice)]],
        colWidths=[1.05 * inch, 5.95 * inch],
    )
    notice_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale_amber),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E3A008")),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([notice_table, Paragraph("Package summary", heading)])

    summary_data = [
        [p("Case", label), p(case["stable_key"]), p("Jurisdiction", label), p(case["jurisdiction"])],
        [p("Package status", label), p(manifest["package_status"]), p("Generated", label), p(generated)],
        [
            p("Evidence items", label),
            p(len(manifest["evidence"])),
            p("Lineage entries", label),
            p(len(manifest["lineage"])),
        ],
        [p("Legal conclusion", label), p("None"), p("External action", label), p("None")],
    ]
    summary = Table(summary_data, colWidths=[1.05 * inch, 2.45 * inch, 1.05 * inch, 2.45 * inch])
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale_blue),
                ("GRID", (0, 0), (-1, -1), 0.45, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([summary, Paragraph("Asset identity", heading)])
    identity = Table(
        [
            [p("Stable key", label), p(case["stable_key"], small)],
            [p("SHA-256", label), p(case["asset_sha256"], small)],
            [p("Relationship", label), p(case["relationship_type"], small)],
            [p("Case status", label), p(case["status"], small)],
        ],
        colWidths=[1.05 * inch, 5.95 * inch],
    )
    identity.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(identity)

    story.append(Paragraph("Evidence inventory", heading))
    evidence_rows = [
        [p("Type", label), p("Stable key", label), p("Observed value", label), p("Extractor", label)]
    ]
    for item in manifest["evidence"]:
        observed = json.dumps(item["observed_value"], ensure_ascii=False, separators=(",", ":"))
        if len(observed) > 260:
            observed = observed[:257] + "..."
        evidence_rows.append(
            [
                p(item["type"], small),
                p(item["stable_key"], small),
                p(observed, small),
                p(f"{item['extractor']}\n{item['extractor_version']}", small),
            ]
        )
    evidence_table = Table(
        evidence_rows,
        colWidths=[0.88 * inch, 1.55 * inch, 3.42 * inch, 1.15 * inch],
        repeatRows=1,
    )
    evidence_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, border),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(evidence_table)

    story.append(Paragraph("Finding and review lineage", heading))
    if manifest["lineage"]:
        lineage_rows = [[p("Finding", label), p("Status", label), p("Control / requirement", label)]]
        for item in manifest["lineage"]:
            control = item.get("control") or {}
            requirement = item.get("requirement") or {}
            lineage_rows.append(
                [
                    p(item["finding"]["title"], small),
                    p(item["finding"]["status"], small),
                    p(f"{control.get('stable_key', 'n/a')} / {requirement.get('id', 'n/a')}", small),
                ]
            )
        lineage_table = Table(lineage_rows, colWidths=[2.65 * inch, 1.3 * inch, 3.05 * inch], repeatRows=1)
        lineage_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, border),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(lineage_table)
    else:
        story.append(
            KeepTogether(
                [
                    Table(
                        [
                            [
                                p("NO ACTIVE RULE RESULT", label),
                                p(
                                    "No approved requirement-control mapping existed when this "
                                    "package was generated.",
                                    body,
                                ),
                            ]
                        ],
                        colWidths=[1.45 * inch, 5.55 * inch],
                        style=TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                                ("BOX", (0, 0), (-1, -1), 0.5, border),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                ("TOPPADDING", (0, 0), (-1, -1), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                            ]
                        ),
                    )
                ]
            )
        )

    story.extend([Paragraph("Interpretation boundaries", heading)])
    for warning in manifest["warnings"]:
        story.extend([p(f"• {warning}", body), Spacer(1, 3)])
    story.append(Spacer(1, 7))
    story.append(
        Paragraph(
            "Manifest version: " + html.escape(str(manifest["manifest_version"])),
            ParagraphStyle("Manifest", parent=small, alignment=TA_CENTER, textColor=muted),
        )
    )
    doc.build(story)
    return output.getvalue()


def export_report(
    session: Session,
    settings: Settings,
    *,
    case: MediaCase,
    formats: list[str],
) -> list[ReportExport]:
    allowed = {"html", "pdf", "json", "csv"}
    requested = list(dict.fromkeys(formats))
    if any(fmt not in allowed for fmt in requested):
        raise HTTPException(status_code=422, detail="Unsupported report format")
    manifest = build_lineage_manifest(session, case)
    export_root = settings.runtime_root / "reports" / case.stable_key
    export_root.mkdir(parents=True, exist_ok=True)
    correlation_id = str(uuid.uuid4())
    result: list[ReportExport] = []
    for fmt in requested:
        if fmt == "html":
            content = _as_html(manifest)
        elif fmt == "csv":
            content = _as_csv(manifest)
        elif fmt == "pdf":
            content = _as_pdf(manifest)
        else:
            content = json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default).encode(
                "utf-8"
            )
        digest = hashlib.sha256(content).hexdigest()
        path = export_root / f"audit-package-{digest[:12]}.{fmt}"
        path.write_bytes(content)
        record = ReportExport(
            case_id=case.id,
            format=fmt,
            file_path=str(path.relative_to(settings.project_root)),
            content_hash=digest,
            lineage_manifest=manifest,
            correlation_id=correlation_id,
        )
        session.add(record)
        result.append(record)
    session.commit()
    for record in result:
        session.refresh(record)
    return result
