"""
Pytest gate for the RAG evals.

Each golden case generates a live answer through the production agent and
asserts it clears every metric at threshold. Skips cleanly when no
OPENAI_API_KEY is available (e.g. offline CI) instead of failing.
"""

import os
import sys
from pathlib import Path

# Make `tests.*` importable no matter how pytest is invoked
# (bare `pytest`, `python -m pytest`, or from the repo root).
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest

from tests.evals.golden_dataset import GOLDEN_CASES
from tests.evals.run_rag_eval import THRESHOLD, build_metrics, evaluate_case

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set -- LLM-judged evals need it",
)


@pytest.fixture(scope="module")
def metrics():
    return build_metrics()


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["name"] for c in GOLDEN_CASES])
def test_rag_case_meets_threshold(case, metrics):
    outcome = evaluate_case(case, metrics)
    failures = {
        name: score
        for name, score in outcome.scores.items()
        if score is None or score < THRESHOLD
    }
    assert not failures and not outcome.notes, (
        f"case={outcome.name} below threshold={THRESHOLD}: {failures} {outcome.notes}\n"
        f"answer was: {outcome.answer[:500]}"
    )
