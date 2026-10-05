"""Create the existing RiskDesk schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("player_id", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("kyc_status", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("country", "device_id", "event_type", "id", "kyc_status", "player_id"):
        op.create_index(f"ix_events_{column}", "events", [column], unique=False)

    op.create_table(
        "risk_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(length=100), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("recommended_action", sa.String(length=50), nullable=False),
        sa.Column("triggered_rules", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("event_id", "id", "player_id", "risk_level", "status"):
        op.create_index(f"ix_risk_cases_{column}", "risk_cases", [column], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("action", "created_at", "entity_id", "entity_type", "id"):
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column], unique=False)


def downgrade() -> None:
    for column in ("id", "entity_type", "entity_id", "created_at", "action"):
        op.drop_index(f"ix_audit_logs_{column}", table_name="audit_logs")
    op.drop_table("audit_logs")

    for column in ("status", "risk_level", "player_id", "id", "event_id"):
        op.drop_index(f"ix_risk_cases_{column}", table_name="risk_cases")
    op.drop_table("risk_cases")

    for column in ("player_id", "kyc_status", "id", "event_type", "device_id", "country"):
        op.drop_index(f"ix_events_{column}", table_name="events")
    op.drop_table("events")
