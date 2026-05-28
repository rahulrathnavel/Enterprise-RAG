from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, select

from src.config.settings import Settings
from src.db.models import Employee, Incident, InfrastructureAsset, Payroll
from src.db.session import build_session_factory, build_sqlite_engine
from src.rag.types import DocumentChunk
from src.security.rbac import AccessGroup, allowed_roles_for_access_group


TABLE_MODEL_MAP = {
    "employees": Employee,
    "payroll": Payroll,
    "infrastructure_assets": InfrastructureAsset,
    "incidents": Incident,
}

TABLE_ACCESS_GROUP = {
    "employees": AccessGroup.HR_FINANCE.value,
    "payroll": AccessGroup.HR_FINANCE.value,
    "infrastructure_assets": AccessGroup.ENGINEERING_OPS.value,
    "incidents": AccessGroup.ENGINEERING_OPS.value,
}


def load_sql_row_chunks(settings: Settings) -> tuple[list[DocumentChunk], list[DocumentChunk]]:
    """Convert relational rows into searchable summaries.

    Business rows are embedded with the general text model. Infrastructure and
    incident rows are embedded with the code/log model because operational
    questions often contain service names, incident IDs, and technical language.
    """

    engine = build_sqlite_engine(settings.sqlite_db_path)
    SessionLocal = build_session_factory(engine)
    text_chunks: list[DocumentChunk] = []
    code_chunks: list[DocumentChunk] = []

    with SessionLocal() as session:
        for table_name, model in TABLE_MODEL_MAP.items():
            access_group = TABLE_ACCESS_GROUP[table_name]
            allowed_roles = allowed_roles_for_access_group(access_group)
            classification = "restricted" if table_name == "payroll" else ("confidential" if table_name == "employees" else "internal")
            rows = session.execute(select(model)).scalars().all()
            for row in rows:
                values = {column.key: getattr(row, column.key) for column in inspect(model).columns}
                row_id = values.get("id")
                summary = "; ".join(f"{key}: {value}" for key, value in values.items())
                payload = {
                    "tenant_id": settings.tenant_id,
                    "source_type": "sql",
                    "source_name": table_name,
                    "document_id": table_name,
                    "row_id": row_id,
                    "chunk_id": f"sql:{table_name}:{row_id}",
                    "access_group": access_group,
                    "allowed_roles": allowed_roles,
                    "classification": classification,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                target = code_chunks if table_name in {"infrastructure_assets", "incidents"} else text_chunks
                target.append(DocumentChunk(text=summary, payload=payload))

    return text_chunks, code_chunks


def get_full_schema(settings: Settings) -> dict[str, list[tuple[str, str]]]:
    """Return table schemas for dynamic SQL generation prompts."""

    engine = build_sqlite_engine(settings.sqlite_db_path)
    inspector = inspect(engine)
    schema: dict[str, list[tuple[str, str]]] = {}
    for table_name in inspector.get_table_names():
        schema[table_name] = [(column["name"], str(column["type"])) for column in inspector.get_columns(table_name)]
    return schema
