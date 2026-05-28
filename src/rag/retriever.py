from __future__ import annotations

from src.config.settings import Settings
from src.rag.embeddings import NvidiaEmbeddingClient
from src.rag.reranker import NvidiaReranker
from src.rag.types import RetrievedChunk, RouteDecision
from src.rag.vector_store import QdrantVectorStore
from src.security.rbac import Role


class EnterpriseRetriever:
    """RBAC-aware retriever across PDF, SQL-row summaries, and JSON logs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embeddings = NvidiaEmbeddingClient(settings)
        self.store = QdrantVectorStore(settings)
        self.reranker = NvidiaReranker(settings)

    def retrieve(self, query: str, role: Role | str, route: RouteDecision) -> list[RetrievedChunk]:
        results: list[RetrievedChunk] = []
        source_types = route.source_types
        if not source_types:
            return []

        if any(source in source_types for source in ("pdf", "sql")):
            vector = self.embeddings.embed_texts([query], input_type="query")[0]
            results.extend(
                self.store.search(
                    collection=self.settings.qdrant_text_collection,
                    query_vector=vector,
                    role=role,
                    source_types=[source for source in source_types if source in {"pdf", "sql"}],
                    limit=self.settings.max_retrieval_results,
                )
            )

        if any(source in source_types for source in ("json_log", "sql")):
            vector = self.embeddings.embed_code_texts([query], input_type="query")[0]
            results.extend(
                self.store.search(
                    collection=self.settings.qdrant_code_collection,
                    query_vector=vector,
                    role=role,
                    source_types=[source for source in source_types if source in {"json_log", "sql"}],
                    limit=self.settings.max_retrieval_results,
                )
            )

        deduped = _dedupe(results)
        return self.reranker.rerank(query, deduped, self.settings.rerank_top_n)


def _dedupe(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[str] = set()
    deduped: list[RetrievedChunk] = []
    for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
        chunk_id = str(chunk.payload.get("chunk_id", ""))
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        deduped.append(chunk)
    return deduped
