from __future__ import annotations

import uuid
from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from src.config.settings import Settings
from src.rag.types import DocumentChunk, RetrievedChunk
from src.security.rbac import Role, get_policy, parse_role


class QdrantVectorStore:
    """Local Qdrant store with hard metadata filtering for RBAC."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.qdrant_path.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(settings.qdrant_path))

    def recreate_collections(self) -> None:
        for collection in (self.settings.qdrant_text_collection, self.settings.qdrant_code_collection):
            if self._collection_exists(collection):
                self.client.delete_collection(collection_name=collection)
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=self.settings.embedding_dimension, distance=Distance.COSINE),
            )

    def ensure_collections(self) -> None:
        for collection in (self.settings.qdrant_text_collection, self.settings.qdrant_code_collection):
            if not self._collection_exists(collection):
                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=self.settings.embedding_dimension, distance=Distance.COSINE),
                )

    def _collection_exists(self, collection: str) -> bool:
        try:
            return self.client.collection_exists(collection)
        except Exception:
            return False

    def upsert_chunks(self, collection: str, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunk/vector length mismatch.")
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection}:{chunk.payload['chunk_id']}")),
                vector=vector,
                payload={**chunk.payload, "text": chunk.text},
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        if points:
            self.client.upsert(collection_name=collection, points=points)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        role: Role | str,
        source_types: Iterable[str],
        limit: int,
    ) -> list[RetrievedChunk]:
        """Search only with mandatory tenant, role, classification, and route filters."""

        normalized_role = parse_role(role) if isinstance(role, str) else role
        policy = get_policy(normalized_role)
        source_type_list = list(source_types)
        if not source_type_list:
            return []

        query_filter = Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=self.settings.tenant_id)),
                FieldCondition(key="allowed_roles", match=MatchValue(value=normalized_role.value)),
                FieldCondition(key="classification", match=MatchAny(any=list(policy.allowed_classifications))),
                FieldCondition(key="source_type", match=MatchAny(any=source_type_list)),
            ]
        )

        hits = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        results: list[RetrievedChunk] = []
        for hit in hits:
            payload = dict(hit.payload or {})
            text = str(payload.pop("text", ""))
            results.append(RetrievedChunk(text=text, score=float(hit.score), payload=payload))
        return results

    def count_all(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for collection in (self.settings.qdrant_text_collection, self.settings.qdrant_code_collection):
            if not self._collection_exists(collection):
                counts[collection] = 0
                continue
            counts[collection] = int(self.client.count(collection_name=collection, exact=True).count)
        return counts

    def close(self) -> None:
        self.client.close()
