#!/usr/bin/env python3
"""Generate a deterministic synthetic creator-commerce governance event stream."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

NAMESPACE = uuid.UUID("cc61a7aa-7aba-5a8e-9d96-0acac1d2ed4b")
RELATIONSHIPS = ["none", "own_brand", "paid", "affiliate", "free_product"]
JURISDICTIONS = ["US", "US", "US", "EU", "EU", "CA"]
EVENT_TYPES = ["content_created", "metadata_recorded", "analysis_completed", "finding_created", "reviewed"]


def stable_id(seed: int, kind: str, value: int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{seed}:{kind}:{value}"))


def build_event(index: int, seed: int, rng: random.Random) -> dict:
    relationship = RELATIONSHIPS[index % len(RELATIONSHIPS)]
    jurisdiction = JURISDICTIONS[index % len(JURISDICTIONS)]
    event_type = EVENT_TYPES[index % len(EVENT_TYPES)]
    promotional = relationship != "none"
    disclosure_flag = promotional and index % 7 not in {0, 1}
    aigc_flag = index % 4 in {0, 1}
    analysis_status = "needs_more_evidence" if index % 23 == 0 else "completed"
    finding_status = None
    disposition = None
    if event_type in {"finding_created", "reviewed"}:
        finding_status = "candidate" if (promotional and not disclosure_flag) else "none"
    if event_type == "reviewed":
        if finding_status == "candidate":
            disposition = ["confirmed_control_issue", "dismissed", "needs_more_evidence"][index % 3]
        else:
            disposition = "not_applicable"
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index * 7)
    latency = max(12, int(rng.lognormvariate(6.0, 0.55)))
    return {
        "event_id": stable_id(seed, "event", index),
        "content_id": stable_id(seed, "content", index % 50_000),
        "creator_id": stable_id(seed, "creator", index % 10_000),
        "merchant_id": stable_id(seed, "merchant", index % 2_000),
        "campaign_id": stable_id(seed, "campaign", index % 5_000),
        "jurisdiction": jurisdiction,
        "event_type": event_type,
        "event_timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "relationship_type": relationship,
        "disclosure_flag": disclosure_flag,
        "aigc_flag": aigc_flag,
        "analysis_status": analysis_status,
        "finding_status": finding_status,
        "review_disposition": disposition,
        "processing_latency_ms": latency,
        "payload": {
            "synthetic": True,
            "generator_version": "2026-08-27.v1",
            "external_action": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()
    if args.count < 1:
        raise SystemExit("count must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    digest = hashlib.sha256()
    jurisdictions: Counter[str] = Counter()
    event_types: Counter[str] = Counter()
    dispositions: Counter[str] = Counter()
    latency_total = 0
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for index in range(args.count):
            event = build_event(index, args.seed, rng)
            line = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
            stream.write(line)
            digest.update(line.encode("utf-8"))
            jurisdictions[event["jurisdiction"]] += 1
            event_types[event["event_type"]] += 1
            if event["review_disposition"]:
                dispositions[event["review_disposition"]] += 1
            latency_total += event["processing_latency_ms"]
    totals = {
        "dataset_version": "governance-events-2026-08-27.v1",
        "seed": args.seed,
        "row_count": args.count,
        "logical_sha256": digest.hexdigest(),
        "jurisdiction_counts": dict(sorted(jurisdictions.items())),
        "event_type_counts": dict(sorted(event_types.items())),
        "review_disposition_counts": dict(sorted(dispositions.items())),
        "processing_latency_ms_total": latency_total,
        "notice": "Synthetic events; not a measurement of TikTok risk, revenue, or ROI.",
    }
    totals_path = args.output.with_suffix(args.output.suffix + ".control-totals.json")
    totals_path.write_text(json.dumps(totals, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
