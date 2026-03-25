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
#   GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET   (for OAuth)
#   ZEP_API_KEY / ZEP_PROJECT_ID              (optional — local fallback available)
#   ASSEMBLYAI_API_KEY                        (for audio transcription)
#   FIRECRAWL_API_KEY                         (for web scraping)

# 3. Start all services
cd infra
docker compose -f docker-compose.prod.yml up --build -d

# 4. Verify health
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/
```

The stack starts:
- **Frontend** on port `3000` (nginx + SPA)
- **Backend API** on port `8000` (FastAPI + uvicorn)
- **RQ Worker** for background jobs (ingestion, podcasts)
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`
- **Milvus** on port `19530` (with etcd + MinIO)

## Environment Variables

See `.env.example` for the full list. Key groups:

### Required
| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | Secret for signing JWT tokens |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `MILVUS_URI` | Milvus vector DB endpoint |

### Optional (graceful fallback)
| Variable | Description |
|----------|-------------|
| `ZEP_API_KEY` | Zep cloud memory — falls back to local DB |
| `ZEP_PROJECT_ID` | Zep project UUID |
| `ASSEMBLYAI_API_KEY` | Audio transcription — feature disabled if missing |
| `FIRECRAWL_API_KEY` | Web scraping — feature disabled if missing |
| `ENABLE_CROSS_ENCODER_RERANK` | Enable cross-encoder reranking (`false` by default) |

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

### Multiple RQ workers

```bash
docker compose -f docker-compose.prod.yml up -d --scale rq-worker=4
```

## Monitoring

- **Health check**: `GET /api/v1/health` — returns dependency status
- **Readiness probe**: `GET /api/v1/health/readiness` — returns 503 if not ready
- **Metrics**: `GET /metrics` — Prometheus-compatible counters and histograms
- **Logs**: JSON-formatted to stdout — compatible with any log aggregator

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
