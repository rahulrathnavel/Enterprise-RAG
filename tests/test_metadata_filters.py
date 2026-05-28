from src.rag.vector_store import QdrantVectorStore
from src.security.rbac import Role


def test_qdrant_filter_contains_role_and_source_constraints(monkeypatch, tmp_path) -> None:
    class FakeClient:
        def __init__(self, path: str) -> None:
            self.filter = None

        def search(self, **kwargs):
            self.filter = kwargs["query_filter"]
            return []

    monkeypatch.setattr("src.rag.vector_store.QdrantClient", FakeClient)

    class Settings:
        qdrant_path = tmp_path
        tenant_id = "demo_enterprise"
        embedding_dimension = 4096
        qdrant_text_collection = "enterprise_text"
        qdrant_code_collection = "enterprise_code_logs"

    store = QdrantVectorStore(Settings())
    store.search("enterprise_text", [0.0] * 4096, Role.HR_FINANCE, ["pdf", "sql"], 3)
    must_conditions = store.client.filter.must
    keys = {condition.key for condition in must_conditions}
    assert {"tenant_id", "allowed_roles", "classification", "source_type"}.issubset(keys)
