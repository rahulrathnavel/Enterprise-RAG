from __future__ import annotations

import runpy

from src.config.settings import Settings
from src.ingestion.json_log_ingestor import load_json_log_chunks
from src.ingestion.pdf_ingestor import load_pdf_chunks
from src.ingestion.sql_ingestor import load_sql_row_chunks
from src.rag.embeddings import NvidiaEmbeddingClient
from src.rag.vector_store import QdrantVectorStore


def ensure_demo_data(settings: Settings) -> None:
    """Generate synthetic data on first run for zero-configuration demos."""

    pdf_dir = settings.root_dir / "data" / "raw" / "pdfs"
    log_dir = settings.root_dir / "data" / "raw" / "logs"
    if settings.sqlite_db_path.exists() and any(pdf_dir.glob("*.pdf")) and any(log_dir.glob("*.jsonl")):
        return
    runpy.run_path(str(settings.root_dir / "scripts" / "generate_data.py"), run_name="__main__")


def build_index(settings: Settings, force: bool = True, store: QdrantVectorStore | None = None) -> dict[str, int]:
    """Build the dual-embedding Qdrant index from generated enterprise data."""

    ensure_demo_data(settings)
    embeddings = NvidiaEmbeddingClient(settings)
    owns_store = store is None
    store = store or QdrantVectorStore(settings)
    if force:
        store.recreate_collections()
    else:
        store.ensure_collections()

    pdf_chunks = load_pdf_chunks(settings)
    sql_text_chunks, sql_code_chunks = load_sql_row_chunks(settings)
    json_log_chunks = load_json_log_chunks(settings)

    text_chunks = pdf_chunks + sql_text_chunks
    code_chunks = sql_code_chunks + json_log_chunks

    if text_chunks:
        vectors = embeddings.embed_texts([chunk.text for chunk in text_chunks])
        store.upsert_chunks(settings.qdrant_text_collection, text_chunks, vectors)
    if code_chunks:
        vectors = embeddings.embed_code_texts([chunk.text for chunk in code_chunks])
        store.upsert_chunks(settings.qdrant_code_collection, code_chunks, vectors)

    counts = store.count_all()
    if owns_store:
        store.close()
    return counts
