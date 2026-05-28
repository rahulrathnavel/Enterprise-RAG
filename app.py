from __future__ import annotations

import streamlit as st

from src.config.settings import Settings, load_settings
from src.ingestion.index_builder import build_index, ensure_demo_data
from src.rag.orchestrator import RagOrchestrator
from src.security.rbac import Role
from src.ui.layout import render_response
from src.ui.theme import apply_enterprise_css


st.set_page_config(
    page_title="Enterprise RAG",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def get_settings() -> Settings:
    return load_settings()


@st.cache_resource(show_spinner=False)
def get_orchestrator() -> RagOrchestrator:
    return RagOrchestrator(get_settings())


def ensure_index(settings: Settings, orchestrator: RagOrchestrator) -> dict[str, int]:
    ensure_demo_data(settings)
    counts = orchestrator.retriever.store.count_all()
    if any(count == 0 for count in counts.values()):
        counts = build_index(settings, force=True, store=orchestrator.retriever.store)
    return counts


def rebuild_index(settings: Settings, orchestrator: RagOrchestrator) -> dict[str, int]:
    return build_index(settings, force=True, store=orchestrator.retriever.store)


def main() -> None:
    apply_enterprise_css()
    settings = get_settings()
    orchestrator = get_orchestrator()

    st.title("Enterprise RAG")

    with st.sidebar:
        st.header("Session")
        role = st.selectbox("Role", [role.value for role in Role], index=0)
        if st.button("Rebuild Index", use_container_width=True):
            with st.spinner("Rebuilding index"):
                counts = rebuild_index(settings, orchestrator)
                st.session_state["index_counts"] = counts
            st.success(f"Indexed {sum(counts.values())} chunks.")

        if "index_counts" not in st.session_state:
            st.session_state["index_counts"] = ensure_index(settings, orchestrator)
        counts = st.session_state["index_counts"]
        st.divider()
        st.metric("Text Collection", counts.get(settings.qdrant_text_collection, 0))
        st.metric("Code/Log Collection", counts.get(settings.qdrant_code_collection, 0))

    query = st.text_area(
        "Question",
        value="Summarize high-risk infrastructure assets and related incident evidence.",
        height=110,
    )

    submit = st.button("Run Query", type="primary")
    if submit and query.strip():
        with st.spinner("Running secure retrieval"):
            response = orchestrator.run(query.strip(), role)
        render_response(response)


if __name__ == "__main__":
    main()
