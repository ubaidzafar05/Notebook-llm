from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.retrieval.citation_guard import filter_citations_by_chunk_ids
from app.retrieval.reranker import rerank
from app.vector_store.collections import VectorRecord
from schemas.citation import Citation

SUPPORT_THRESHOLD = 0.85
CITATION_THRESHOLD = 1.0
DEFAULT_GOLDEN_PATH = Path(__file__).resolve().parents[1] / "tests" / "evals" / "retrieval_golden.json"


@dataclass(slots=True)
class GoldenCaseResult:
    case_id: str
    support_hit: bool
    citation_integrity_pass: bool
    top_chunk_ids: list[str]
    filtered_citation_chunk_ids: list[str]


@dataclass(slots=True)
class RetrievalEvalSummary:
    total_cases: int
    support_rate: float
    citation_integrity_rate: float
    support_threshold: float
    citation_threshold: float
    passed: bool
    case_results: list[GoldenCaseResult]


def evaluate_golden_set(golden_path: Path = DEFAULT_GOLDEN_PATH) -> RetrievalEvalSummary:
    payload = _load_payload(golden_path)
    case_results: list[GoldenCaseResult] = []

    for case in payload:
        query = _require_str(case, "query")
        case_id = _require_str(case, "id")
        expected_chunk_ids = set(_require_string_list(case, "expected_chunk_ids"))
        proposed_citation_chunk_ids = _require_string_list(case, "proposed_citation_chunk_ids")

        candidates = _to_candidates(case)
        reranked = rerank(query=query, candidates=candidates, final_k=5)
        top_chunk_ids = [record.chunk_id for record in reranked]
        support_hit = bool(expected_chunk_ids.intersection(top_chunk_ids))

        proposed_citations = [
            Citation(source_id="eval-source", chunk_id=chunk_id, excerpt="eval")
            for chunk_id in proposed_citation_chunk_ids
        ]
        filtered = filter_citations_by_chunk_ids(proposed_citations, set(top_chunk_ids))
        filtered_ids = [item.chunk_id for item in filtered]
        citation_integrity_pass = all(chunk_id in top_chunk_ids for chunk_id in filtered_ids)

        case_results.append(
            GoldenCaseResult(
                case_id=case_id,
                support_hit=support_hit,
                citation_integrity_pass=citation_integrity_pass,
                top_chunk_ids=top_chunk_ids,
                filtered_citation_chunk_ids=filtered_ids,
            )
        )

    support_rate = _rate([result.support_hit for result in case_results])
    citation_integrity_rate = _rate([result.citation_integrity_pass for result in case_results])
    passed = support_rate >= SUPPORT_THRESHOLD and citation_integrity_rate >= CITATION_THRESHOLD
    return RetrievalEvalSummary(
        total_cases=len(case_results),
        support_rate=support_rate,
        citation_integrity_rate=citation_integrity_rate,
        support_threshold=SUPPORT_THRESHOLD,
        citation_threshold=CITATION_THRESHOLD,
        passed=passed,
        case_results=case_results,
    )


def main() -> int:
    summary = evaluate_golden_set()
    print(
        json.dumps(
            {
                "total_cases": summary.total_cases,
                "support_rate": round(summary.support_rate, 4),
                "citation_integrity_rate": round(summary.citation_integrity_rate, 4),
                "support_threshold": summary.support_threshold,
                "citation_threshold": summary.citation_threshold,
                "passed": summary.passed,
                "case_results": [asdict(case) for case in summary.case_results],
            },
            indent=2,
        )
    )
    return 0 if summary.passed else 1


def _load_payload(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Golden retrieval file must be a list")
    return [item for item in raw if isinstance(item, dict)]


def _to_candidates(case: dict[str, Any]) -> list[VectorRecord]:
    raw_candidates = case.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError(f"Case {case.get('id', '<unknown>')} candidates must be a list")

    candidates: list[VectorRecord] = []
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            continue
        chunk_id = _require_str(raw, "chunk_id")
        source_id = _require_str(raw, "source_id")
        text = _require_str(raw, "text")
        candidates.append(
            VectorRecord(
                chunk_id=chunk_id,
                source_id=source_id,
                user_id="eval-user",
                notebook_id="eval-notebook",
                text=text,
                vector=[],
                metadata={},
            )
        )
    if not candidates:
        raise ValueError(f"Case {case.get('id', '<unknown>')} has zero candidates")
    return candidates


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid field: {key}")
    return value


def _require_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Missing or invalid list field: {key}")
    result = [item for item in value if isinstance(item, str) and item]
    if not result:
        raise ValueError(f"Field {key} must contain at least one non-empty string")
    return result


def _rate(items: list[bool]) -> float:
    if not items:
        return 0.0
    return sum(1 for value in items if value) / len(items)


if __name__ == "__main__":
    raise SystemExit(main())
