from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sqlparse
from openai import OpenAI
from sqlalchemy import inspect, text

from src.config.settings import Settings
from src.db.session import build_sqlite_engine
from src.rag.errors import compact_model_error, is_transient_model_error
from src.rag.types import SqlResult
from src.security.rbac import Role, get_policy, parse_role


FORBIDDEN_SQL_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
}

ALL_DEMO_TABLES = {"employees", "payroll", "infrastructure_assets", "incidents"}


@dataclass(frozen=True)
class SchemaPrompt:
    text: str
    allowed_tables: tuple[str, ...]


class DynamicSqlRetriever:
    """Qwen-powered dynamic SQL retriever with backend security enforcement.

    The model is shown only schemas permitted for the active role. The resulting
    SQL is still treated as untrusted input and must pass strict validation
    before SQLAlchemy executes it against SQLite.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = build_sqlite_engine(settings.sqlite_db_path)
        self.client = (
            OpenAI(api_key=settings.nvidia_qwen_api_key, base_url=settings.nvidia_base_url, timeout=20.0, max_retries=0)
            if settings.nvidia_qwen_api_key and not settings.force_local_model_fallback
            else None
        )

    def answer_sql(self, query: str, role: Role | str) -> SqlResult:
        normalized_role = parse_role(role) if isinstance(role, str) else role
        schema_prompt = self._schema_prompt(normalized_role)
        try:
            generated = self._generate_sql(query, normalized_role, schema_prompt)
        except Exception as exc:
            if not is_transient_model_error(exc):
                return SqlResult(
                    sql="",
                    columns=[],
                    rows=[],
                    blocked=True,
                    reason=f"Qwen SQL generation failed: {compact_model_error(exc)}",
                )
            generated = self._fallback_sql(query, schema_prompt.allowed_tables)
        try:
            safe_sql = self._validate_and_limit_sql(generated, schema_prompt.allowed_tables)
            return self._execute(safe_sql)
        except ValueError as exc:
            return SqlResult(sql=generated, columns=[], rows=[], blocked=True, reason=str(exc))
        except Exception as exc:
            return SqlResult(sql=generated, columns=[], rows=[], blocked=True, reason=f"SQL execution failed: {exc}")

    def _schema_prompt(self, role: Role) -> SchemaPrompt:
        allowed_tables = get_policy(role).allowed_sql_tables
        inspector = inspect(self.engine)
        lines: list[str] = []
        for table_name in allowed_tables:
            columns = inspector.get_columns(table_name)
            column_text = ", ".join(f"{column['name']} {column['type']}" for column in columns)
            lines.append(f"- {table_name}({column_text})")
        return SchemaPrompt(text="\n".join(lines), allowed_tables=allowed_tables)

    def _generate_sql(self, query: str, role: Role, schema_prompt: SchemaPrompt) -> str:
        if not self.client:
            return self._fallback_sql(query, schema_prompt.allowed_tables)

        system_prompt = f"""
You are Qwen Coder generating SQLite for a secure enterprise RAG system.
Return exactly one SQLite SELECT statement and no markdown.

Security contract:
- The active role is {role.value}.
- You may use ONLY these table schemas:
{schema_prompt.text}
- Do not reference tables that are not listed.
- Do not use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, REPLACE, ATTACH, DETACH, PRAGMA, or VACUUM.
- Do not include comments.
- Prefer aggregate SELECT queries when the user asks for summaries.
- Include LIMIT {self.settings.max_sql_rows} unless an aggregate query returns one row.
""".strip()

        try:
            response = self.client.chat.completions.create(
                model=self.settings.nvidia_qwen_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=512,
                timeout=20,
            )
            return _strip_sql(response.choices[0].message.content or "")
        except Exception:
            if not self.settings.enable_local_model_fallback:
                raise
            return self._fallback_sql(query, schema_prompt.allowed_tables)

    def _fallback_sql(self, query: str, allowed_tables: tuple[str, ...]) -> str:
        """Offline fallback used only when Qwen is unavailable."""

        lowered = query.lower()
        if "payroll" in allowed_tables and any(term in lowered for term in ("payroll", "gross", "net", "tax", "salary")):
            return "SELECT employee_id, period, gross_pay, tax_withheld, net_pay FROM payroll"
        if "employees" in allowed_tables and any(term in lowered for term in ("employee", "department", "manager", "compensation")):
            return "SELECT employee_id, department, compensation_band, manager FROM employees"
        if "incidents" in allowed_tables and any(term in lowered for term in ("incident", "severity", "root cause", "remediation")):
            return "SELECT incident_id, severity, affected_service, root_cause, remediation FROM incidents"
        if "infrastructure_assets" in allowed_tables:
            return "SELECT asset_id, service_name, environment, owner_team, risk_level FROM infrastructure_assets"
        return f"SELECT * FROM {allowed_tables[0]}"

    def _validate_and_limit_sql(self, sql: str, allowed_tables: tuple[str, ...]) -> str:
        candidate = sql.strip()
        if not candidate:
            raise ValueError("Generated SQL was empty.")
        if "--" in candidate or "/*" in candidate or "*/" in candidate:
            raise ValueError("SQL comments are not allowed.")

        candidate = candidate.rstrip().rstrip(";").strip()
        parsed = sqlparse.parse(candidate)
        if len(parsed) != 1:
            raise ValueError("Only one SQL statement is allowed.")

        normalized = " ".join(str(parsed[0]).upper().split())
        tokens = set(re.findall(r"\b[A-Z_]+\b", normalized))
        forbidden = sorted(tokens.intersection(FORBIDDEN_SQL_KEYWORDS))
        if forbidden:
            raise ValueError(f"Forbidden SQL keyword detected: {', '.join(forbidden)}.")

        if not normalized.startswith("SELECT "):
            raise ValueError("Only SELECT statements are permitted.")

        for table_name in ALL_DEMO_TABLES.difference(set(allowed_tables)):
            if re.search(rf"\b{re.escape(table_name)}\b", candidate, flags=re.IGNORECASE):
                raise ValueError(f"Role is not permitted to query table: {table_name}.")

        referenced_tables = {
            match.group(1).lower()
            for match in re.finditer(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", candidate, flags=re.IGNORECASE)
        }
        unknown_tables = referenced_tables.difference(set(allowed_tables))
        if unknown_tables:
            raise ValueError(f"SQL references non-allowed table(s): {', '.join(sorted(unknown_tables))}.")

        if not re.search(r"\bLIMIT\b", candidate, flags=re.IGNORECASE) and not _looks_like_single_row_aggregate(candidate):
            candidate = f"{candidate} LIMIT {self.settings.max_sql_rows}"
        return candidate

    def _execute(self, sql: str) -> SqlResult:
        with self.engine.connect() as connection:
            result = connection.execute(text(sql))
            rows = [dict(row) for row in result.mappings().fetchmany(self.settings.max_sql_rows)]
            columns = list(result.keys())
        return SqlResult(sql=sql, columns=columns, rows=rows)


def _strip_sql(content: str) -> str:
    fence = re.search(r"```(?:sql)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        return fence.group(1).strip()
    select_match = re.search(r"\bSELECT\b.*", content, flags=re.IGNORECASE | re.DOTALL)
    return select_match.group(0).strip() if select_match else content.strip()


def _looks_like_single_row_aggregate(sql: str) -> bool:
    lowered = sql.lower()
    has_aggregate = any(function in lowered for function in ("count(", "sum(", "avg(", "min(", "max("))
    has_group_by = " group by " in f" {lowered} "
    return has_aggregate and not has_group_by
