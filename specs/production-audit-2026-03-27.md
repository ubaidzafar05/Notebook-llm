# Production Audit — 2026-03-27

## Scope
- Backend correctness
- Retrieval and generation stability
- Podcast job runtime stability
- Docker production runtime
- Frontend workspace and notebooks UX regressions

## Acceptance Bar
- Core flows work end-to-end in Docker
- No silent broken happy path remains
- Failure states are explicit
- Health/readiness reflect actual runtime state
- Backend tests pass
- Frontend typecheck/build pass

## Fixed

### LLM and retrieval
- Ollama remains the only active generation provider.
- `qwen3:8b` requests now disable hidden reasoning so empty-content responses are less likely.
- Blank model output now falls back to extractive answer synthesis instead of emitting a broken `Sources:` style answer.
- Support gating now accepts valid grounded listing questions when a single strong source supports the answer.
- Chat/export paths now carry richer retrieval context for report generation.

### Source ingestion and retrieval usability
- Sources can no longer surface as effectively usable when parsing/chunking produced no retrievable content.
- Workspace source selection now prefers retrievable sources and blocks misleading chat attachment state.

### Podcast pipeline
- Worker restart recovery now marks stale `processing` podcast jobs as failed with `PODCAST_WORKER_INTERRUPTED`.
- Kokoro runtime dependencies are now explicit:
  - spaCy English model is baked into the backend image
  - TTS startup validates spaCy model presence before Kokoro init
  - runtime no longer relies on hidden `spacy download` behavior inside a worker job
- Kokoro repo selection is explicit via config.
- TTS stage timeout increased to fit actual CPU runtime.
- Per-turn TTS progress logging added for operability.

### Runtime and health
- Backend health/readiness now reflects Ollama-only generation readiness.
- Worker healthcheck no longer depends on `pgrep`, which is absent in the slim image.
- Docker prod runtime now boots cleanly with healthy backend, frontend, worker, Postgres, Redis, and Milvus.

### Frontend product behavior
- Workspace sidebar behavior was stabilized to remove hide/show and scroll regressions.
- Notebook page CTA duplication was reduced.
- Long source titles and paths wrap safely in the affected views.

## Removed or effectively retired
- Runtime dependence on external hosted providers for the active generation path.
- Hidden Kokoro runtime package/model bootstrapping from within the worker process.

## Verified

### Tests
- Backend: `67 passed`
- Frontend: `npm run lint` passed
- Frontend: `npm run build` passed

### Docker runtime
- `docker compose -f infra/docker-compose.prod.yml up --build -d`
- `GET /api/v1/health` -> `ok`
- `GET /api/v1/health/readiness` -> `ready`

### End-to-end smoke
- register
- login
- notebook create
- source upload
- ingestion complete
- chat SSE complete with grounded answer
- markdown export
- pdf export
- podcast create
- podcast complete
- audio download

## Still risky but acceptable
- Podcast synthesis is CPU-heavy on the current local stack.
- First-run podcast completion is measured in minutes, not seconds.
- This is acceptable for the current single-node local Ollama/Kokoro design, but it is not high-throughput and will become a capacity limit before it becomes a correctness problem.

## Deferred
- No correctness blocker is deferred from this pass.
- Any next pass should focus on throughput and UX polish, not core production breakage.
