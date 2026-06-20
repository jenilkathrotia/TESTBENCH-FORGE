"""Baseline / best-of-N runner for TestBench-Forge using the Fireworks inference SDK.

Produces the "before" number (base model's mutant-kill rate per module) and doubles as the
demo fallback: best-of-N suites selected by kill-rate. Uses the exact SDK shape:

    from fireworks import Fireworks
    client = Fireworks()
    client.chat.completions.create(model=..., messages=[...])

Setup:
    pip install fireworks-ai
    export FIREWORKS_API_KEY=fw-...
    # optional overrides:
    export FW_MODEL=accounts/fireworks/models/deepseek-v3p1   # base model to baseline
    export BEST_OF_N=1                                         # raise for best-of-N

Run: .venv/bin/python fireworks_baseline.py
"""
import os

import families
import testbench

MODEL = os.environ.get("FW_MODEL", "accounts/fireworks/models/deepseek-v3p1")
BEST_OF_N = int(os.environ.get("BEST_OF_N", "1"))
TEMPERATURE = float(os.environ.get("FW_TEMP", "0.7"))


def run_module(client, module_id, n=1):
    prompt = testbench.build_testbench_prompt(module_id)
    best_rate, best_info = -1.0, {}
    for _ in range(n):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
        suite = families.extract_code(resp.choices[0].message.content)
        rate, info = testbench.score_suite(module_id, suite)
        if rate > best_rate:
            best_rate, best_info = rate, info
    return best_rate, best_info


def main():
    from fireworks import Fireworks  # imported here so the file loads without the SDK

    client = Fireworks()  # reads FIREWORKS_API_KEY
    print(f"model={MODEL}  best-of-{BEST_OF_N}\n")
    rates = []
    for module_id in testbench.MODULES:
        rate, info = run_module(client, module_id, n=BEST_OF_N)
        rates.append(rate)
        gate = "ok" if info.get("gate") else "GATE-FAIL"
        print(f"  {module_id:20s} kill_rate={rate:.3f}  "
              f"({info.get('killed', 0)}/{info.get('mutants', 0)} mutants, gate {gate})")
    print(f"\n  mean baseline kill_rate = {sum(rates) / len(rates):.3f}  "
          f"(this is the 'before' number RFT improves on)")


if __name__ == "__main__":
    main()
