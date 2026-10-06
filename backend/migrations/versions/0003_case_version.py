"""Add optimistic-concurrency version to risk cases.

Revision ID: 0003_case_version
Revises: 0002_case_queue_indexes
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_case_version"
down_revision: str | Sequence[str] | None = "0002_case_queue_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "risk_cases",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("risk_cases", "version")
