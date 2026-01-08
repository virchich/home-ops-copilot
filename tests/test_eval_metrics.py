"""Tests for eval format metric computation."""

import pytest

from eval.run_eval import EvalResult, compute_format_metrics


def make_result(
    question_id: int = 1,
    category: str = "hvac",
    has_answer: bool = True,
    has_risk_level: bool = True,
    risk_level_valid: bool = True,
    has_citations: bool = False,
    high_risk_recommends_pro: bool | None = None,
    answer_length: int = 500,
    answer_concise: bool = True,
    mentions_safety_for_dangerous: bool | None = None,
    error: str | None = None,
) -> EvalResult:
    """Factory function to create EvalResult with sensible defaults."""
    return EvalResult(
        question_id=question_id,
        category=category,
        question="Test question?",
        answer="Test answer" if not error else "",
        risk_level="LOW" if risk_level_valid else "",
        citations=[],
        contexts=[],
        has_answer=has_answer,
        has_risk_level=has_risk_level,
        risk_level_valid=risk_level_valid,
        has_citations=has_citations,
        high_risk_recommends_pro=high_risk_recommends_pro,
        answer_length=answer_length,
        answer_concise=answer_concise,
        mentions_safety_for_dangerous=mentions_safety_for_dangerous,
        error=error,
    )


class TestComputeFormatMetricsBasic:
    """Tests for basic format metrics."""

    def test_empty_results(self) -> None:
        """Should handle empty results list."""
        metrics = compute_format_metrics([])

        assert metrics["total_questions"] == 0
        assert metrics["successful_calls"] == 0
        assert metrics["error_rate"] == 0
        assert metrics["has_answer_rate"] == 0
        assert metrics["high_risk_recommends_pro_rate"] is None
        assert metrics["dangerous_mentions_safety_rate"] is None

    def test_all_successful(self) -> None:
        """Should compute correct rates when all calls succeed."""
        results = [make_result(question_id=i) for i in range(5)]
        metrics = compute_format_metrics(results)

        assert metrics["total_questions"] == 5
        assert metrics["successful_calls"] == 5
        assert metrics["error_rate"] == 0.0
        assert metrics["has_answer_rate"] == 1.0
        assert metrics["has_risk_level_rate"] == 1.0
        assert metrics["risk_level_valid_rate"] == 1.0

    def test_some_errors(self) -> None:
        """Should correctly compute error rate."""
        results = [
            make_result(question_id=1),
            make_result(question_id=2),
            make_result(question_id=3, error="API error"),
            make_result(question_id=4, error="Timeout"),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["total_questions"] == 4
        assert metrics["successful_calls"] == 2
        assert metrics["error_rate"] == 0.5

    def test_partial_format_compliance(self) -> None:
        """Should compute correct rates with mixed format compliance."""
        results = [
            make_result(question_id=1, has_answer=True, has_risk_level=True),
            make_result(question_id=2, has_answer=True, has_risk_level=False),
            make_result(question_id=3, has_answer=False, has_risk_level=True),
            make_result(question_id=4, has_answer=False, has_risk_level=False),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["has_answer_rate"] == 0.5
        assert metrics["has_risk_level_rate"] == 0.5


class TestComputeFormatMetricsCustom:
    """Tests for custom metrics (citations, conciseness)."""

    def test_citation_rate(self) -> None:
        """Should correctly compute citation rate."""
        results = [
            make_result(question_id=1, has_citations=True),
            make_result(question_id=2, has_citations=True),
            make_result(question_id=3, has_citations=False),
            make_result(question_id=4, has_citations=False),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["has_citations_rate"] == 0.5

    def test_concise_rate(self) -> None:
        """Should correctly compute conciseness rate."""
        results = [
            make_result(question_id=1, answer_concise=True, answer_length=500),
            make_result(question_id=2, answer_concise=True, answer_length=1000),
            make_result(question_id=3, answer_concise=False, answer_length=2500),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["answer_concise_rate"] == pytest.approx(2 / 3)

    def test_average_answer_length(self) -> None:
        """Should correctly compute average answer length."""
        results = [
            make_result(question_id=1, answer_length=100),
            make_result(question_id=2, answer_length=200),
            make_result(question_id=3, answer_length=300),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["avg_answer_length"] == 200.0


class TestComputeFormatMetricsConditional:
    """Tests for conditional metrics (high risk, dangerous categories)."""

    def test_high_risk_recommends_pro_all_recommend(self) -> None:
        """Should compute 100% when all HIGH risk answers recommend professional."""
        results = [
            make_result(question_id=1, high_risk_recommends_pro=True),
            make_result(question_id=2, high_risk_recommends_pro=True),
            make_result(question_id=3, high_risk_recommends_pro=None),  # Not HIGH risk
        ]
        metrics = compute_format_metrics(results)

        assert metrics["high_risk_recommends_pro_rate"] == 1.0
        assert metrics["high_risk_count"] == 2

    def test_high_risk_recommends_pro_partial(self) -> None:
        """Should compute partial rate when some HIGH risk don't recommend professional."""
        results = [
            make_result(question_id=1, high_risk_recommends_pro=True),
            make_result(question_id=2, high_risk_recommends_pro=False),
            make_result(question_id=3, high_risk_recommends_pro=None),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["high_risk_recommends_pro_rate"] == 0.5
        assert metrics["high_risk_count"] == 2

    def test_high_risk_recommends_pro_none_high_risk(self) -> None:
        """Should return None when no HIGH risk answers."""
        results = [
            make_result(question_id=1, high_risk_recommends_pro=None),
            make_result(question_id=2, high_risk_recommends_pro=None),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["high_risk_recommends_pro_rate"] is None
        assert metrics["high_risk_count"] == 0

    def test_dangerous_category_safety_mentions(self) -> None:
        """Should compute safety mention rate for dangerous categories."""
        results = [
            make_result(question_id=1, category="electrical", mentions_safety_for_dangerous=True),
            make_result(question_id=2, category="plumbing", mentions_safety_for_dangerous=False),
            make_result(question_id=3, category="hvac", mentions_safety_for_dangerous=None),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["dangerous_mentions_safety_rate"] == 0.5
        assert metrics["dangerous_category_count"] == 2

    def test_dangerous_category_none_dangerous(self) -> None:
        """Should return None when no dangerous category questions."""
        results = [
            make_result(question_id=1, category="hvac", mentions_safety_for_dangerous=None),
            make_result(question_id=2, category="appliances", mentions_safety_for_dangerous=None),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["dangerous_mentions_safety_rate"] is None
        assert metrics["dangerous_category_count"] == 0


class TestComputeFormatMetricsErrorHandling:
    """Tests for error handling in format metrics."""

    def test_errors_excluded_from_rates(self) -> None:
        """Errored results should not count toward success metrics."""
        results = [
            make_result(question_id=1, has_answer=True),
            make_result(question_id=2, has_answer=True, error="Failed"),
        ]
        metrics = compute_format_metrics(results)

        # Only 1 successful, and it has an answer
        assert metrics["successful_calls"] == 1
        assert metrics["has_answer_rate"] == 1.0

    def test_errors_excluded_from_conditional_metrics(self) -> None:
        """Errored results should not count toward conditional metrics."""
        results = [
            make_result(question_id=1, high_risk_recommends_pro=True),
            make_result(question_id=2, high_risk_recommends_pro=True, error="Failed"),
        ]
        metrics = compute_format_metrics(results)

        assert metrics["high_risk_count"] == 1
        assert metrics["high_risk_recommends_pro_rate"] == 1.0
