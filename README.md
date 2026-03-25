# NotebookLM Clone

Open-source notebook-style AI assistant grounded in your documents with verifiable citations.

## Features
- Multi-user authentication (JWT + Google OAuth)
- Ingestion for PDF, text, markdown, audio, YouTube, and websites
- Retrieval-augmented chat with citations
- Provider failover (Ollama primary, OpenRouter fallback)
- Conversation memory with Zep support
- Podcast generation from source context with Kokoro TTS
- React notebook workspace on port `3000`
- Streamlit fallback UI during migration

## Local Setup
1. Create and activate environment:
   ```bash
   uv venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   uv sync --all-extras
   ```
   Use the project-local environment only:
   ```bash
   source .venv/bin/activate
   ```
3. Copy env template:
   ```bash
   cp .env.example .env
   ```
4. Apply DB migrations (Alembic-first schema management):
   ```bash
   uv run alembic upgrade head
   ```
   If you are upgrading from an old local SQLite scaffold, reset once first:
   ```bash
   rm -f notebooklm_dev.db && uv run alembic upgrade head
   ```
5. Start infrastructure:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
6. Optional: start RQ worker container profile:
   ```bash
   docker compose -f infra/docker-compose.yml --profile workers up -d rq-worker
   ```
7. Run backend:
   ```bash
   uv run uvicorn app.main:app --app-dir src/backend --host 0.0.0.0 --port 8000 --reload
   ```
8. Run the React workspace on port 3000:
   ```bash
   cd src/frontend-web
   npm install
   npm run dev
   ```
9. Optional fallback: run Streamlit UI on port 3000 instead of the React workspace:
   ```bash
   uv run streamlit run src/frontend/streamlit_app.py --server.port 3000
   ```
   Streamlit may warn that port `3000` is reserved; in this project that warning is expected and non-blocking.
10. Run preflight checks before daily use:
   ```bash
   uv run python scripts/preflight.py
   ```
   Preflight now fails if `kokoro` is unavailable, because podcast TTS is Kokoro-only.

## Google OAuth Configuration
- OAuth client type: Web Application
- Authorized JavaScript origin: `http://localhost:3000`
- Authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
- UI flow:
  - `GET /api/v1/auth/google/start` returns provider URL
  - Google redirects to backend callback
  - Backend callback redirects to UI with short-lived `oauth_code`
  - UI exchanges code at `POST /api/v1/auth/google/exchange`

## API Overview
All responses use:
```json
{ "data": {}, "error": { "code": "", "message": "" }, "meta": { "request_id": "" } }
```

## New APIs
- `GET /api/v1/sources/{source_id}/chunks?limit=50&offset=0`
- `POST /api/v1/podcasts/{podcast_id}/retry`
- `GET /api/v1/health/readiness`

## Health and Startup Checks
- `GET /api/v1/health` returns overall state plus dependency statuses.
- `GET /api/v1/health/dependencies` returns per-service status:
  - `postgres`
  - `redis`
  - `milvus`
  - `zep`
  - `ollama`
  - `openrouter`
  - `provider_gate`
- Startup runs dependency checks and logs degraded mode when required services are unavailable.
- `GET /api/v1/health/readiness` is the release-gate endpoint:
  - `200` with `status=ready` when required deps (`postgres`, `redis`, `milvus`, `zep`, `provider_gate`) are healthy
  - `503` with `status=not_ready` otherwise

## Zep (Optional)
- Zep is **optional** — missing credentials trigger a warning, not a crash.
- When Zep is unavailable, memory operations fall back to local DB summaries.
- For full temporal knowledge graph memory, set `ZEP_API_KEY` and `ZEP_PROJECT_ID`.

## Provider Fallback Behavior
- Primary generation path: Ollama (`OLLAMA_BASE_URL` + model config).
- Fallback path: OpenRouter when Ollama fails or is unavailable.
- Health endpoint exposes provider reachability so failures can be diagnosed before runtime.
- `OPENROUTER_API_KEY` is optional, but fallback is disabled when not set.

## Podcast TTS
- Podcast synthesis is Kokoro-only (`PODCAST_TTS_PROVIDER=kokoro`).
- Required env keys:
  - `KOKORO_VOICE_HOST`
  - `KOKORO_VOICE_ANALYST`
- If Kokoro is unavailable at runtime, podcast jobs fail with typed errors:
  - `KOKORO_UNAVAILABLE`
  - `KOKORO_SYNTH_FAILED`
  - `KOKORO_DEPENDENCY_MISSING`

## Queue and Worker Behavior
- Queue mode is strict Redis/RQ. Ingestion and podcast creation do not fall back to in-process background tasks.
- Queue outage returns typed `503 QUEUE_UNAVAILABLE`.
- Job payload includes:
  - `queue_job_id`
  - `queue_name`
  - `dead_lettered`
  - `failure_code`
  - `cancel_requested`
- Local worker command:
  ```bash
  uv run rq worker "${RQ_QUEUE_NAME:-notebooklm-default}" --url "${REDIS_URL:-redis://localhost:6379/0}"
  ```
- DLQ inspection command:
  ```bash
  uv run rq info --url "${REDIS_URL:-redis://localhost:6379/0}"
  ```

## Auth State Store
- OAuth state, OAuth exchange code, and refresh revocation are Redis-backed with TTL and one-time consume semantics.
- If Redis is unavailable, auth state-sensitive routes fail closed with typed `503 AUTH_STATE_UNAVAILABLE`.

## Retrieval Controls
- Default rerank strategy is lexical overlap.
- Optional cross-encoder reranking can be enabled:
  - `ENABLE_CROSS_ENCODER_RERANK=true`
  - `CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2`
- Citation integrity guard removes any citation whose `chunk_id` is not present in retrieved chunks.

## Ingestion Failure Taxonomy
| Source Type | Failure Codes |
| --- | --- |
| PDF | `PDF_OPEN_FAILED`, `PDF_EMPTY`, `PDF_PARSE_FAILED` |
| WEB | `WEB_FETCH_FAILED`, `WEB_TIMEOUT`, `WEB_PARSE_FAILED` |
| YOUTUBE | `YOUTUBE_FETCH_FAILED`, `YOUTUBE_SUBTITLE_MISSING`, `YOUTUBE_AUDIO_DOWNLOAD_FAILED`, `YOUTUBE_TRANSCRIBE_FAILED` |
| AUDIO | `AUDIO_PARSE_FAILED`, `AUDIO_TIMEOUT`, `AUDIO_UPSTREAM_FAILED` |

## Test Commands
```bash
uv run pytest -q
uv run mypy
uv run ruff check .
uv run python scripts/retrieval_eval.py
cd src/frontend-web && npm test && npm run build
```

## Release Checklist
Use this before calling the project production-ready for daily use.

1. Dependency readiness:
   ```bash
   curl -s http://localhost:8000/api/v1/health/readiness
   ```
   Must return `200` and `data.status=ready`.
2. Quality gates:
   ```bash
   uv run ruff check .
   uv run mypy
   uv run pytest -q
   cd src/frontend-web && npm test && npm run build
   ```
3. Worker gate:
   - RQ worker is running on `${RQ_QUEUE_NAME:-notebooklm-default}` and Redis is reachable.
4. User journey gate:
   - Register/login works.
   - Upload source -> ingestion completes with no failed job.
   - Chat response returns citations and final SSE fields (`content`, `citations`, `model_info`, `confidence`).
   - Podcast create + retry paths both complete and audio download succeeds.

## Troubleshooting Matrix
| Symptom | Likely Cause | What to Check | Fix |
| --- | --- | --- | --- |
| Google login returns to UI but no session | Invalid callback/origin config or expired OAuth code | Google console origins/redirect URI, backend logs, `oauth_code` age | Set exact localhost values, retry sign-in |
| Google auth endpoints return 503 | Redis unavailable for auth state store | `GET /api/v1/health/dependencies` for `redis`, backend logs | Restore Redis; auth routes fail closed by design |
| Chat fails with model/provider errors | Ollama not running and OpenRouter unavailable | `GET /api/v1/health/dependencies` for `ollama`, `openrouter`, and `provider_gate` | Start Ollama or configure valid `OPENROUTER_API_KEY` |
| Upload/podcast create fails with 503 | Queue strict mode + Redis/RQ outage | `GET /api/v1/health/dependencies` for `redis`, `rq worker` process | Restore Redis/RQ worker and retry |
| Citations missing in final answer | Retrieved set had no valid citation anchors | Chat final SSE payload `citations` and source chunk state | Re-ingest source or narrow source filters |
| Podcast never reaches completed | TTS/audio pipeline failure | Podcast job `failure_code` and `failure_detail` | Validate source text availability and retry via `/podcasts/{id}/retry` |

## Security Notes
- Secrets are environment-only (`.env`) and must never be committed.
- OAuth callback no longer places bearer tokens in browser URL parameters.

## Changelog
- **v1.0.0** — Production-ready release
  - Everforest light/dark theme (CSS variable architecture)
  - Hardened MemoryService with graceful Zep fallback to local DB
  - Targeted semantic cache invalidation via Redis reverse index
  - Prometheus metrics endpoint (`GET /metrics`)
  - Non-root Docker containers with HEALTHCHECK
  - CI pipeline: lint → test → build → Docker build → security scan
  - 52 backend tests, 10 frontend tests
  - Zep made optional (warns, doesn't crash)
  - Deployment guide (`DEPLOY.md`) and operations runbook (`RUNBOOK.md`)
- Added full greenfield scaffold for FastAPI backend + Streamlit UI with dual LLM routing.
- Implemented authentication (JWT + Google OAuth), source ingestion, chat, memory, and podcast endpoints.
- Added notebook-centered React workspace with notebook, source, chat, and studio panels.
- Added local infrastructure compose stack (Postgres, Redis, Milvus) and baseline test suite.
