# RFC: Phase 6 Completion and Release Gates

Date: 2026-03-05

## Context
The scaffold is functionally complete and Phase 4/5 reliability + UX contracts are implemented. The remaining risk is release confidence: validating full user-journey behavior in one deterministic flow and documenting strict go-live gates.

## Options
1. Minimal gate
- Keep unit/integration tests only.
- Pros: fastest.
- Cons: no single regression signal for full auth -> ingestion -> chat -> podcast lifecycle.

2. End-to-end contract gate (recommended)
- Add deterministic e2e test that exercises the complete user flow with strict queue semantics preserved.
- Add explicit release checklist in README mapped to required health/test gates.
- Pros: strongest confidence for daily use readiness with low implementation risk.
- Cons: slightly longer test runtime.

3. External-only staging gate
- Rely on manual staging runs with real Redis/Milvus/Ollama/OpenRouter.
- Pros: realistic environment validation.
- Cons: slower feedback, flaky for local development, not CI-friendly.

## Recommendation
Choose Option 2.

Confidence: High
- Assumption validated: local deterministic queue monkeypatch can preserve production API behavior while removing external runtime flakiness.

## Definition of Done
- A single e2e test covers:
  - register/login
  - source upload + ingestion completion
  - chat SSE final event schema and citation integrity
  - podcast create/get/audio + retry lineage
- README contains an explicit release checklist with hard pass criteria.
