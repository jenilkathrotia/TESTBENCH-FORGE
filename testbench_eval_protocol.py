"""Eval Protocol wrapper for TestBench-Forge RFT.

This file gives Fireworks Eval Protocol a normal `@evaluation_test` entrypoint
whose scorer is the same hidden-mutant reward used locally by `reward.py`.
"""
import json
import os
from typing import Any

import families
import reward
import testbench
from eval_protocol.models import EvaluateResult, EvaluationRow, InputMetadata, Message, MetricResult
from eval_protocol.pytest.default_no_op_rollout_processor import NoOpRolloutProcessor
from eval_protocol.pytest import SingleTurnRolloutProcessor, evaluation_test


DEFAULT_MODEL = os.environ.get("EP_MODEL", "fireworks_ai/glm-latest")
DEFAULT_MAX_TOKENS = int(os.environ.get("EP_MAX_OUTPUT_TOKENS", "4096"))
DEFAULT_TEMPERATURE = float(os.environ.get("EP_TEMPERATURE", "0.7"))


def dataset_to_rows(data: list[dict[str, Any]]) -> list[EvaluationRow]:
    rows: list[EvaluationRow] = []
    for idx, item in enumerate(data):
        ground_truth = item.get("ground_truth") or item.get("ground_truth_for_eval") or {}
        messages = [
            Message(role=message["role"], content=message.get("content", ""))
            for message in item.get("messages", [])
        ]
        module_id = ground_truth.get("module_id", f"row-{idx}")
        rows.append(
            EvaluationRow(
                messages=messages,
                ground_truth=ground_truth,
                input_metadata=InputMetadata(row_id=str(module_id)),
            )
        )
    return rows


def _score_row(row: EvaluationRow) -> EvaluationRow:
    score, reason = reward.compute_score(row.messages, row.ground_truth)
    row.evaluation_result = EvaluateResult(
        score=score,
        reason=reason,
        metrics={
            "mutant_kill_rate": MetricResult(
                score=score,
                reason=reason,
                is_score_valid=True,
            )
        },
    )
    return row


def _fixture_rows() -> list[EvaluationRow]:
    suite = (
        "```python\n"
        "def test_ok():\n    assert is_balanced('([{}])') == True\n"
        "def test_empty():\n    assert is_balanced('') == True\n"
        "def test_wrong_type():\n    assert is_balanced('(]') == False\n"
        "def test_interleaved():\n    assert is_balanced('([)]') == False\n"
        "def test_unclosed():\n    assert is_balanced('(((') == False\n"
        "def test_extra_close():\n    assert is_balanced('())') == False\n"
        "def test_pair():\n    assert is_balanced('()') == True\n"
        "```"
    )
    return [
        EvaluationRow(
            messages=[
                Message(role="user", content=testbench.build_testbench_prompt("is_balanced")),
                Message(role="assistant", content=suite),
            ],
            ground_truth={"module_id": "is_balanced"},
            input_metadata=InputMetadata(row_id="is_balanced-fixture"),
        )
    ]


@evaluation_test(
    input_rows=[_fixture_rows()],
    passed_threshold=0.9,
    rollout_processor=NoOpRolloutProcessor(),
    mode="pointwise",
)
def test_testbench_forge_fixture(row: EvaluationRow) -> EvaluationRow:
    """Local no-token fixture for validating evaluator packaging."""
    return _score_row(row)


@evaluation_test(
    input_dataset=["dataset.jsonl"],
    dataset_adapter=dataset_to_rows,
    completion_params=[
        {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
    ],
    passed_threshold=0.2,
    rollout_processor=SingleTurnRolloutProcessor(),
    num_runs=1,
    mode="pointwise",
)
def test_testbench_forge_rft(row: EvaluationRow) -> EvaluationRow:
    """Fireworks RFT evaluator entrypoint."""
    return _score_row(row)


def score_jsonl(path: str = "dataset.jsonl") -> list[dict[str, Any]]:
    """Developer helper for checking dataset row conversion without invoking a model."""
    out = []
    with open(path) as f:
        for line in f:
            rows = dataset_to_rows([json.loads(line)])
            row = rows[0]
            out.append({"row_id": row.input_metadata.row_id, "module_id": row.ground_truth.get("module_id")})
    return out


def extract_candidate_suite(text: str) -> str:
    return families.extract_code(text)
