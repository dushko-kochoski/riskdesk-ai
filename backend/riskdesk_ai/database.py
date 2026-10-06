import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("RISKDESK_DATABASE_URL", "sqlite:///./riskdesk_ai.db")


def create_database_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        return create_engine(database_url, connect_args={"check_same_thread": False})

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("RISKDESK_DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("RISKDESK_DB_MAX_OVERFLOW", "5")),
        pool_recycle=int(os.getenv("RISKDESK_DB_POOL_RECYCLE_SECONDS", "300")),
    )


def get_migration_database_url() -> str:
    migration_url = os.getenv("RISKDESK_MIGRATION_DATABASE_URL")
    if not migration_url:
        raise RuntimeError(
            "RISKDESK_MIGRATION_DATABASE_URL must be set before running Alembic migrations",
        )
    return migration_url


engine = create_database_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
