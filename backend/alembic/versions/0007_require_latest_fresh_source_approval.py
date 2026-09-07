"""require latest fresh source evidence for requirement approval

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ccg_authoritative_requirement_approval() RETURNS trigger AS $$
        BEGIN
            IF NEW.disposition = 'approved' AND NOT EXISTS (
                SELECT 1
                FROM requirement_candidates requirement
                JOIN source_snapshots snapshot
                  ON snapshot.id = requirement.source_snapshot_id
                JOIN sources source
                  ON source.id = snapshot.source_id
                WHERE requirement.id = NEW.requirement_id
                  AND snapshot.fetch_status IN ('current', 'manual_snapshot')
                  AND source.status IN ('current', 'changed')
                  AND snapshot.id = (
                      SELECT latest.id
                      FROM source_snapshots latest
                      WHERE latest.source_id = source.id
                        AND latest.fetch_status IN ('current', 'manual_snapshot')
                      ORDER BY latest.retrieved_at DESC, latest.created_at DESC, latest.id DESC
                      LIMIT 1
                  )
            ) THEN
                RAISE EXCEPTION
                  'Requirement approval requires the latest authoritative snapshot and fresh source status';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ccg_authoritative_requirement_approval() RETURNS trigger AS $$
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
