from __future__ import annotations

import pandas as pd
import streamlit as st

from src.rag.orchestrator import QueryResponse
from src.security.pii import redact_pii


def render_response(response: QueryResponse) -> None:
    st.subheader("Answer")
    st.write(response.answer)

    st.subheader("Access Decision")
    route_cols = st.columns(3)
    route_cols[0].metric("Route", ", ".join(response.route.source_types) or "None")
    route_cols[1].metric("SQL", "Enabled" if response.route.requires_sql else "Not used")
    route_cols[2].metric("Denied", ", ".join(response.route.denied_source_types) or "None")
    st.caption(response.route.rationale)

    if response.sql_result is not None:
        st.subheader("SQL Execution")
        st.code(response.sql_result.sql, language="sql")
        if response.sql_result.blocked:
            st.error(response.sql_result.reason or "SQL blocked.")
        elif response.sql_result.rows:
            st.dataframe(_redacted_frame(response.sql_result.rows), use_container_width=True, hide_index=True)
        else:
            st.info("The SQL query returned no rows.")

    st.subheader("Retrieved Sources")
    if not response.retrieved_chunks:
        st.info("No vector sources were retrieved for this query.")
        return

    for index, chunk in enumerate(response.retrieved_chunks, start=1):
        source = chunk.payload.get("source_name", "unknown")
        chunk_id = chunk.payload.get("chunk_id", "unknown")
        label = f"{index}. {source} | {chunk.payload.get('source_type')} | score {chunk.score:.4f}"
        with st.expander(label):
            st.code(chunk_id, language="text")
            st.write(redact_pii(chunk.text))


def _redacted_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].dtype == object:
            frame[column] = frame[column].map(lambda value: redact_pii(str(value)) if value is not None else value)
    return frame
