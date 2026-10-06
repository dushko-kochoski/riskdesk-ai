"""Add indexes for the server-side case queue filters.

Revision ID: 0002_case_queue_indexes
Revises: 0001_initial_schema
Create Date: 2026-10-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_case_queue_indexes"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_risk_cases_recommended_action",
        "risk_cases",
        ["recommended_action"],
        unique=False,
    )
    op.create_index(
        "ix_risk_cases_queue",
        "risk_cases",
        ["status", "risk_level", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_risk_cases_queue", table_name="risk_cases")
    op.drop_index("ix_risk_cases_recommended_action", table_name="risk_cases")
