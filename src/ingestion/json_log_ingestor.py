from __future__ import annotations

import json
from datetime import datetime, timezone

from src.config.settings import Settings
from src.rag.types import DocumentChunk
from src.security.rbac import AccessGroup, allowed_roles_for_access_group


def load_json_log_chunks(settings: Settings) -> list[DocumentChunk]:
    """Load JSONL system logs into the Engineering/Ops vector silo."""

    log_dir = settings.root_dir / "data" / "raw" / "logs"
    chunks: list[DocumentChunk] = []
    for log_path in sorted(log_dir.glob("*.jsonl")):
        with log_path.open("r", encoding="utf-8") as handle:
            for line_index, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                access_group = record.get("access_group", AccessGroup.ENGINEERING_OPS.value)
                text = (
                    f"timestamp={record.get('timestamp')} service={record.get('service')} "
                    f"environment={record.get('environment')} severity={record.get('severity')} "
                    f"event_type={record.get('event_type')} actor={record.get('actor')} "
                    f"message={record.get('message')} trace_id={record.get('trace_id')}"
                )
                payload = {
                    "tenant_id": settings.tenant_id,
                    "source_type": "json_log",
                    "source_name": log_path.name,
                    "document_id": log_path.stem,
                    "row_id": line_index,
                    "chunk_id": f"json_log:{log_path.stem}:{line_index}",
                    "access_group": access_group,
                    "allowed_roles": allowed_roles_for_access_group(access_group),
                    "classification": record.get("classification", "internal"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                chunks.append(DocumentChunk(text=text, payload=payload))
    return chunks
