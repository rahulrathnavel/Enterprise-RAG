from src.rag.retriever import EnterpriseRetriever
from src.rag.types import RouteDecision
from src.security.rbac import Role


class TimeoutLikeError(Exception):
    pass


def test_retriever_continues_when_one_embedding_collection_times_out() -> None:
    retriever = EnterpriseRetriever.__new__(EnterpriseRetriever)
    retriever.settings = type(
        "Settings",
        (),
        {
            "qdrant_text_collection": "enterprise_text",
            "qdrant_code_collection": "enterprise_code_logs",
            "max_retrieval_results": 8,
            "rerank_top_n": 5,
        },
    )()

    class Embeddings:
        def embed_texts(self, texts, input_type):
            raise TimeoutLikeError("Request timed out.")

        def embed_code_texts(self, texts, input_type):
            return [[0.0, 1.0]]

    class Store:
        def search(self, **kwargs):
            return []

    class Reranker:
        def rerank(self, query, chunks, top_n):
            return chunks

    retriever.embeddings = Embeddings()
    retriever.store = Store()
    retriever.reranker = Reranker()

    route = RouteDecision(source_types=["sql"], requires_sql=True, rationale="test")
    assert retriever.retrieve("incident evidence", Role.ADMIN, route) == []
