# Deployment Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Service orchestration |
| Git | 2.40+ | Source control |

## Quick Start (Docker Compose)

```bash
# 1. Clone the repository
git clone https://github.com/ubaidzafar05/Notebook-llm.git
cd Notebook-llm

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set:
#   JWT_SECRET       (generate with: openssl rand -hex 32)
#   OLLAMA_BASE_URL                           (defaults to host.docker.internal:11434 in compose)
#   OLLAMA_CHAT_MODEL                         (defaults to qwen3:8b)
#   GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET   (for OAuth)
#   ZEP_API_KEY / ZEP_PROJECT_ID              (optional — local fallback available)
#   ASSEMBLYAI_API_KEY                        (for audio transcription)
#   FIRECRAWL_API_KEY                         (for web scraping)

# 2a. Make sure Ollama is running on the Docker host
ollama serve
ollama pull qwen3:8b
ollama list

# 3. Start all services
cd infra
docker compose -f docker-compose.prod.yml up --build -d

# 4. Verify health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/readiness
curl http://localhost:3000/
```

The stack starts:
- **Frontend** on port `3000` (nginx + SPA)
- **Backend API** on port `8000` (FastAPI + uvicorn)
- **Core worker** for ingestion and queue-backed notebook jobs
- **Two podcast workers** dedicated to podcast generation and TTS
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`
- **Milvus** on port `19530` (with etcd + MinIO)

## Environment Variables

See `.env.example` for the full list. Key groups:

### Required
| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | Secret for signing JWT tokens |
| `OLLAMA_BASE_URL` | Ollama endpoint reachable from the backend/worker runtime |
| `OLLAMA_CHAT_MODEL` | Local chat model tag (`qwen3:8b` recommended) |

### Optional (graceful fallback)
| Variable | Description |
|----------|-------------|
| `ZEP_API_KEY` | Zep cloud memory — falls back to local DB |
| `ZEP_PROJECT_ID` | Zep project UUID |
| `ASSEMBLYAI_API_KEY` | Audio transcription — feature disabled if missing |
| `FIRECRAWL_API_KEY` | Web scraping — feature disabled if missing |
| `ENABLE_CROSS_ENCODER_RERANK` | Enable cross-encoder reranking (`false` by default) |
| `KOKORO_PREWARM_ON_STARTUP` | Preload podcast TTS runtime and voices on worker startup (`true` by default) |
| `PODCAST_TTS_TIMEOUT_SECONDS` | CPU budget for podcast TTS stage (`600` by default) |

## Database Migrations

Migrations run automatically on startup via Alembic. For manual migration:

```bash
# Inside the backend container
docker exec -it notebooklm-backend alembic upgrade head

# Or from the project root
uv run alembic upgrade head
```

## Scaling

### Multiple API workers

```bash
# Override CMD to add workers
docker compose -f docker-compose.prod.yml up -d --scale backend=3
```

Update nginx upstream to load-balance across backend replicas.

### Worker topology

```bash
docker compose -f docker-compose.prod.yml up -d
```

- `rq-worker-core` handles ingestion and non-podcast background jobs.
- `rq-worker-podcast` and `rq-worker-podcast-2` are dedicated podcast workers.
- Podcast jobs no longer compete with ingestion work on the same queue.

## Monitoring

- **Health check**: `GET /api/v1/health` — returns dependency status
- **Readiness probe**: `GET /api/v1/health/readiness` — returns 503 if not ready
- **Podcast TTS readiness**: surfaced as the `kokoro` dependency inside health/readiness
- **Metrics**: `GET /metrics` — Prometheus-compatible counters and histograms
- **Logs**: JSON-formatted to stdout — compatible with any log aggregator

## Production Smoke Checklist

Run this after every fresh deployment:

```bash
curl http://localhost:8000/api/v1/health/readiness
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep notebooklm
```

Then verify the product path in the browser:
- register/login
- create notebook
- upload a small text source
- wait for ingestion to complete
- send one grounded chat query
- export markdown and pdf
- create a podcast and wait for audio download
- check `queue_name` on job payloads if debugging worker routing

## Operational Notes

- First podcast generation on a cold worker is CPU-heavy even with prewarm enabled.
- On the current local CPU stack, podcast generation is measured in minutes, not seconds.
- This is a throughput constraint, not a correctness issue.
- If the worker restarts mid-job, stale `processing` podcast rows are automatically marked failed with `PODCAST_WORKER_INTERRUPTED`.
- Use `python scripts/profile_podcast_tts.py` to benchmark local TTS throughput before changing synthesis concurrency.

## TLS / HTTPS

For production, terminate TLS at a load balancer or reverse proxy:

```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

Set `AUTH_COOKIE_SECURE=true` and `AUTH_COOKIE_SAMESITE=strict` in `.env` for HTTPS.

## Backup

### PostgreSQL
```bash
docker exec notebooklm-postgres pg_dump -U notebooklm notebooklm > backup.sql
```

### Redis
Redis is configured with AOF persistence. Data is in the `redis_data` volume.

### Milvus
Data is in the `milvus_data` volume. Snapshot the Docker volume for backup.

## Stopping / Restarting

```bash
cd infra
docker compose -f docker-compose.prod.yml down       # stop
docker compose -f docker-compose.prod.yml up -d       # restart
docker compose -f docker-compose.prod.yml down -v     # stop + delete volumes (data loss!)
```
