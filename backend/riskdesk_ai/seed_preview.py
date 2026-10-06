import argparse
import json
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from riskdesk_ai.database import get_migration_database_url
from riskdesk_ai.services.demo_service import DemoService


def seed_preview(database_url: str) -> dict[str, object]:
    if os.getenv("RISKDESK_DEPLOYMENT_ENV") != "preview":
        raise RuntimeError("RISKDESK_DEPLOYMENT_ENV must be 'preview'")
    if os.getenv("RISKDESK_PREVIEW_SEED_ENABLED", "false").lower() != "true":
        raise RuntimeError("RISKDESK_PREVIEW_SEED_ENABLED must be 'true'")
    if make_url(database_url).get_backend_name() != "postgresql":
        raise RuntimeError("Preview seed requires a PostgreSQL migration connection")

    engine = create_engine(database_url, poolclass=NullPool)
    try:
        with Session(engine) as db:
            result = DemoService(db).seed()
            return result.model_dump()
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace preview data with the repository's synthetic demo dataset.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Required acknowledgement that existing preview rows will be deleted.",
    )
    args = parser.parse_args()
    if not args.replace:
        parser.error("--replace is required")

    result = seed_preview(get_migration_database_url())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
