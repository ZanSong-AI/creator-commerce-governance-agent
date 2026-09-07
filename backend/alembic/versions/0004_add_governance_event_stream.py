"""add synthetic governance event stream

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commerce_governance_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("merchant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("jurisdiction", sa.String(length=40), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("disclosure_flag", sa.Boolean(), nullable=False),
        sa.Column("aigc_flag", sa.Boolean(), nullable=False),
        sa.Column("analysis_status", sa.String(length=40), nullable=False),
        sa.Column("finding_status", sa.String(length=50), nullable=True),
        sa.Column("review_disposition", sa.String(length=50), nullable=True),
        sa.Column("processing_latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_governance_events_jurisdiction_type",
        "commerce_governance_events",
        ["jurisdiction", "event_type"],
    )
    op.create_index(
        "ix_governance_events_disposition",
        "commerce_governance_events",
        ["review_disposition"],
    )
    op.create_index(
        "ix_governance_events_timestamp",
        "commerce_governance_events",
        ["event_timestamp"],
    )
    op.create_index(
        "ix_commerce_governance_events_content_id",
        "commerce_governance_events",
        ["content_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_commerce_governance_events_content_id", table_name="commerce_governance_events")
    op.drop_index("ix_governance_events_timestamp", table_name="commerce_governance_events")
    op.drop_index("ix_governance_events_disposition", table_name="commerce_governance_events")
    op.drop_index("ix_governance_events_jurisdiction_type", table_name="commerce_governance_events")
    op.drop_table("commerce_governance_events")
