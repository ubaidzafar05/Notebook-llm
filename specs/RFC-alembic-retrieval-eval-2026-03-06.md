# RFC: Alembic Migration Cutover + Retrieval Eval Harness (2026-03-06)

## Goal
Close remaining release blockers by (1) removing runtime model-driven schema bootstrap and enforcing Alembic-first schema management, and (2) adding a deterministic retrieval evaluation harness with explicit pass/fail thresholds.

## Scope
- Add Alembic config and initial migration matching current runtime schema.
- Replace `init_db()` runtime `create_all` behavior with Alembic upgrade execution.
- Update tests to reset DB through migrations (not ORM metadata creation).
- Add retrieval golden set + evaluator for top-k support and citation-integrity checks.

## Options
1. Manual DB migrations only (startup fails if pending)  
   - Pros: strict ops discipline.  
   - Cons: more local friction and onboarding errors.
2. Auto-run Alembic upgrade at startup (recommended)  
   - Pros: deterministic and no drift; still migration-driven.
   - Cons: schema changes apply at boot; requires migration hygiene.
3. Keep runtime `create_all` plus Alembic for prod  
   - Pros: simplest dev loop.  
   - Cons: split behavior and drift risk; rejected.

## Decision
Adopt option 2. Runtime schema changes are Alembic-only. Startup runs `upgrade head` idempotently, and tests reset through migrations.

## Confidence
- Alembic cutover: High.
- Retrieval eval harness threshold quality signal: Medium (assumption: golden set size will expand over time).

## Risks
- Mis-modeled initial migration could miss legacy local DB edge cases.
- Retrieval eval can be gamed if golden set is too small.

## Mitigations
- Add migration-aware startup/preflight checks and run full quality gates.
- Keep dataset explicit and versioned; require threshold assertions in CI tests.
