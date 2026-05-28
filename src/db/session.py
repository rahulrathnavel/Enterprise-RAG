from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_sqlite_engine(db_path: str | Path) -> Engine:
    """Create a SQLite engine with production-style SQLAlchemy access.

    SQLite is used for the hackathon package because it is self-contained. The
    rest of the code depends on SQLAlchemy abstractions so the persistence layer
    can move to PostgreSQL without rewriting the RAG/security pipeline.
    """

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path.as_posix()}", future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
