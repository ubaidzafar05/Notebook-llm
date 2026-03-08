# RFC: Stabilization Completion with Mandatory Zep

Date: 2026-03-06

## Context
Current scaffold is feature-complete but not operationally deterministic: tests depend on external DB/network state, readiness did not fully represent mandatory memory dependencies, and frontend auth failures were noisy for users.

Locked constraints:
- Keep architecture: FastAPI + Streamlit + Postgres + Redis + Milvus + RQ
- Keep model strategy: Ollama primary, OpenRouter fallback
- Make Zep mandatory for runtime memory behavior
- Keep Streamlit on `localhost:3000`

## Options
1. Soft stabilization
- Keep optional memory fallback and patch only test flakes.
- Pros: lowest short-term effort.
- Cons: runtime behavior diverges from production intent; hidden failures remain.

2. Runtime-hard + deterministic tests (recommended)
- Enforce Zep at startup/runtime, keep deterministic test stubs, and harden readiness/envelope/frontend diagnostics.
- Pros: production behavior is explicit while local tests stay stable and fast.
- Cons: stricter startup requirements.

3. Full external integration in all tests
- Remove all test stubs and require live providers for every suite.
- Pros: highest fidelity.
- Cons: brittle CI/local flow, frequent non-code failures.

## Recommendation
Choose option 2.

Confidence: High  
Assumption verified: deterministic test transport stubs can preserve contract coverage while keeping runtime behavior strict.

## Definition of Done
- Runtime startup fails without valid `ZEP_API_KEY` and UUID `ZEP_PROJECT_ID`.
- Readiness requires `postgres`, `redis`, and `zep`.
- Validation and AppError responses always use envelope shape with optional details.
- Streamlit validates auth inputs client-side and surfaces dependency status/error details.
- Preflight script reports machine-readable dependency checks and fails on required dependency outages.
- `ruff`, `mypy`, and `pytest` pass with deterministic local test configuration.
