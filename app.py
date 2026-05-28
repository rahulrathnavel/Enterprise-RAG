from __future__ import annotations

import streamlit as st

from src.config.settings import Settings, load_settings, missing_required_secret_names
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


def render_startup_error_if_present(settings: Settings) -> None:
    startup_error = settings.root_dir / "data" / "generated" / "startup_error.txt"
    if not startup_error.exists():
        return

    st.error("Runtime index preparation failed.")
    st.write(
        "The server is online, but the vector index could not be built during startup. "
        "Check the deployment logs and verify the NVIDIA model keys and endpoint settings."
    )
    details = startup_error.read_text(encoding="utf-8", errors="ignore")
    with st.expander("Technical details"):
        st.code(details[-6000:], language="text")
    st.stop()


def main() -> None:
    apply_enterprise_css()
    settings = get_settings()

    st.title("Enterprise RAG")

    missing_secrets = missing_required_secret_names(settings)
    if missing_secrets:
        st.error("Deployment configuration is incomplete.")
        st.write(
            "The server is running, but model access is disabled because required "
            "NVIDIA NIM environment variables are not configured."
        )
        st.code("\n".join(missing_secrets), language="text")
        st.info(
            "Set these values in your cloud provider's Environment Variables or "
            "Secrets dashboard. Do not place API keys in GitHub, Dockerfile, README, "
            ".env.example, or any committed file."
        )
        st.stop()

    render_startup_error_if_present(settings)

    orchestrator = get_orchestrator()

    with st.sidebar:
        st.header("Session")
        role = st.selectbox("Role", [role.value for role in Role], index=0)
        if st.button("Rebuild Index", use_container_width=True):
            with st.spinner("Rebuilding index"):
                counts = rebuild_index(settings, orchestrator)
                st.session_state["index_counts"] = counts
            st.success(f"Indexed {sum(counts.values())} chunks.")

        if "index_counts" not in st.session_state:
            try:
                st.session_state["index_counts"] = ensure_index(settings, orchestrator)
            except Exception as exc:
                st.error("Vector index initialization failed.")
                st.write("Verify the NVIDIA embedding keys and Render environment variables, then redeploy.")
                st.code(f"{type(exc).__name__}: {exc}", language="text")
                st.stop()
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
            try:
                response = orchestrator.run(query.strip(), role)
            except Exception as exc:
                st.error("The query could not be completed.")
                st.write(
                    "A model provider or retrieval dependency returned an unexpected error. "
                    "Please retry the query. If this persists, check the deployment logs."
                )
                st.code(f"{type(exc).__name__}: {str(exc)[:500]}", language="text")
                st.stop()
        render_response(response)


if __name__ == "__main__":
    main()
