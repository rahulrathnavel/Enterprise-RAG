from src.rag.embeddings import NvidiaEmbeddingClient


def test_remote_embedding_sends_nvidia_input_type() -> None:
    class FakeEmbeddingResource:
        def __init__(self) -> None:
            self.kwargs = {}

        def create(self, **kwargs):
            self.kwargs = kwargs
            item = type("EmbeddingItem", (), {"embedding": [0.1, 0.2]})
            return type("EmbeddingResponse", (), {"data": [item]})

    class FakeClient:
        def __init__(self) -> None:
            self.embeddings = FakeEmbeddingResource()

    client = FakeClient()
    embedding_client = NvidiaEmbeddingClient.__new__(NvidiaEmbeddingClient)

    vectors = embedding_client._remote_embed(client, "nvidia/nv-embed-v1", ["policy text"], "passage")

    assert vectors == [[0.1, 0.2]]
    assert client.embeddings.kwargs["extra_body"] == {"input_type": "passage"}
