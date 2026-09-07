from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.postgres


def _engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL trigger tests")
    return create_engine(url)


def _seed_lineage(connection, *, fetch_status: str = "current") -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    source_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())
    requirement_id = str(uuid.uuid4())
    connection.execute(
        text(
            """
            INSERT INTO sources (
              id, stable_key, publisher, title, official_url, source_type, jurisdiction,
              version, applicable_scope, fetch_mode, redistribution_note, status,
              created_at, updated_at
            ) VALUES (
              :id, :stable_key, 'Test publisher', 'Test source', 'https://example.gov/policy',
              'regulation', 'US', 'test', 'Trigger test only', 'http', 'Test only',
              'current', NOW(), NOW()
            )
            """
        ),
        {"id": source_id, "stable_key": f"trigger-test-{suffix}"},
    )
    connection.execute(
        text(
            """
            INSERT INTO source_snapshots (
              id, source_id, content_hash, content_text, retrieved_at, locator_map,
              diff_summary, fetch_status, immutable, created_at, updated_at
            ) VALUES (
              :id, :source_id, :hash, 'Exact official quote', NOW(), '{}'::jsonb,
              '{}'::jsonb, :fetch_status, TRUE, NOW(), NOW()
            )
            """
        ),
        {
            "id": snapshot_id,
            "source_id": source_id,
            "hash": suffix.ljust(64, "0")[:64],
            "fetch_status": fetch_status,
        },
    )
    connection.execute(
        text(
            """
            INSERT INTO requirement_candidates (
              id, source_snapshot_id, exact_quote, source_locator, actor, trigger,
              required_action, jurisdiction, scope, confidence, uncertainties, status,
              model_provider, model_version, prompt_version, validation, correlation_id,
              created_at, updated_at
            ) VALUES (
              :id, :snapshot_id, 'Exact official quote', 'test', 'provider', 'test trigger',
              'test action', 'US', 'test scope', 1.0, '[]'::jsonb, 'candidate',
              'fixture', 'test', 'test', CAST(:validation AS JSONB),
              :correlation_id, NOW(), NOW()
            )
            """
        ),
        {
            "id": requirement_id,
            "snapshot_id": snapshot_id,
            "correlation_id": str(uuid.uuid4()),
            "validation": '{"exact_quote_present": true}',
        },
    )
    return snapshot_id, requirement_id


def test_database_rejects_non_human_review() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        _, requirement_id = _seed_lineage(connection)
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO requirement_reviews (
                      id, requirement_id, disposition, reviewer_type, reviewer_id,
                      rationale, correlation_id, created_at
                    ) VALUES (
                      :id, :requirement_id, 'approved', 'model', 'test-model',
                      'attempted self approval', :correlation_id, NOW()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "requirement_id": requirement_id,
                    "correlation_id": str(uuid.uuid4()),
                },
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_rejects_short_review_rationale_and_has_all_rationale_constraints() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        constraint_names = set(
            connection.execute(
                text(
                    """
                    SELECT conname
                    FROM pg_constraint
                    WHERE conname IN (
                      'ck_requirement_reviews_rationale_min_20',
                      'ck_mapping_candidates_rationale_min_20',
                      'ck_mapping_reviews_rationale_min_20',
                      'ck_finding_reviews_rationale_min_20'
                    )
                    """
                )
            ).scalars()
        )
        assert constraint_names == {
            "ck_requirement_reviews_rationale_min_20",
            "ck_mapping_candidates_rationale_min_20",
            "ck_mapping_reviews_rationale_min_20",
            "ck_finding_reviews_rationale_min_20",
        }
        _, requirement_id = _seed_lineage(connection)
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO requirement_reviews (
                      id, requirement_id, disposition, reviewer_type, reviewer_id,
                      rationale, correlation_id, created_at
                    ) VALUES (
                      :id, :requirement_id, 'needs_more_evidence', 'human', 'Song',
                      'too short', :correlation_id, NOW()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "requirement_id": requirement_id,
                    "correlation_id": str(uuid.uuid4()),
                },
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_rejects_source_snapshot_mutation() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        snapshot_id, _ = _seed_lineage(connection)
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text("UPDATE source_snapshots SET content_text = 'changed' WHERE id = :id"),
                {"id": snapshot_id},
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_rejects_approval_from_public_test_fixture() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        _, requirement_id = _seed_lineage(connection, fetch_status="public_test_fixture")
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO requirement_reviews (
                      id, requirement_id, disposition, reviewer_type, reviewer_id,
                      rationale, correlation_id, created_at
                    ) VALUES (
                      :id, :requirement_id, 'approved', 'human', 'Song',
                      'Fixture evidence cannot authorize an operational rule', :correlation_id, NOW()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "requirement_id": requirement_id,
                    "correlation_id": str(uuid.uuid4()),
                },
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_rejects_approval_from_superseded_authoritative_snapshot() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        snapshot_id, requirement_id = _seed_lineage(connection)
        source_id = connection.execute(
            text("SELECT source_id FROM source_snapshots WHERE id = :id"),
            {"id": snapshot_id},
        ).scalar_one()
        suffix = uuid.uuid4().hex
        connection.execute(
            text(
                """
                INSERT INTO source_snapshots (
                  id, source_id, content_hash, content_text, retrieved_at, locator_map,
                  diff_summary, fetch_status, immutable, created_at, updated_at
                ) VALUES (
                  :id, :source_id, :hash, 'Newer official source text',
                  NOW() + INTERVAL '1 second', '{}'::jsonb, '{}'::jsonb,
                  'current', TRUE, NOW() + INTERVAL '1 second', NOW() + INTERVAL '1 second'
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "hash": suffix.ljust(64, "0")[:64],
            },
        )
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO requirement_reviews (
                      id, requirement_id, disposition, reviewer_type, reviewer_id,
                      rationale, correlation_id, created_at
                    ) VALUES (
                      :id, :requirement_id, 'approved', 'human', 'Song',
                      'Superseded source evidence must not authorize approval',
                      :correlation_id, NOW()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "requirement_id": requirement_id,
                    "correlation_id": str(uuid.uuid4()),
                },
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_rejects_approval_when_source_refresh_is_not_fresh() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        snapshot_id, requirement_id = _seed_lineage(connection)
        connection.execute(
            text(
                """
                UPDATE sources
                SET status = 'fetch_error'
                WHERE id = (SELECT source_id FROM source_snapshots WHERE id = :snapshot_id)
                """
            ),
            {"snapshot_id": snapshot_id},
        )
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    """
                    INSERT INTO requirement_reviews (
                      id, requirement_id, disposition, reviewer_type, reviewer_id,
                      rationale, correlation_id, created_at
                    ) VALUES (
                      :id, :requirement_id, 'approved', 'human', 'Song',
                      'A failed source refresh must block a new approval',
                      :correlation_id, NOW()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "requirement_id": requirement_id,
                    "correlation_id": str(uuid.uuid4()),
                },
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_rejects_requirement_status_change_without_review() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        _, requirement_id = _seed_lineage(connection)
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "UPDATE requirement_candidates SET status = 'approved' WHERE id = :id"
                ),
                {"id": requirement_id},
            )
        savepoint.rollback()
    finally:
        outer.rollback()
        connection.close()


def test_database_allows_authoritative_human_review_transition() -> None:
    engine = _engine()
    connection = engine.connect()
    outer = connection.begin()
    try:
        _, requirement_id = _seed_lineage(connection)
        connection.execute(
            text(
                """
                INSERT INTO requirement_reviews (
                  id, requirement_id, disposition, reviewer_type, reviewer_id,
                  rationale, correlation_id, created_at
                ) VALUES (
                  :id, :requirement_id, 'approved', 'human', 'Song',
                  'Authoritative test approval', :correlation_id, NOW()
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "requirement_id": requirement_id,
                "correlation_id": str(uuid.uuid4()),
            },
        )
        connection.execute(
            text("UPDATE requirement_candidates SET status = 'approved' WHERE id = :id"),
            {"id": requirement_id},
        )
        assert (
            connection.execute(
                text("SELECT status FROM requirement_candidates WHERE id = :id"),
                {"id": requirement_id},
            ).scalar_one()
            == "approved"
        )
    finally:
        outer.rollback()
        connection.close()
