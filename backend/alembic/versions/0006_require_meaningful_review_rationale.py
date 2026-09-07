"""require meaningful rationale for governance candidates and reviews

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_requirement_reviews_rationale_min_20",
        "requirement_reviews",
        "length(trim(rationale)) >= 20",
    )
    op.create_check_constraint(
        "ck_mapping_candidates_rationale_min_20",
        "requirement_control_mappings",
        "length(trim(rationale)) >= 20",
    )
    op.create_check_constraint(
        "ck_mapping_reviews_rationale_min_20",
        "mapping_reviews",
        "length(trim(rationale)) >= 20",
    )
    op.create_check_constraint(
        "ck_finding_reviews_rationale_min_20",
        "finding_reviews",
        "length(trim(rationale)) >= 20",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_finding_reviews_rationale_min_20", "finding_reviews", type_="check"
    )
    op.drop_constraint(
        "ck_mapping_reviews_rationale_min_20", "mapping_reviews", type_="check"
    )
    op.drop_constraint(
        "ck_mapping_candidates_rationale_min_20",
        "requirement_control_mappings",
        type_="check",
    )
    op.drop_constraint(
        "ck_requirement_reviews_rationale_min_20",
        "requirement_reviews",
        type_="check",
    )
