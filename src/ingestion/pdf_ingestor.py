from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from src.config.settings import Settings
from src.ingestion.chunking import chunk_text
from src.rag.types import DocumentChunk
from src.security.rbac import AccessGroup, allowed_roles_for_access_group


def _access_group_from_filename(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("hr_finance"):
        return AccessGroup.HR_FINANCE.value
    if name.startswith("engineering"):
        return AccessGroup.ENGINEERING_OPS.value
    return AccessGroup.SHARED.value


def load_pdf_chunks(settings: Settings) -> list[DocumentChunk]:
    """Extract PDF text and attach immutable RBAC metadata to every chunk."""

    pdf_dir = settings.root_dir / "data" / "raw" / "pdfs"
    chunks: list[DocumentChunk] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        access_group = _access_group_from_filename(pdf_path)
        allowed_roles = allowed_roles_for_access_group(access_group)
        classification = "internal" if access_group == AccessGroup.SHARED.value else "confidential"
        reader = PdfReader(str(pdf_path))
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for chunk_index, chunk in enumerate(chunk_text(text), start=1):
                document_id = pdf_path.stem
                payload = {
                    "tenant_id": settings.tenant_id,
                    "source_type": "pdf",
                    "source_name": pdf_path.name,
                    "document_id": document_id,
                    "chunk_id": f"pdf:{document_id}:p{page_index}:c{chunk_index}",
                    "page_number": page_index,
                    "access_group": access_group,
                    "allowed_roles": allowed_roles,
                    "classification": classification,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                chunks.append(DocumentChunk(text=chunk, payload=payload))
    return chunks
