from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv


SECRET_FILES = ("apis.txt", "apiss.txt")


def _read_candidate_files(root: Path) -> str:
    chunks: list[str] = []
    for filename in SECRET_FILES:
        path = root / filename
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def parse_apis_file(root: Path) -> dict[str, str]:
    """Parse the local hackathon API notes without logging any secret value.

    The approved production path is environment variables or `.env`. This parser
    exists only because the challenge package includes minimal NVIDIA sample code
    in `apis.txt`/`apiss.txt`. It maps those snippets into normalized variable
    names used by the application.
    """

    text = _read_candidate_files(root)
    if not text:
        return {}

    parsed: dict[str, str] = {}

    base_url = _first_match(r"base_url\s*=\s*[\"']([^\"']+)[\"']", text)
    if base_url:
        parsed["NVIDIA_BASE_URL"] = base_url

    qwen_key = _first_match(
        r"client\s*=\s*OpenAI\([^)]*?api_key\s*=\s*[\"']([^\"']+)[\"'][^)]*?\).*?qwen/qwen3-coder",
        text,
    )
    if qwen_key:
        parsed["NVIDIA_QWEN_API_KEY"] = qwen_key

    model_key_pairs = {
        "NVIDIA_EMBED_API_KEY": r"nv-embed-v1\s*[\r\n]+api\s*key\s*:\s*(nvapi-[^\s]+)",
        "NVIDIA_EMBEDCODE_API_KEY": r"nv-embedcode-7b-v1\s*[\r\n]+api\s*key\s*:\s*(nvapi-[^\s]+)",
        "NVIDIA_RERANK_API_KEY": r"rerank-qa-mistral-4b\s*[\r\n]+api\s*key\s*:\s*(nvapi-[^\s]+)",
        "NVIDIA_SAFETY_API_KEY": r"nemotron-content-safety-reasoning-4b\s*[\r\n]+api\s*key\s*:\s*(nvapi-[^\s]+)",
        "GLINER_PII_API_KEY": r"gliner-pii\s*[\r\n]+api\s*key\s*:\s*([^\s]+)",
    }
    for env_name, pattern in model_key_pairs.items():
        value = _first_match(pattern, text)
        if value:
            parsed[env_name] = value

    mistral_key = _first_match(r"Authorization[\"']?\s*:\s*[\"']Bearer\s+(nvapi-[^\"']+)[\"']", text)
    if mistral_key:
        parsed["NVIDIA_MISTRAL_API_KEY"] = mistral_key

    return parsed


def load_secret_values(root: Path) -> dict[str, str]:
    """Load secrets with strict precedence: environment, .env, local fallback."""

    load_dotenv(root / ".env")
    fallback = parse_apis_file(root)

    names = {
        "NVIDIA_BASE_URL",
        "NVIDIA_QWEN_API_KEY",
        "NVIDIA_MISTRAL_API_KEY",
        "NVIDIA_EMBED_API_KEY",
        "NVIDIA_EMBEDCODE_API_KEY",
        "NVIDIA_RERANK_API_KEY",
        "NVIDIA_SAFETY_API_KEY",
        "GLINER_PII_API_KEY",
    }

    resolved: dict[str, str] = {}
    for name in names:
        value = os.getenv(name) or fallback.get(name)
        if value:
            resolved[name] = value
    return resolved
