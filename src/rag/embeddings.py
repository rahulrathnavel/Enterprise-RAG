from __future__ import annotations

import hashlib
import math
from functools import lru_cache

import numpy as np
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Settings


class NvidiaEmbeddingClient:
    """Dual embedding client for NVIDIA NIM retrieval models.

    `nvidia/nv-embed-v1` is used for business text and PDF/SQL summaries.
    `nvidia/nv-embedcode-7b-v1` is used for code-like technical material such
    as JSON logs, incidents, and infrastructure rows.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._text_client = self._client(settings.nvidia_embed_api_key)
        self._code_client = self._client(settings.nvidia_embedcode_api_key)

    def _client(self, api_key: str | None) -> OpenAI | None:
        if self.settings.force_local_model_fallback or not api_key:
            return None
        return OpenAI(api_key=api_key, base_url=self.settings.nvidia_base_url, timeout=12.0, max_retries=0)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, self.settings.nvidia_embed_model, self._text_client, "text")

    def embed_code_texts(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, self.settings.nvidia_embedcode_model, self._code_client, "code")

    @retry(wait=wait_exponential(multiplier=1, min=1, max=2), stop=stop_after_attempt(1), reraise=True)
    def _remote_embed(self, client: OpenAI, model: str, texts: list[str]) -> list[list[float]]:
        response = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]

    def _embed(self, texts: list[str], model: str, client: OpenAI | None, namespace: str) -> list[list[float]]:
        if not texts:
            return []
        if client is not None:
            try:
                return self._remote_embed(client, model, texts)
            except Exception:
                if not self.settings.enable_local_model_fallback:
                    raise
        return [deterministic_embedding(text, self.settings.embedding_dimension, namespace) for text in texts]


@lru_cache(maxsize=8192)
def _token_hash(token: str, namespace: str) -> int:
    digest = hashlib.sha256(f"{namespace}:{token}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def deterministic_embedding(text: str, dimension: int, namespace: str) -> list[float]:
    """Deterministic fallback embedding for offline/rate-limited demos.

    It is not a replacement for NVIDIA embeddings, but it keeps indexing and UI
    flows testable when API calls are unavailable. The vector dimension matches
    NV-Embed/NV-EmbedCode so Qdrant collection schemas stay consistent.
    """

    vector = np.zeros(dimension, dtype=np.float32)
    tokens = [token.strip(".,:;()[]{}\"'").lower() for token in text.split()]
    for token in tokens:
        if not token:
            continue
        hashed = _token_hash(token, namespace)
        index = hashed % dimension
        sign = -1.0 if hashed & 1 else 1.0
        vector[index] += sign * (1.0 + math.log1p(len(token)))
    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector /= norm
    return vector.astype(float).tolist()
