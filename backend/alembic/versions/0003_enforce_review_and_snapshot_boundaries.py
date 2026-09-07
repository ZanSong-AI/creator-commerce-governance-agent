"""enforce review and immutable snapshot boundaries

Revision ID: 0003
Revises: 2ba60b8764e9
Create Date: 2026-08-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "2ba60b8764e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_requirement_status",
        "requirement_candidates",
        "status IN ('candidate', 'approved', 'rejected', 'superseded', 'needs_more_evidence')",
    )
    op.create_check_constraint(
        "ck_mapping_status",
        "requirement_control_mappings",
        "status IN ('candidate', 'approved', 'rejected', 'superseded')",
    )
    op.create_check_constraint(
        "ck_finding_status",
        "findings",
        "status IN ('candidate', 'confirmed_control_issue', 'dismissed', "
        "'not_applicable', 'needs_more_evidence')",
    )
    op.execute(
        """
        CREATE FUNCTION ccg_require_human_review() RETURNS trigger AS $$
        BEGIN
            IF NEW.reviewer_type <> 'human' THEN
                RAISE EXCEPTION 'Only a human reviewer can create a review record';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("requirement_reviews", "mapping_reviews", "finding_reviews"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_human_only
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION ccg_require_human_review();
            """
        )
    op.execute(
        """
        CREATE FUNCTION ccg_immutable_source_snapshot() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Source snapshots are immutable; create a new version';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_source_snapshots_immutable
        BEFORE UPDATE OR DELETE ON source_snapshots
        FOR EACH ROW EXECUTE FUNCTION ccg_immutable_source_snapshot();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_source_snapshots_immutable ON source_snapshots")
    op.execute("DROP FUNCTION IF EXISTS ccg_immutable_source_snapshot")
    for table in ("requirement_reviews", "mapping_reviews", "finding_reviews"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_human_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS ccg_require_human_review")
    op.drop_constraint("ck_finding_status", "findings", type_="check")
    op.drop_constraint("ck_mapping_status", "requirement_control_mappings", type_="check")
    op.drop_constraint("ck_requirement_status", "requirement_candidates", type_="check")
