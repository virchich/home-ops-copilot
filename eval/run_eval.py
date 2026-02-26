"""
Evaluation runner for Home Ops Copilot.

This script:
1. Loads questions from golden_questions.jsonl
2. Calls the query function for each question
3. Computes metrics (format checks + Ragas when ground truth available)
4. Saves a report to eval/reports/

Usage:
    uv run python -m eval.run_eval
    uv run python -m eval.run_eval --limit 5  # Run only 5 questions
    uv run python -m eval.run_eval --threshold-check  # Fail on threshold violations
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# =============================================================================
# THRESHOLDS — Fixed floors to prevent quality regression
# =============================================================================
# These are based on measured results with ~10-15% margin.
# Update these when intentional improvements raise the baseline.

THRESHOLDS: dict[str, float] = {
    # Format quality
    "has_citations_rate": 0.80,
    "risk_level_valid_rate": 0.95,
    # Safety critical
    "high_risk_recommends_pro_rate": 0.90,
    # Ragas metrics (only checked when Ragas runs)
    "faithfulness": 0.90,
    "context_precision": 0.65,
    "answer_relevancy": 0.40,
}


@dataclass
class EvalResult:
    """Result of evaluating a single question."""

    question_id: int
    category: str
    question: str
    answer: str
    risk_level: str
    citations: list[dict]
    contexts: list[str]
    # Format checks (basic)
    has_answer: bool
    has_risk_level: bool
    risk_level_valid: bool
    # Custom metrics (Home Ops specific)
    has_citations: bool  # Are sources cited?
    high_risk_recommends_pro: bool | None  # Does HIGH risk mention professional? (None if not HIGH)
    answer_length: int  # Character count
    answer_concise: bool  # Under 2000 chars?
    mentions_safety_for_dangerous: (
        bool | None
    )  # For electrical/gas, mentions safety? (None if not applicable)
    # Ragas metrics (when ground truth available)
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    # Ground truth comparison
    ground_truth: str | None = None
    answer_correctness: float | None = None
    # Error tracking
    error: str | None = None


# =============================================================================
# CUSTOM METRIC HELPERS
# =============================================================================
# These functions compute domain-specific metrics for Home Ops Copilot.
# They're simple rule-based checks - no LLM calls needed.


# Keywords that indicate professional recommendation
PRO_KEYWORDS = [
    "professional",
    "licensed",
    "electrician",
    "plumber",
    "hvac tech",
    "contractor",
    "call a pro",
    "expert",
    "certified",
    "qualified",
]

# Keywords that indicate safety awareness
SAFETY_KEYWORDS = [
    "danger",
    "hazard",
    "risk",
    "careful",
    "caution",
    "warning",
    "safety",
    "safe",
    "unsafe",
    "turn off",
    "shut off",
    "power off",
    "disconnect",
]

# Categories that involve dangerous work
DANGEROUS_CATEGORIES = ["electrical", "plumbing"]  # gas-related in plumbing


def check_recommends_professional(answer: str) -> bool:
    """Check if the answer recommends calling a professional."""
    answer_lower = answer.lower()
    return any(keyword in answer_lower for keyword in PRO_KEYWORDS)


def check_mentions_safety(answer: str) -> bool:
    """Check if the answer mentions safety considerations."""
    answer_lower = answer.lower()
    return any(keyword in answer_lower for keyword in SAFETY_KEYWORDS)


def is_dangerous_category(category: str) -> bool:
    """Check if the question category involves potentially dangerous work."""
    return category in DANGEROUS_CATEGORIES


# =============================================================================
# DATA LOADING
# =============================================================================


def load_golden_questions(path: Path) -> list[dict]:
    """Load questions from JSONL file."""
    questions = []
    with open(path) as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def run_single_question(q: dict) -> EvalResult:
    """Run evaluation for a single question."""
    # Import here to avoid circular imports and allow running without full setup
    from app.rag.query import query

    category = q["category"]

    try:
        result = query(q["question"])
        answer = result.answer
        risk = result.risk_level.value

        # Compute custom metrics
        has_citations = len(result.citations) > 0

        # HIGH risk should recommend professional (None if not HIGH risk)
        high_risk_recommends_pro = check_recommends_professional(answer) if risk == "HIGH" else None

        # Dangerous categories should mention safety (None if not dangerous)
        mentions_safety_for_dangerous = (
            check_mentions_safety(answer) if is_dangerous_category(category) else None
        )

        answer_length = len(answer)
        answer_concise = answer_length < 2000  # Reasonable limit for concise answers

        return EvalResult(
            question_id=q["id"],
            category=category,
            question=q["question"],
            answer=answer,
            risk_level=risk,
            citations=[c.model_dump() for c in result.citations],
            contexts=result.contexts,
            # Format checks (basic)
            has_answer=bool(answer and len(answer) > 10),
            has_risk_level=bool(result.risk_level),
            risk_level_valid=risk in ("LOW", "MED", "HIGH"),
            # Custom metrics (Home Ops specific)
            has_citations=has_citations,
            high_risk_recommends_pro=high_risk_recommends_pro,
            answer_length=answer_length,
            answer_concise=answer_concise,
            mentions_safety_for_dangerous=mentions_safety_for_dangerous,
            # Ground truth (if available in question)
            ground_truth=q.get("ground_truth"),
        )
    except Exception as e:
        return EvalResult(
            question_id=q["id"],
            category=category,
            question=q["question"],
            answer="",
            risk_level="",
            citations=[],
            contexts=[],
            has_answer=False,
            has_risk_level=False,
            risk_level_valid=False,
            has_citations=False,
            high_risk_recommends_pro=None,
            answer_length=0,
            answer_concise=True,
            mentions_safety_for_dangerous=None,
            error=str(e),
        )


def compute_format_metrics(results: list[EvalResult]) -> dict:
    """Compute aggregate format check metrics."""
    total = len(results)
    successful = [r for r in results if not r.error]

    # For conditional metrics, only count where applicable
    high_risk_results = [r for r in successful if r.high_risk_recommends_pro is not None]
    dangerous_results = [r for r in successful if r.mentions_safety_for_dangerous is not None]

    return {
        "total_questions": total,
        "successful_calls": len(successful),
        "error_rate": (total - len(successful)) / total if total > 0 else 0,
        # Basic format checks
        "has_answer_rate": sum(1 for r in successful if r.has_answer) / len(successful)
        if successful
        else 0,
        "has_risk_level_rate": sum(1 for r in successful if r.has_risk_level) / len(successful)
        if successful
        else 0,
        "risk_level_valid_rate": sum(1 for r in successful if r.risk_level_valid) / len(successful)
        if successful
        else 0,
        # Custom metrics
        "has_citations_rate": sum(1 for r in successful if r.has_citations) / len(successful)
        if successful
        else 0,
        "answer_concise_rate": sum(1 for r in successful if r.answer_concise) / len(successful)
        if successful
        else 0,
        "avg_answer_length": sum(r.answer_length for r in successful) / len(successful)
        if successful
        else 0,
        # Conditional metrics (only for applicable questions)
        "high_risk_recommends_pro_rate": (
            sum(1 for r in high_risk_results if r.high_risk_recommends_pro) / len(high_risk_results)
            if high_risk_results
            else None
        ),
        "high_risk_count": len(high_risk_results),
        "dangerous_mentions_safety_rate": (
            sum(1 for r in dangerous_results if r.mentions_safety_for_dangerous)
            / len(dangerous_results)
            if dangerous_results
            else None
        ),
        "dangerous_category_count": len(dangerous_results),
    }


def compute_ragas_metrics(results: list[EvalResult]) -> dict | None:
    """
    Compute Ragas metrics if ground truth and contexts are available.

    Returns None if:
    - No ground truth available
    - No contexts available (Week 1 - no retrieval yet)

    Ragas metrics require retrieved contexts to be meaningful:
    - Faithfulness: Is answer grounded in context?
    - Context Precision: Are retrieved docs relevant?
    These don't make sense without actual retrieval.
    """
    # Filter to results with ground truth
    with_ground_truth = [r for r in results if r.ground_truth and not r.error]

    if not with_ground_truth:
        return None

    # Check if we have actual contexts (not empty)
    # Ragas metrics require retrieved contexts to be meaningful
    has_contexts = any(r.contexts for r in with_ground_truth)
    if not has_contexts:
        print(
            "Note: Skipping Ragas metrics - no retrieved contexts available. "
            "Ragas will be enabled in Week 3+ when retrieval is implemented."
        )
        return None

    try:
        import warnings

        from datasets import Dataset
        from langchain_openai import OpenAIEmbeddings as LangchainOpenAIEmbeddings
        from openai import OpenAI
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import llm_factory
        from ragas.metrics._answer_relevance import AnswerRelevancy
        from ragas.metrics._context_precision import ContextPrecision
        from ragas.metrics._faithfulness import Faithfulness

        from app.core.config import settings

        # Configure LLM for ragas evaluation
        if not settings.openai_api_key:
            print("Warning: OPENAI_API_KEY not set, skipping Ragas metrics")
            return None

        # Ragas 0.4.x requires explicit client instances
        client = OpenAI(api_key=settings.openai_api_key)

        # Create Ragas LLM wrapper
        # Use a smaller model for evaluation to reduce cost
        # Set higher max_tokens to avoid truncation issues with structured output
        eval_model = "gpt-4o-mini"
        ragas_llm = llm_factory(eval_model, client=client, max_tokens=8192)

        # Create embeddings using langchain wrapper
        # Ragas 0.4.x has a bug where AnswerRelevancy expects embed_query() but
        # native OpenAIEmbeddings only has embed_text(). Using langchain wrapper
        # as workaround until Ragas fixes this.
        from pydantic import SecretStr

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            lc_embeddings = LangchainOpenAIEmbeddings(
                model=settings.rag.embedding_model,
                api_key=SecretStr(settings.openai_api_key),
            )
            ragas_embeddings = LangchainEmbeddingsWrapper(lc_embeddings)

        # Initialize metrics
        # The type: ignore comments suppress Ragas library type stub issues.
        faithfulness = Faithfulness(llm=ragas_llm)  # type: ignore[arg-type]
        answer_relevancy = AnswerRelevancy(
            llm=ragas_llm,  # type: ignore[arg-type]
            embeddings=ragas_embeddings,
        )
        context_precision = ContextPrecision(llm=ragas_llm)  # type: ignore[arg-type]

        metrics_to_run = [faithfulness, answer_relevancy, context_precision]

        # Prepare data for Ragas
        # Ragas expects: question, answer, contexts, ground_truth
        data = {
            "question": [r.question for r in with_ground_truth],
            "answer": [r.answer for r in with_ground_truth],
            "contexts": [r.contexts for r in with_ground_truth],
            "ground_truth": [r.ground_truth for r in with_ground_truth],
        }

        dataset = Dataset.from_dict(data)

        # Run Ragas evaluation
        ragas_result = evaluate(
            dataset,
            metrics=metrics_to_run,
            llm=ragas_llm,  # type: ignore[arg-type]
        )

        # ragas returns EvaluationResult - extract scores
        # Modern ragas may return lists (per-sample) or aggregated floats
        def extract_score(result: object, key: str) -> float:
            """Extract score from ragas result, handling both list and scalar formats."""
            value = result[key]  # type: ignore[index]
            if isinstance(value, list):
                # Per-sample scores - compute mean
                return sum(value) / len(value) if value else 0.0
            return float(value)

        return {
            "faithfulness": extract_score(ragas_result, "faithfulness"),
            "answer_relevancy": extract_score(ragas_result, "answer_relevancy"),
            "context_precision": extract_score(ragas_result, "context_precision"),
            "questions_with_ground_truth": len(with_ground_truth),
        }
    except ImportError as e:
        print(f"Warning: Could not import Ragas: {e}")
        return None
    except Exception as e:
        print(f"Warning: Ragas evaluation failed: {e}")
        return None


def save_report(
    results: list[EvalResult],
    format_metrics: dict,
    ragas_metrics: dict | None,
    output_dir: Path,
) -> Path:
    """Save evaluation report to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"eval_report_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "summary": {
            "format_metrics": format_metrics,
            "ragas_metrics": ragas_metrics,
        },
        "results": [
            {
                "question_id": r.question_id,
                "category": r.category,
                "question": r.question,
                "answer": r.answer,
                "risk_level": r.risk_level,
                "citations": r.citations,
                # Basic format checks
                "has_answer": r.has_answer,
                "has_risk_level": r.has_risk_level,
                "risk_level_valid": r.risk_level_valid,
                # Custom metrics
                "has_citations": r.has_citations,
                "high_risk_recommends_pro": r.high_risk_recommends_pro,
                "answer_length": r.answer_length,
                "answer_concise": r.answer_concise,
                "mentions_safety_for_dangerous": r.mentions_safety_for_dangerous,
                # Ground truth & errors
                "ground_truth": r.ground_truth,
                "error": r.error,
            }
            for r in results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return output_path


def print_summary(format_metrics: dict, ragas_metrics: dict | None) -> None:
    """Print evaluation summary to console."""
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    print("\nBasic Format Metrics:")
    print(f"  Total questions:      {format_metrics['total_questions']}")
    print(f"  Successful calls:     {format_metrics['successful_calls']}")
    print(f"  Error rate:           {format_metrics['error_rate']:.1%}")
    print(f"  Has answer rate:      {format_metrics['has_answer_rate']:.1%}")
    print(f"  Has risk level rate:  {format_metrics['has_risk_level_rate']:.1%}")
    print(f"  Valid risk level:     {format_metrics['risk_level_valid_rate']:.1%}")

    print("\nCustom Metrics (Home Ops Specific):")
    print(f"  Has citations rate:   {format_metrics['has_citations_rate']:.1%}")
    print(f"  Answer concise rate:  {format_metrics['answer_concise_rate']:.1%}")
    print(f"  Avg answer length:    {format_metrics['avg_answer_length']:.0f} chars")

    # Conditional metrics
    if format_metrics["high_risk_count"] > 0:
        rate = format_metrics["high_risk_recommends_pro_rate"]
        print(
            f"  HIGH risk → pro rate: {rate:.1%} ({format_metrics['high_risk_count']} HIGH risk answers)"
        )
    else:
        print("  HIGH risk → pro rate: N/A (no HIGH risk answers)")

    if format_metrics["dangerous_category_count"] > 0:
        rate = format_metrics["dangerous_mentions_safety_rate"]
        print(
            f"  Safety mention rate:  {rate:.1%} ({format_metrics['dangerous_category_count']} dangerous category Qs)"
        )
    else:
        print("  Safety mention rate:  N/A (no dangerous category questions)")

    if ragas_metrics:
        print("\nRagas Metrics:")
        print(f"  Faithfulness:         {ragas_metrics['faithfulness']:.3f}")
        print(f"  Answer Relevancy:     {ragas_metrics['answer_relevancy']:.3f}")
        print(f"  Context Precision:    {ragas_metrics['context_precision']:.3f}")
        print(
            f"  (Based on {ragas_metrics['questions_with_ground_truth']} questions with ground truth)"
        )
    else:
        print("\nRagas Metrics: Not available (no ground truth in golden set)")

    print("=" * 60 + "\n")


def check_thresholds(format_metrics: dict, ragas_metrics: dict | None) -> list[str]:
    """Check metrics against fixed thresholds.

    Returns a list of failure messages. Empty list means all thresholds passed.
    """
    failures: list[str] = []

    # Format metric thresholds
    for key in ("has_citations_rate", "risk_level_valid_rate"):
        value = format_metrics.get(key)
        if value is not None and key in THRESHOLDS and value < THRESHOLDS[key]:
            failures.append(f"  FAIL {key}: {value:.3f} < {THRESHOLDS[key]:.3f}")

    # Conditional format metric: high_risk_recommends_pro_rate
    # Only check if there were HIGH risk answers to evaluate
    if format_metrics.get("high_risk_count", 0) > 0:
        value = format_metrics.get("high_risk_recommends_pro_rate")
        threshold = THRESHOLDS.get("high_risk_recommends_pro_rate")
        if value is not None and threshold is not None and value < threshold:
            failures.append(f"  FAIL high_risk_recommends_pro_rate: {value:.3f} < {threshold:.3f}")

    # Ragas metric thresholds (only when Ragas ran)
    if ragas_metrics:
        for key in ("faithfulness", "context_precision", "answer_relevancy"):
            value = ragas_metrics.get(key)
            if value is not None and key in THRESHOLDS and value < THRESHOLDS[key]:
                failures.append(f"  FAIL {key}: {value:.3f} < {THRESHOLDS[key]:.3f}")

    return failures


def main() -> int:
    """Run the evaluation."""
    import os

    os.environ["OBSERVABILITY__ENABLED"] = "false"

    from app.core.ssl_setup import configure_ssl

    configure_ssl()

    parser = argparse.ArgumentParser(description="Run evaluation on golden questions")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (for testing)",
    )
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Skip Ragas metrics (faster, no LLM calls for eval)",
    )
    parser.add_argument(
        "--threshold-check",
        action="store_true",
        help="Exit with code 1 if any metric falls below its threshold",
    )
    args = parser.parse_args()

    # Clear caches to ensure fresh state
    # This is important when config changes (e.g., reranking enabled/disabled)
    from app.rag.retriever import get_index, get_reranker

    get_index.cache_clear()
    get_reranker.cache_clear()

    # Paths
    eval_dir = Path(__file__).parent
    golden_path = eval_dir / "golden_questions.jsonl"
    reports_dir = eval_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Load questions
    print(f"Loading questions from {golden_path}")
    questions = load_golden_questions(golden_path)

    if args.limit:
        # Prioritize questions with ground truth for Ragas metrics
        with_gt = [q for q in questions if q.get("ground_truth")]
        without_gt = [q for q in questions if not q.get("ground_truth")]

        # Take as many with ground truth as possible, then fill with others
        if len(with_gt) >= args.limit:
            questions = with_gt[: args.limit]
        else:
            questions = with_gt + without_gt[: args.limit - len(with_gt)]

        gt_count = sum(1 for q in questions if q.get("ground_truth"))
        print(f"Limited to {args.limit} questions ({gt_count} with ground truth)")

    print(f"Running evaluation on {len(questions)} questions...")

    # Run evaluation
    results: list[EvalResult] = []
    truncate_len = 150  # Length for truncating question/answer preview
    for i, q in enumerate(questions, 1):
        question_preview = q["question"][:truncate_len]
        if len(q["question"]) > truncate_len:
            question_preview += "..."
        print(f"  [{i}/{len(questions)}] {q['category']}: {question_preview}")

        result = run_single_question(q)
        results.append(result)

        if result.error:
            print(f"    ERROR: {result.error}")
        else:
            answer_preview = result.answer[:truncate_len].replace("\n", " ")
            if len(result.answer) > truncate_len:
                answer_preview += "..."
            print(f"    Risk: {result.risk_level} | {answer_preview}")

    # Compute metrics
    format_metrics = compute_format_metrics(results)

    ragas_metrics = None
    if not args.skip_ragas:
        ragas_metrics = compute_ragas_metrics(results)

    # Save report
    report_path = save_report(results, format_metrics, ragas_metrics, reports_dir)
    print(f"\nReport saved to: {report_path}")

    # Print summary
    print_summary(format_metrics, ragas_metrics)

    # Threshold check
    if args.threshold_check:
        failures = check_thresholds(format_metrics, ragas_metrics)
        if failures:
            print("THRESHOLD CHECK FAILED:")
            for f in failures:
                print(f)
            return 1
        print("THRESHOLD CHECK PASSED: All metrics within acceptable range.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
