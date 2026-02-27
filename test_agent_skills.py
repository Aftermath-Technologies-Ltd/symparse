from __future__ import annotations
import statistics
import pytest

def evaluate_agent(scores: list[float]) -> tuple[float, float]:
    """
    Evaluates an agent over multiple seeds.
    Returns mean and standard deviation.
    """
    if len(scores) < 5:
        raise ValueError("Single-run results are unreliable; always show variance and confidence intervals. Run at least 5-10 seeds.")
    mean = statistics.mean(scores)
    std = statistics.stdev(scores)
    return mean, std

def test_evaluate_agent() -> None:
    # Test with enough seeds
    scores = [1.0, 0.9, 0.95, 1.0, 0.85]
    mean, std = evaluate_agent(scores)
    assert mean == 0.94
    assert round(std, 4) == 0.0652

def test_evaluate_agent_insufficient_seeds() -> None:
    with pytest.raises(ValueError, match="Single-run results are unreliable"):
        evaluate_agent([1.0, 0.9])
