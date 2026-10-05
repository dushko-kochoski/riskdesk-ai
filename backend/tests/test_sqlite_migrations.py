import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_existing_sqlite_database_can_be_adopted_without_losing_data(tmp_path) -> None:
    database_path = tmp_path / "existing-riskdesk.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    previous_url = os.environ.get("RISKDESK_MIGRATION_DATABASE_URL")
    os.environ["RISKDESK_MIGRATION_DATABASE_URL"] = database_url
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    try:
        command.upgrade(config, "0001_initial_schema")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO events (
                        id, event_type, player_id, amount, currency, country,
                        ip_address, device_id, payment_method, kyc_status,
                        timestamp, created_at
                    ) VALUES (
                        1, 'login', 'plr_existing', 0, 'EUR', 'PL',
                        '203.0.113.10', 'device-existing', NULL, 'verified',
                        '2026-10-05 10:00:00', '2026-10-05 10:00:00'
                    )
                    """,
                ),
            )
            connection.execute(text("DROP TABLE alembic_version"))
        engine.dispose()

        command.stamp(config, "0001_initial_schema")
        command.upgrade(config, "head")

        engine = create_engine(database_url)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT player_id FROM events WHERE id = 1")) == (
                "plr_existing"
            )
        index_names = {index["name"] for index in inspect(engine).get_indexes("risk_cases")}
        assert {"ix_risk_cases_queue", "ix_risk_cases_recommended_action"}.issubset(index_names)
        engine.dispose()
    finally:
        if previous_url is None:
            os.environ.pop("RISKDESK_MIGRATION_DATABASE_URL", None)
        else:
            os.environ["RISKDESK_MIGRATION_DATABASE_URL"] = previous_url
