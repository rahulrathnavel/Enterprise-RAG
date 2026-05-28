from __future__ import annotations

from src.config.settings import Settings
from src.ingestion.index_builder import ensure_demo_data


def ensure_seeded(settings: Settings) -> None:
    """Compatibility wrapper for database/data seeding."""

    ensure_demo_data(settings)
