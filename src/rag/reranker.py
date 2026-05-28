from __future__ import annotations

from collections import Counter

import requests

from src.config.settings import Settings
from src.rag.types import RetrievedChunk


class NvidiaReranker:
    """NVIDIA retrieval reranker with lexical fallback for free-tier resilience."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_n: int | None = None) -> list[RetrievedChunk]:
        if not chunks:
            return []
        top_n = top_n or self.settings.rerank_top_n
        if self.settings.nvidia_rerank_api_key and not self.settings.force_local_model_fallback:
            try:
                return self._remote_rerank(query, chunks)[:top_n]
            except Exception:
                if not self.settings.enable_local_model_fallback:
                    raise
        return self._lexical_rerank(query, chunks)[:top_n]

    def _remote_rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        payload = {
            "model": self.settings.nvidia_rerank_model,
            "query": {"text": query[:9000]},
            "passages": [{"text": chunk.text[:9000]} for chunk in chunks[:512]],
        }
        response = requests.post(
            self.settings.nvidia_rerank_url,
            headers={
                "Authorization": f"Bearer {self.settings.nvidia_rerank_api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        ranked_items = data.get("rankings") or data.get("results") or data.get("data") or []
        if not ranked_items:
            return chunks

        ranked: list[RetrievedChunk] = []
        for item in ranked_items:
            index = int(item.get("index", item.get("passage_index", 0)))
            score = float(item.get("score", item.get("logit", chunks[index].score)))
            if 0 <= index < len(chunks):
                original = chunks[index]
                ranked.append(RetrievedChunk(text=original.text, score=score, payload=original.payload))
        return ranked or chunks

    def _lexical_rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        query_terms = Counter(_terms(query))

        def score(chunk: RetrievedChunk) -> float:
            terms = Counter(_terms(chunk.text))
            overlap = sum(min(count, terms[term]) for term, count in query_terms.items())
            return float(overlap) + chunk.score

        return sorted(chunks, key=score, reverse=True)


def _terms(text: str) -> list[str]:
    return [token.strip(".,:;()[]{}\"'").lower() for token in text.split() if len(token.strip()) > 2]
