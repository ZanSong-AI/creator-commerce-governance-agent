"""require authoritative evidence and a review row for requirement disposition

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION ccg_authoritative_requirement_approval() RETURNS trigger AS $$
        BEGIN
            IF NEW.disposition = 'approved' AND NOT EXISTS (
                SELECT 1
                FROM requirement_candidates requirement
                JOIN source_snapshots snapshot
                  ON snapshot.id = requirement.source_snapshot_id
                WHERE requirement.id = NEW.requirement_id
                  AND snapshot.fetch_status IN ('current', 'manual_snapshot')
            ) THEN
                RAISE EXCEPTION
                  'Requirement approval requires a current or human-confirmed source snapshot';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_requirement_reviews_authoritative
        BEFORE INSERT OR UPDATE ON requirement_reviews
        FOR EACH ROW EXECUTE FUNCTION ccg_authoritative_requirement_approval();
        """
    )
    op.execute(
        """
        CREATE FUNCTION ccg_requirement_status_requires_review() RETURNS trigger AS $$
        BEGIN
            IF NEW.status IS DISTINCT FROM OLD.status
               AND NEW.status IN ('approved', 'rejected', 'needs_more_evidence')
               AND NOT EXISTS (
                   SELECT 1 FROM requirement_reviews review
                   WHERE review.requirement_id = NEW.id
                     AND review.disposition = NEW.status
                     AND review.reviewer_type = 'human'
               ) THEN
                RAISE EXCEPTION 'Requirement disposition requires a matching human review record';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_requirement_status_requires_review
        BEFORE UPDATE OF status ON requirement_candidates
        FOR EACH ROW EXECUTE FUNCTION ccg_requirement_status_requires_review();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_requirement_status_requires_review ON requirement_candidates"
    )
    op.execute("DROP FUNCTION IF EXISTS ccg_requirement_status_requires_review")
    op.execute("DROP TRIGGER IF EXISTS trg_requirement_reviews_authoritative ON requirement_reviews")
    op.execute("DROP FUNCTION IF EXISTS ccg_authoritative_requirement_approval")
