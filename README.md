# NotebookLM Clone

Document-grounded AI assistant with citations, memory, and podcast generation.

## Architecture
- FastAPI backend handles auth, ingestion, retrieval, memory, and generation APIs.
- React notebook workspace is the primary UI.
- Streamlit remains as a fallback UI during migration and debugging.
- Redis and RQ process background jobs such as ingestion and podcast generation.
- PostgreSQL, Alembic, and Milvus support structured state, migrations, and vector retrieval.

## Problem + Solution
### Problem
Notebook-style assistants often answer without citations and struggle with PDFs, web pages, audio, and other mixed inputs.

### Solution
Built a retrieval-first workspace that grounds responses in source documents, keeps conversation memory, and can turn source material into podcast-style output.

## Tech Stack
Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, RQ, Milvus, React, Vite, Tailwind, Streamlit, Kokoro TTS, Faster Whisper, Authlib, Google OAuth, Zep support.

## Local Setup
1. Create and activate the Python environment with `uv sync --all-extras`.
2. Copy `.env.example` to `.env` and run `uv run alembic upgrade head`.
3. Start infra with `docker compose -f infra/docker-compose.yml up -d`.
4. Run the backend with `uv run uvicorn app.main:app --app-dir src/backend --host 0.0.0.0 --port 8000 --reload`.
5. Start the React workspace with `cd src/frontend-web && npm install && npm run dev`.
