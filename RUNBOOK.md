# Operations Runbook

## Service Architecture

```
[nginx :3000] → [FastAPI :8000] → [PostgreSQL :5432]
                      ↓                    ↑
                  [RQ Worker] ←→ [Redis :6379]
                      ↓
                [Milvus :19530]
```

## Common Issues

### Backend won't start

| Symptom | Cause | Fix |
|---------|-------|-----|
| `REDIS_UNAVAILABLE` | Redis not running | `docker compose up redis -d` |
| `Milvus unavailable` | Milvus or etcd down | Check `docker logs notebooklm-milvus` |
| `Zep credentials missing` | ZEP_API_KEY not set | Set in `.env` or ignore (local fallback active) |
| Port 8000 in use | Another process on port | `lsof -i :8000` and stop conflicting process |

### Ingestion jobs stuck

```bash
# Check RQ queue
docker exec notebooklm-backend rq info --url redis://redis:6379/0

# Check worker logs
docker logs notebooklm-rq-worker --tail 100

# Retry failed jobs
docker exec notebooklm-backend rq requeue --all --url redis://redis:6379/0
```

### Podcast generation fails

1. Check Kokoro TTS is installed: `docker exec notebooklm-backend python -c "import kokoro"`
2. Check ffmpeg: `docker exec notebooklm-backend ffmpeg -version`
3. Check disk space in `/app/outputs/podcasts/`
4. Check circuit breaker state in logs: search for `circuit_breaker`

### Database migration fails

```bash
# Check current revision
docker exec notebooklm-backend alembic current

# Show migration history
docker exec notebooklm-backend alembic history

# Downgrade one step
docker exec notebooklm-backend alembic downgrade -1

# Re-apply
docker exec notebooklm-backend alembic upgrade head
```

### Memory / Zep issues

- Zep is **optional** — if unreachable, MemoryService falls back to local DB summaries
- Check Zep status: `GET /api/v1/health/dependencies` → look at `zep.status`
- Verify API key: `curl -H "Authorization: Api-Key $ZEP_API_KEY" https://api.getzep.com/api/v2/projects/info`

### High latency

1. Check `/metrics` for `http_request_duration_seconds`
2. Check Milvus query latency: `GET /api/v1/health/dependencies` → `milvus.latency_ms`
3. Check Redis cache hit rate in logs: search for `SemanticCache hit`
4. Consider enabling cross-encoder rerank: set `ENABLE_CROSS_ENCODER_RERANK=true`

## Restart Procedures

### Graceful restart (zero downtime)
```bash
cd infra
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker compose -f docker-compose.prod.yml up -d --no-deps --build rq-worker
docker compose -f docker-compose.prod.yml up -d --no-deps --build frontend
```

### Full restart
```bash
cd infra
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Database Restore

```bash
# Stop backend and worker
docker compose -f docker-compose.prod.yml stop backend rq-worker

# Restore from backup
cat backup.sql | docker exec -i notebooklm-postgres psql -U notebooklm notebooklm

# Restart
docker compose -f docker-compose.prod.yml up -d backend rq-worker
```

## Log Analysis

Logs are JSON-formatted. Use `jq` for filtering:

```bash
# All errors in last hour
docker logs notebooklm-backend --since 1h 2>&1 | jq 'select(.level == "ERROR")'

# Slow requests (>2s)
docker logs notebooklm-backend --since 1h 2>&1 | jq 'select(.level == "WARNING")'

# Search by request ID
docker logs notebooklm-backend 2>&1 | jq 'select(.correlation_id == "REQUEST_ID_HERE")'
```
