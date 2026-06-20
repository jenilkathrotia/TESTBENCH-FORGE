"""Generate the RFT dataset (JSONL) for TestBench-Forge.

Each row pairs the module's prompt with its ground-truth metadata so the reward function
can recover which module to score:

    {"messages": [{"role": "user", "content": <prompt>}],
     "ground_truth_for_eval": {"module_id": <id>}}

GRPO samples N rollouts per prompt internally, so one row per module is enough to start —
add more modules in testbench.py for real training volume.

Run: .venv/bin/python build_dataset.py   ->  writes dataset.jsonl
"""
import json

import testbench


def build(path: str = "dataset.jsonl") -> int:
    rows = []
    for module_id in testbench.MODULES:
        rows.append({
            "messages": [{"role": "user", "content": testbench.build_testbench_prompt(module_id)}],
            "ground_truth_for_eval": {"module_id": module_id},
        })
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return len(rows)


if __name__ == "__main__":
    n = build()
    print(f"wrote {n} rows to dataset.jsonl "
          f"(one per module: {list(testbench.MODULES)}). "
          f"Add more modules in testbench.py for training volume.")
