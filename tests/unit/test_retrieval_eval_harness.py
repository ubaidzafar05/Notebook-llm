from __future__ import annotations

from pathlib import Path

from scripts.retrieval_eval import CITATION_THRESHOLD, SUPPORT_THRESHOLD, evaluate_golden_set


def test_retrieval_eval_golden_set_meets_thresholds() -> None:
    golden_path = Path(__file__).resolve().parents[1] / "evals" / "retrieval_golden.json"
    summary = evaluate_golden_set(golden_path=golden_path)

    assert summary.total_cases >= 8
    assert summary.support_rate >= SUPPORT_THRESHOLD
    assert summary.citation_integrity_rate >= CITATION_THRESHOLD
    assert summary.passed is True
