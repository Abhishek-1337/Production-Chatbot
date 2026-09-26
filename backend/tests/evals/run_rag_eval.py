import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(_BACKEND_DIR / ".env")

JUDGE_MODEL = os.getenv("DEEPEVAL_JUDGE_MODEL", "gpt-4o-mini")
THRESHOLD = float(os.getenv("DEEPEVAL_THRESHOLD", "0.5"))


@dataclass
class EvalOutcome:
    name: str
    answer: str
    scores: dict
    passed: bool
    notes: list = field(default_factory=list) #it is to create separate instance of empty list for different objects.


def generate_answer(query: str, retrieval_context: list) -> str:
    """Answer exactly the way production does (minus DB/history)."""
    from api.v1.controllers.document import agent

    context = "\n\n".join(retrieval_context)
    prompt = f"Document context:\n{context}\n\nQuestion: {query.strip()}"
    result = agent.run_sync(prompt)
    return (result.output or "").strip()


def build_metrics():
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualRecallMetric,
        FaithfulnessMetric,
    )

    return {
        "faithfulness": FaithfulnessMetric(threshold=THRESHOLD, model=JUDGE_MODEL),
        "answer_relevancy": AnswerRelevancyMetric(threshold=THRESHOLD, model=JUDGE_MODEL),
        "contextual_recall": ContextualRecallMetric(threshold=THRESHOLD, model=JUDGE_MODEL),
    }


def _measure_with_retry(metric, test_case, attempts: int = 3):
    """Judge calls flake (transient timeouts); retry those, not real failures.

    A low score is returned normally and never retried -- only an exception
    (e.g. TimeoutError from the judge request) triggers another attempt.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            metric.measure(test_case)
            return
        except Exception as exc:  # noqa: BLE001 -- retried below, raised at the end
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def evaluate_case(case: dict, metrics: dict | None = None) -> EvalOutcome:
    from deepeval.test_case import LLMTestCase

    all_metrics = metrics or build_metrics()
    wanted = case.get("metrics", list(all_metrics))
    answer = generate_answer(case["query"], case["retrieval_context"])
    test_case = LLMTestCase(
        input=case["query"],
        actual_output=answer,
        expected_output=case["expected_output"],
        retrieval_context=case["retrieval_context"],
    )
    scores: dict = {}
    for metric_name in wanted:
        metric = all_metrics[metric_name]
        _measure_with_retry(metric, test_case)
        scores[metric_name] = round(metric.score, 3) if metric.score is not None else None
    notes: list = []
    for phrase in case.get("must_contain", []):
        if phrase.lower() not in answer.lower():
            notes.append(f"answer missing required phrase: {phrase!r}")
    passed = all(
        (score is not None and score >= THRESHOLD) for score in scores.values()
    ) and not notes
    return EvalOutcome(name=case["name"], answer=answer, scores=scores, passed=passed, notes=notes)


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set -- cannot run evals (see backend/.env.example).")
        return 2
    from tests.evals.golden_dataset import GOLDEN_CASES

    metrics = build_metrics()
    outcomes = [evaluate_case(case, metrics) for case in GOLDEN_CASES]

    print(f"\nRAG evals (judge={JUDGE_MODEL}, threshold={THRESHOLD})")
    print("-" * 90)
    failures = 0
    for outcome in outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        failures += outcome.passed is False
        score_str = "  ".join(f"{k}={v}" for k, v in outcome.scores.items())
        print(f"[{status}] {outcome.name}: {score_str}")
        print(f"        answer: {outcome.answer[:200]}")
        for note in outcome.notes:
            print(f"        note: {note}")
    print("-" * 90)
    print(f"{len(outcomes) - failures}/{len(outcomes)} cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
