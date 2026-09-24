"""Unit tests for token cost math. Run directly (no pytest in venv)."""
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")

from services.token_usage_service import cost_usd_for, total_cost_usd


def test_gpt4o_mini_rates():
    # $0.15 / 1M input + $0.60 / 1M output
    assert cost_usd_for("gpt-4o-mini", 1_000_000, 1_000_000) == 0.75
    assert cost_usd_for("GPT-4O-MINI", 1_000_000, 0) == 0.15
    assert cost_usd_for("gpt-4o-mini", 0, 1_000_000) == 0.60


def test_free_models():
    assert cost_usd_for("all-MiniLM-L6-v2", 999_999, 999_999) == 0.0
    assert cost_usd_for("cache", 0, 0) == 0.0


def test_unknown_models_cost_zero():
    assert cost_usd_for("mystery-model", 10**9, 10**9) == 0.0
    assert cost_usd_for(None, 100, 100) == 0.0
    assert cost_usd_for("", 100, 100) == 0.0


def test_total_cost_usd_sums_rows():
    rows = [
        SimpleNamespace(model="gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0),
        SimpleNamespace(model="cache", prompt_tokens=0, completion_tokens=0),
        SimpleNamespace(model="mystery", prompt_tokens=10**9, completion_tokens=0),
    ]
    assert total_cost_usd(rows) == 0.15


if __name__ == "__main__":
    test_gpt4o_mini_rates()
    test_free_models()
    test_unknown_models_cost_zero()
    test_total_cost_usd_sums_rows()
    print("token cost tests: PASS")
