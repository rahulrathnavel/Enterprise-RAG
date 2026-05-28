from __future__ import annotations

import json

from openai import OpenAI

from src.config.settings import Settings
from src.rag.errors import compact_model_error, is_transient_model_error
from src.rag.types import RetrievedChunk, SqlResult
from src.security.guardrails import output_guardrail
from src.security.rbac import Role, parse_role


class MistralSynthesizer:
    """Answer synthesis through Mistral Large on NVIDIA NIM."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = (
            OpenAI(api_key=settings.nvidia_mistral_api_key, base_url=settings.nvidia_base_url, timeout=35.0, max_retries=0)
            if settings.nvidia_mistral_api_key and not settings.force_local_model_fallback
            else None
        )

    def synthesize(
        self,
        query: str,
        role: Role | str,
        chunks: list[RetrievedChunk],
        sql_result: SqlResult | None,
    ) -> str:
        normalized_role = parse_role(role) if isinstance(role, str) else role
        context = _format_context(chunks, sql_result)
        if not context.strip():
            return "No authorized context was retrieved for this role and query."

        if self.client:
            try:
                answer = self._remote_synthesis(query, normalized_role, context)
                return output_guardrail(answer)
            except Exception as exc:
                if not is_transient_model_error(exc) and not self.settings.enable_local_model_fallback:
                    raise
                if not self.settings.enable_local_model_fallback:
                    return output_guardrail(
                        "The NVIDIA synthesis endpoint is temporarily busy. "
                        "Authorized context was retrieved successfully, but final generation could not complete. "
                        f"Please retry in a moment. Provider detail: {compact_model_error(exc)}"
                    )
        return output_guardrail(_fallback_synthesis(context))

    def _remote_synthesis(self, query: str, role: Role, context: str) -> str:
        system_prompt = (
            "You are an enterprise RAG answer synthesizer. Answer only from the authorized context provided. "
            "If the context is insufficient, say so. Do not infer data from outside context. "
            "Use concise professional language and cite source names or SQL result when relevant. "
            f"The active role is {role.value}; never mention or reveal hidden data outside this context."
        )
        response = self.client.chat.completions.create(
            model=self.settings.nvidia_mistral_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question:\n{query}\n\nAuthorized context:\n{context}"},
            ],
            temperature=0.1,
            top_p=1,
            max_tokens=900,
            timeout=35,
        )
        return response.choices[0].message.content or ""


def _format_context(chunks: list[RetrievedChunk], sql_result: SqlResult | None) -> str:
    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.payload.get("source_name", "unknown")
        source_type = chunk.payload.get("source_type", "unknown")
        chunk_id = chunk.payload.get("chunk_id", "unknown")
        parts.append(
            f"[Context {index}] source_type={source_type}; source={source}; chunk_id={chunk_id}; "
            f"score={chunk.score:.4f}\n{chunk.text}"
        )
    if sql_result and not sql_result.blocked:
        parts.append(
            "[SQL Result]\n"
            f"Executed SELECT: {sql_result.sql}\n"
            f"Columns: {', '.join(sql_result.columns)}\n"
            f"Rows: {json.dumps(sql_result.rows, default=str)}"
        )
    elif sql_result and sql_result.blocked:
        parts.append(f"[SQL Blocked]\nReason: {sql_result.reason}")
    return "\n\n".join(parts)


def _fallback_synthesis(context: str) -> str:
    compact = context[:2200]
    return f"Authorized context retrieved. Summary excerpt:\n\n{compact}"
