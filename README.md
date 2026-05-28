<div align="center">

# Enterprise Secure RAG Assistant

Production-oriented Retrieval-Augmented Generation for secure enterprise knowledge access.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-0B5CAD?style=for-the-badge)](https://enterprise-rag-01b7.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA%20NIM-AI%20Models-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com/)

![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-DC244C?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-Self%20Contained-003B57?style=flat-square&logo=sqlite&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Data%20Layer-D71F00?style=flat-square)
![RBAC](https://img.shields.io/badge/RBAC-Enforced-0B5CAD?style=flat-square)
![PII Guardrails](https://img.shields.io/badge/PII%20Guardrails-Enabled-0B5CAD?style=flat-square)

</div>

## Overview

Enterprise Secure RAG Assistant is a Dockerized Streamlit application that retrieves from PDFs, SQLite tables, and JSON audit logs while enforcing role-based access control before retrieval and before SQL execution.

Live application:

```text
https://enterprise-rag-01b7.onrender.com
```

## Capabilities

- PDF, SQLite, and JSON log retrieval.
- NVIDIA NIM integrations for embeddings, dynamic routing, reranking, safety checks, and answer synthesis.
- Dual embeddings with `nvidia/nv-embed-v1` and `nvidia/nv-embedcode-7b-v1`.
- Qdrant local vector store with hard payload filters for RBAC.
- Dynamic Qwen-generated SQLite `SELECT` queries using only role-approved schemas.
- PII redaction and content guardrails on input and output.
- Synthetic enterprise data generation for zero-configuration demos.
- Dockerized deployment on Render.
- Graceful handling for temporary hosted-model capacity errors.

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

LIVE Demo: https://enterprise-rag-01b7.onrender.com/
