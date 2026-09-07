#!/usr/bin/env python3
"""Run a no-persistence Ollama extraction against a current local source snapshot."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from ccg_agent.models import SourceSnapshot  # noqa: E402
from ccg_agent.services.governance import (  # noqa: E402
    request_ollama_extraction,
    validate_extraction_payload,
)
from ccg_agent.settings import Settings  # noqa: E402


def _get_json(client: httpx.Client, url: str) -> Any:
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def _model_digest(client: httpx.Client, ollama_base: str, model: str) -> str | None:
    tags = _get_json(client, f"{ollama_base.rstrip('/')}/api/tags")
    for item in tags.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            return item.get("digest")
    return None


def _bounded_anchor_window(source_key: str, source_text: str, window_chars: int) -> tuple[str, str]:
    fixture_path = ROOT / "fixtures" / "policies" / "verified_requirements.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    requirement = next(
        (item for item in fixture["requirements"] if item["source_key"] == source_key), None
    )
    if requirement is None:
        raise SystemExit(f"No reviewed public anchor exists for source: {source_key}")
    anchor = requirement["exact_quote"]
    pattern = re.compile(r"\s+".join(re.escape(part) for part in anchor.split()))
    match = pattern.search(source_text)
    if match is None:
        raise SystemExit("Reviewed public anchor is not present in the current immutable snapshot")
    offset = match.start()
    before = max(0, window_chars // 3)
    start = max(0, offset - before)
    end = min(len(source_text), start + window_chars)
    start = max(0, end - window_chars)
    return source_text[start:end], anchor


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the local model's strict requirement schema and evidence guards without "
            "creating a requirement candidate or any review state."
        )
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--ollama-base", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="song-local:latest")
    parser.add_argument("--source-key", default="tiktok-commercial-content-disclosure")
    parser.add_argument("--window-chars", type=int, default=4_000)
    parser.add_argument(
        "--full-snapshot",
        action="store_true",
        help="Send the full current snapshot instead of an anchor-assisted bounded window.",
    )
    args = parser.parse_args()

    with httpx.Client(timeout=30) as local_client:
        sources = _get_json(local_client, f"{args.api_base.rstrip('/')}/api/v1/sources")
        source = next((item for item in sources if item["stable_key"] == args.source_key), None)
        if source is None:
            raise SystemExit(f"Source key not found in local registry: {args.source_key}")
        latest = _get_json(
            local_client, f"{args.api_base.rstrip('/')}/api/v1/source-snapshots/latest"
        )
        snapshot_summary = next(
            (item for item in latest if item["source_id"] == source["id"]), None
        )
        if snapshot_summary is None:
            raise SystemExit(f"No local snapshot exists for source: {args.source_key}")
        snapshot_body = _get_json(
            local_client,
            f"{args.api_base.rstrip('/')}/api/v1/source-snapshots/{snapshot_summary['id']}",
        )
        if snapshot_body["fetch_status"] not in {"current", "manual_snapshot"}:
            raise SystemExit(
                "Dry run requires an authoritative current or human-confirmed manual snapshot; "
                f"got {snapshot_body['fetch_status']}"
            )

        settings = Settings(
            project_root=ROOT,
            ollama_base_url=args.ollama_base,
            ollama_model=args.model,
            allow_cloud=False,
        )
        if args.full_snapshot:
            extraction_text = snapshot_body["content_text"]
            anchor = None
            context_strategy = "full-current-snapshot"
        else:
            extraction_text, anchor = _bounded_anchor_window(
                source["stable_key"], snapshot_body["content_text"], args.window_chars
            )
            context_strategy = "reviewed-public-anchor-bounded-current-snapshot"
        payload, metrics = request_ollama_extraction(
            settings,
            source_title=source["title"],
            source_jurisdiction=source["jurisdiction"],
            source_text=extraction_text,
            client=local_client,
        )
        snapshot = SourceSnapshot(
            source_id=source["id"],
            content_hash=snapshot_body["content_hash"],
            content_text=snapshot_body["content_text"],
            locator_map=snapshot_body["locator_map"],
            diff_summary=snapshot_body["diff_summary"],
            fetch_status=snapshot_body["fetch_status"],
        )
        validation = validate_extraction_payload(
            snapshot=snapshot,
            source_jurisdiction=source["jurisdiction"],
            payload=payload,
        )
        passed = bool(
            validation["exact_quote_present"]
            and validation["legal_language_guard_passed"]
            and validation["jurisdiction_matches_source"]
        )
        model_digest = _model_digest(local_client, args.ollama_base, args.model)

    duration_keys = (
        "total_duration",
        "load_duration",
        "prompt_eval_duration",
        "eval_duration",
    )
    normalized_metrics = dict(metrics)
    for key in duration_keys:
        if isinstance(normalized_metrics.get(key), int):
            normalized_metrics[f"{key}_ms"] = round(normalized_metrics.pop(key) / 1_000_000, 3)

    result = {
        "status": "passed" if passed else "failed",
        "source": {
            "stable_key": source["stable_key"],
            "publisher": source["publisher"],
            "source_type": source["source_type"],
            "jurisdiction": source["jurisdiction"],
            "source_status": source["status"],
            "snapshot_id": snapshot_body["id"],
            "snapshot_sha256": snapshot_body["content_hash"],
            "snapshot_fetch_status": snapshot_body["fetch_status"],
        },
        "model": {"name": args.model, "digest": model_digest, "cloud_enabled": False},
        "schema": "requirement-extraction-v1",
        "input_context": {
            "strategy": context_strategy,
            "full_snapshot_characters": len(snapshot_body["content_text"]),
            "model_input_characters": len(extraction_text),
            "reviewed_anchor_present_in_full_snapshot": anchor is None
            or bool(re.compile(r"\s+".join(re.escape(part) for part in anchor.split())).search(
                snapshot_body["content_text"]
            )),
            "autonomous_requirement_discovery": args.full_snapshot,
        },
        "validation": {
            **validation,
            "schema_valid": True,
        },
        "candidate_preview": payload.model_dump(mode="json"),
        "metrics": normalized_metrics,
        "persistence": {
            "database_write": False,
            "candidate_created": False,
            "review_created": False,
            "external_action": False,
        },
        "limitations": [
            "A schema-valid extraction is a model candidate, not an approved requirement.",
            "Exact-quote presence does not validate applicability or legal interpretation.",
            "This command measures one local run and is not a production throughput benchmark.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
