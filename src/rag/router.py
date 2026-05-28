from __future__ import annotations

import json
import re

from openai import OpenAI

from src.config.settings import Settings
from src.rag.errors import is_transient_model_error
from src.rag.types import RouteDecision
from src.security.rbac import Role, filter_route_for_role, get_policy, parse_role


class AgenticRouter:
    """Qwen Coder router constrained by backend RBAC validation."""

    VALID_SOURCE_TYPES = {"pdf", "sql", "json_log"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = (
            OpenAI(api_key=settings.nvidia_qwen_api_key, base_url=settings.nvidia_base_url, timeout=20.0, max_retries=0)
            if settings.nvidia_qwen_api_key and not settings.force_local_model_fallback
            else None
        )

    def route(self, query: str, role: Role | str) -> RouteDecision:
        normalized_role = parse_role(role) if isinstance(role, str) else role
        degraded = False
        try:
            requested = self._remote_route(query, normalized_role) if self.client else self._heuristic_route(query)
        except Exception as exc:
            if not is_transient_model_error(exc):
                raise
            requested = self._heuristic_route(query)
            degraded = True
        allowed = filter_route_for_role(normalized_role, requested)
        denied = [source for source in requested if source not in allowed]
        rationale = f"Requested={requested}; allowed={allowed}; role={normalized_role.value}"
        if degraded:
            rationale += "; Qwen router temporarily unavailable, used deterministic RBAC-safe route"
        return RouteDecision(
            source_types=allowed,
            requires_sql="sql" in allowed,
            rationale=rationale,
            denied_source_types=denied,
        )

    def _remote_route(self, query: str, role: Role) -> list[str]:
        policy = get_policy(role)
        system_prompt = (
            "You are an enterprise RAG routing agent. Return only JSON. "
            "Choose source_types from this exact set: pdf, sql, json_log. "
            "Use sql for questions requiring database rows or aggregates. "
            "Use pdf for policy, handbook, runbook, or document questions. "
            "Use json_log for audit log, incident trace, runtime, deployment, or service event questions. "
            f"The user's role is {role.value}. Backend-permitted source types are {list(policy.allowed_source_types)}. "
            "Do not include source types outside the permitted set."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.settings.nvidia_qwen_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=256,
                timeout=20,
            )
            content = response.choices[0].message.content or "{}"
            parsed = _parse_json_object(content)
            source_types = parsed.get("source_types", [])
            if isinstance(source_types, list):
                return [source for source in source_types if source in self.VALID_SOURCE_TYPES]
        except Exception as exc:
            if not self.settings.enable_local_model_fallback or not is_transient_model_error(exc):
                raise
        return self._heuristic_route(query)

    def _heuristic_route(self, query: str) -> list[str]:
        lowered = query.lower()
        sources: set[str] = set()
        if any(term in lowered for term in ("employee", "payroll", "salary", "compensation", "asset", "incident", "severity", "table", "database", "sql")):
            sources.add("sql")
        if any(term in lowered for term in ("policy", "handbook", "runbook", "benefit", "control", "procedure", "sop", "document")):
            sources.add("pdf")
        if any(term in lowered for term in ("log", "trace", "deployment", "runtime", "auth", "error", "event", "vpn", "token")):
            sources.add("json_log")
        return list(sources or {"pdf", "sql"})


def _parse_json_object(content: str) -> dict:
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
