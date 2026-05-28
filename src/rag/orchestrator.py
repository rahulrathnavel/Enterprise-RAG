from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import Settings
from src.rag.retriever import EnterpriseRetriever
from src.rag.router import AgenticRouter
from src.rag.sql_retriever import DynamicSqlRetriever
from src.rag.synthesizer import MistralSynthesizer
from src.rag.types import RetrievedChunk, RouteDecision, SqlResult
from src.security.audit import AuditLogger
from src.security.guardrails import input_guardrail, optional_nvidia_safety_check
from src.security.rbac import Role, parse_role


@dataclass(frozen=True)
class QueryResponse:
    answer: str
    route: RouteDecision
    retrieved_chunks: list[RetrievedChunk]
    sql_result: SqlResult | None
    blocked: bool = False
    reason: str | None = None


class RagOrchestrator:
    """End-to-end secure RAG pipeline used by Streamlit."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.router = AgenticRouter(settings)
        self.retriever = EnterpriseRetriever(settings)
        self.sql_retriever = DynamicSqlRetriever(settings)
        self.synthesizer = MistralSynthesizer(settings)
        self.audit = AuditLogger(settings.root_dir / "data" / "generated" / "audit.jsonl")

    def run(self, query: str, role: Role | str) -> QueryResponse:
        normalized_role = parse_role(role) if isinstance(role, str) else role
        guarded = input_guardrail(query, self.settings)
        if not guarded.allowed:
            self.audit.log("query_blocked", role=normalized_role.value, query=query, reason=guarded.reason)
            return QueryResponse(
                answer="The request was blocked by input guardrails.",
                route=RouteDecision(source_types=[], requires_sql=False, rationale="blocked"),
                retrieved_chunks=[],
                sql_result=None,
                blocked=True,
                reason=guarded.reason,
            )

        safety = optional_nvidia_safety_check(guarded.text, self.settings)
        if not safety.allowed:
            self.audit.log("query_blocked", role=normalized_role.value, query=query, reason=safety.reason)
            return QueryResponse(
                answer="The request was blocked by content safety controls.",
                route=RouteDecision(source_types=[], requires_sql=False, rationale="blocked"),
                retrieved_chunks=[],
                sql_result=None,
                blocked=True,
                reason=safety.reason,
            )

        route = self.router.route(safety.text, normalized_role)
        chunks = self.retriever.retrieve(safety.text, normalized_role, route)
        sql_result = self.sql_retriever.answer_sql(safety.text, normalized_role) if route.requires_sql else None
        answer = self.synthesizer.synthesize(safety.text, normalized_role, chunks, sql_result)

        self.audit.log(
            "query_completed",
            role=normalized_role.value,
            query=query,
            route=route.source_types,
            denied_source_types=route.denied_source_types,
            retrieved_chunk_ids=[chunk.payload.get("chunk_id") for chunk in chunks],
            sql=sql_result.sql if sql_result else None,
            sql_blocked=sql_result.blocked if sql_result else None,
        )

        return QueryResponse(answer=answer, route=route, retrieved_chunks=chunks, sql_result=sql_result)

    def close(self) -> None:
        self.retriever.store.close()
        self.sql_retriever.engine.dispose()
