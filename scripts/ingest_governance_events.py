#!/usr/bin/env python3
"""Idempotently ingest the synthetic event stream into PostgreSQL and verify totals."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

INSERT = """
INSERT INTO commerce_governance_events (
  event_id, content_id, creator_id, merchant_id, campaign_id, jurisdiction,
  event_type, event_timestamp, relationship_type, disclosure_flag, aigc_flag,
  analysis_status, finding_status, review_disposition, processing_latency_ms, payload, ingested_at
) VALUES (
  %(event_id)s, %(content_id)s, %(creator_id)s, %(merchant_id)s, %(campaign_id)s, %(jurisdiction)s,
  %(event_type)s, %(event_timestamp)s, %(relationship_type)s, %(disclosure_flag)s, %(aigc_flag)s,
  %(analysis_status)s, %(finding_status)s, %(review_disposition)s, %(processing_latency_ms)s,
  %(payload)s, NOW()
) ON CONFLICT (event_id) DO NOTHING
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=2_000)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    totals = json.loads(args.input.with_suffix(args.input.suffix + ".control-totals.json").read_text())
    inserted = 0
    batch: list[dict] = []
    with psycopg.connect(database_url) as connection, args.input.open(encoding="utf-8") as stream:
        with connection.cursor() as cursor:
            for line in stream:
                event = json.loads(line)
                event["payload"] = Jsonb(event["payload"])
                batch.append(event)
                if len(batch) >= args.batch_size:
                    cursor.executemany(INSERT, batch)
                    inserted += cursor.rowcount
                    batch.clear()
            if batch:
                cursor.executemany(INSERT, batch)
                inserted += cursor.rowcount
            connection.commit()
            cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(processing_latency_ms), 0) "
                "FROM commerce_governance_events"
            )
            database_rows, latency_total = cursor.fetchone()
    if database_rows != totals["row_count"] or latency_total != totals["processing_latency_ms_total"]:
        raise SystemExit(
            f"control total mismatch: database_rows={database_rows}, expected={totals['row_count']}, "
            f"latency={latency_total}, expected_latency={totals['processing_latency_ms_total']}"
        )
    print(
        json.dumps(
            {
                "inserted_this_run": inserted,
                "database_rows": database_rows,
                "processing_latency_ms_total": latency_total,
                "control_totals_match": True,
            }
        )
    )


if __name__ == "__main__":
    main()
