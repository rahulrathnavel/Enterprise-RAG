# Enterprise Dual-Embedding RAG Demo

Production-oriented Streamlit RAG application for an enterprise hackathon challenge.

## Capabilities

- PDF, SQLite, and JSON log retrieval.
- NVIDIA NIM integrations for embeddings, dynamic routing, reranking, safety checks, and answer synthesis.
- Dual embeddings with `nvidia/nv-embed-v1` and `nvidia/nv-embedcode-7b-v1`.
- Qdrant local vector store with hard payload filters for RBAC.
- Dynamic Qwen-generated SQLite `SELECT` queries using only role-approved schemas.
- PII redaction and content guardrails on input and output.
- Synthetic enterprise data generation for zero-configuration demos.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/generate_data.py
streamlit run app.py
```

Open `http://localhost:8501`.

## Configuration

Copy `.env.example` to `.env` and set the NVIDIA API keys. The application reads environment variables first, `.env` second, and `apis.txt`/`apiss.txt` only as a local fallback.

## Docker

```bash
docker compose up --build
```

For cloud deployment, configure real API keys as platform environment variables.
Never commit `.env`, `apis.txt`, or `apiss.txt`.

## Security Notes

The LLM is never the authorization boundary. RBAC is enforced before retrieval through Qdrant metadata filters and before SQL execution through table allowlists, query validation, and forbidden keyword rejection.
