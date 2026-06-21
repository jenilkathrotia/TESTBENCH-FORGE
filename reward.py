"""Fireworks Eval Protocol reward adapter for TestBench-Forge.

Wraps `testbench.score_suite` as a reward-kit reward function so the SAME scorer that
evaluates also trains the model via RFT/GRPO, so the before/after lift is
measured against the identical signal.

Eval Protocol and reward-kit signatures, verified against current local SDKs:
    @reward_function
    def fn(messages, ground_truth=None, **kwargs) -> EvaluateResult(score, reason, metrics)
  - model output  = messages[-1]["content"]   (the generated test suite)
  - per-sample id = ground_truth["module_id"] (from the dataset row's ground_truth)

This file imports cleanly even if neither SDK is installed (offline shims), so the core
scoring glue can be unit-tested without the SDK. Install for real training:
    pip install eval-protocol fireworks-ai
Validate: eval-protocol local-test --entry testbench_eval_protocol.py::test_testbench_forge_fixture --ignore-docker -y
"""
from __future__ import annotations

import families
import testbench

try:
    from eval_protocol import reward_function  # type: ignore[attr-defined]
    from eval_protocol.models import EvaluateResult, MetricResult
    _HAS_REWARD_SDK = True
except Exception:  # offline / not installed -> minimal shims so this module still imports
    try:
        from reward_kit import reward_function  # type: ignore[no-redef]
        from reward_kit.models import EvaluateResult, MetricResult  # type: ignore[no-redef]
        _HAS_REWARD_SDK = True
    except Exception:
        _HAS_REWARD_SDK = False
        from dataclasses import dataclass, field

        def reward_function(fn):  # type: ignore[no-redef]
            return fn

        @dataclass
        class MetricResult:  # type: ignore[no-redef]
            score: float = 0.0
            reason: str = ""
            is_score_valid: bool = True

        @dataclass
        class EvaluateResult:  # type: ignore[no-redef]
            score: float = 0.0
            reason: str = ""
            metrics: dict = field(default_factory=dict)


def _content(msg) -> str:
    if isinstance(msg, dict):
        return msg.get("content") or ""
    return getattr(msg, "content", "") or ""


def compute_score(messages, ground_truth):
    """Pure scoring core without SDK types. Returns (score, reason)."""
    suite = families.extract_code(_content(messages[-1]) if messages else "")
    module_id = (ground_truth or {}).get("module_id")
    if module_id not in testbench.MODULES:
        return 0.0, f"unknown module_id: {module_id!r}"
    rate, info = testbench.score_suite(module_id, suite)
    if not info.get("gate"):
        return 0.0, f"gate failed: {info.get('reason', 'suite did not pass reference')}"
    denom = info.get("denominator", "raw")
    if denom == "ms_star":
        penalty = info.get("size_penalty", 0.0)
        penalty_text = f"; size penalty {penalty:.3f}" if penalty else ""
        return rate, (
            f"MS* killed {info.get('ms_star_killed', 0)}/{info.get('ms_star_total', 0)} "
            f"behavioral mutant clusters; raw killed {info.get('killed', 0)}/"
            f"{info.get('mutants', 0)}{penalty_text}"
        )
    return rate, f"killed {info['killed']}/{info['mutants']} hidden mutants"


def _metric_result(score: float, reason: str):
    try:
        return MetricResult(score=score, is_score_valid=True, reason=reason)
    except TypeError:
        return MetricResult(score=score, success=score > 0.0, reason=reason)


def _evaluate(messages, ground_truth=None, **kwargs) -> EvaluateResult:
    score, reason = compute_score(messages, ground_truth)
    return EvaluateResult(
        score=score,
        reason=reason,
        metrics={"mutant_kill_rate": _metric_result(score, reason)},
    )


# The deployable reward function. With an SDK installed it gains validation metadata.
evaluate = reward_function(_evaluate) if _HAS_REWARD_SDK else _evaluate
