from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.config.secrets import load_secret_values


ROOT_DIR = Path(__file__).resolve().parents[2]


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the self-contained RAG application."""

    root_dir: Path
    app_env: str
    tenant_id: str
    sqlite_db_path: Path
    qdrant_path: Path
    qdrant_text_collection: str
    qdrant_code_collection: str
    nvidia_base_url: str
    nvidia_qwen_model: str
    nvidia_mistral_model: str
    nvidia_embed_model: str
    nvidia_embedcode_model: str
    nvidia_safety_model: str
    nvidia_rerank_url: str
    nvidia_rerank_model: str
    nvidia_qwen_api_key: str | None
    nvidia_mistral_api_key: str | None
    nvidia_embed_api_key: str | None
    nvidia_embedcode_api_key: str | None
    nvidia_rerank_api_key: str | None
    nvidia_safety_api_key: str | None
    gliner_pii_api_key: str | None
    enable_local_model_fallback: bool
    force_local_model_fallback: bool
    enable_remote_safety: bool
    max_sql_rows: int
    max_retrieval_results: int
    rerank_top_n: int
    embedding_dimension: int = 4096


def load_settings() -> Settings:
    """Resolve application configuration without exposing secret material."""

    load_dotenv(ROOT_DIR / ".env")
    secrets = load_secret_values(ROOT_DIR)

    return Settings(
        root_dir=ROOT_DIR,
        app_env=os.getenv("APP_ENV", "development"),
        tenant_id=os.getenv("TENANT_ID", "demo_enterprise"),
        sqlite_db_path=ROOT_DIR / os.getenv("SQLITE_DB_PATH", "data/generated/enterprise_demo.db"),
        qdrant_path=ROOT_DIR / os.getenv("QDRANT_PATH", "data/qdrant"),
        qdrant_text_collection=os.getenv("QDRANT_TEXT_COLLECTION", "enterprise_text"),
        qdrant_code_collection=os.getenv("QDRANT_CODE_COLLECTION", "enterprise_code_logs"),
        nvidia_base_url=secrets.get("NVIDIA_BASE_URL", os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")),
        nvidia_qwen_model=os.getenv("NVIDIA_QWEN_MODEL", "qwen/qwen3-coder-480b-a35b-instruct"),
        nvidia_mistral_model=os.getenv("NVIDIA_MISTRAL_MODEL", "mistralai/mistral-large-3-675b-instruct-2512"),
        nvidia_embed_model=os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nv-embed-v1"),
        nvidia_embedcode_model=os.getenv("NVIDIA_EMBEDCODE_MODEL", "nvidia/nv-embedcode-7b-v1"),
        nvidia_safety_model=os.getenv("NVIDIA_SAFETY_MODEL", "nvidia/nemotron-content-safety-reasoning-4b"),
        nvidia_rerank_url=os.getenv("NVIDIA_RERANK_URL", "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"),
        nvidia_rerank_model=os.getenv("NVIDIA_RERANK_MODEL", "nv-rerank-qa-mistral-4b:1"),
        nvidia_qwen_api_key=secrets.get("NVIDIA_QWEN_API_KEY"),
        nvidia_mistral_api_key=secrets.get("NVIDIA_MISTRAL_API_KEY"),
        nvidia_embed_api_key=secrets.get("NVIDIA_EMBED_API_KEY"),
        nvidia_embedcode_api_key=secrets.get("NVIDIA_EMBEDCODE_API_KEY"),
        nvidia_rerank_api_key=secrets.get("NVIDIA_RERANK_API_KEY"),
        nvidia_safety_api_key=secrets.get("NVIDIA_SAFETY_API_KEY"),
        gliner_pii_api_key=secrets.get("GLINER_PII_API_KEY"),
        enable_local_model_fallback=_bool("ENABLE_LOCAL_MODEL_FALLBACK", True),
        force_local_model_fallback=_bool("FORCE_LOCAL_MODEL_FALLBACK", False),
        enable_remote_safety=_bool("ENABLE_REMOTE_SAFETY", False),
        max_sql_rows=_int("MAX_SQL_ROWS", 100),
        max_retrieval_results=_int("MAX_RETRIEVAL_RESULTS", 8),
        rerank_top_n=_int("RERANK_TOP_N", 5),
    )
