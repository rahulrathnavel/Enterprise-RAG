from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentChunk:
    """A normalized retrieval unit with Qdrant payload metadata."""

    text: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    score: float
    payload: dict[str, Any]


@dataclass(frozen=True)
class RouteDecision:
    """Validated router output after RBAC filtering."""

    source_types: list[str]
    requires_sql: bool
    rationale: str
    denied_source_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SqlResult:
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    blocked: bool = False
    reason: str | None = None
