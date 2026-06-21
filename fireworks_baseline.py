"""Baseline / best-of-N runner for TestBench-Forge using the Fireworks inference SDK.

Produces a raw baseline sample for the base model and doubles as the demo fallback:
best-of-N suites selected by score. Gate-failed suites are included as 0.0 scores.
Uses the exact SDK shape:

    from fireworks import Fireworks
    client = Fireworks()
    client.chat.completions.create(model=..., messages=[...])

Setup:
    pip install fireworks-ai
    export FIREWORKS_API_KEY=fw-...
    # optional overrides:
    export FW_MODEL=accounts/fireworks/models/gpt-oss-120b     # base model to baseline
    export BEST_OF_N=1                                         # raise for best-of-N

Run: .venv/bin/python fireworks_baseline.py
"""
import json
import os
import traceback
from datetime import datetime, timezone

import families
import testbench

MODEL = os.environ.get("FW_MODEL", "accounts/fireworks/models/gpt-oss-120b")
BEST_OF_N = int(os.environ.get("BEST_OF_N", "1"))
TEMPERATURE = float(os.environ.get("FW_TEMP", "0.7"))
OUT_PATH = os.environ.get("FW_RESULTS", "fireworks_results.json")
TIMEOUT_SECONDS = float(os.environ.get("FW_TIMEOUT", "90"))


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


def _write_result(payload):
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    from fireworks import Fireworks

    api_key = os.environ.get("FIREWORKS_API_KEY")
    if not api_key:
        _write_result({
            "status": "blocked",
            "blocked_on": "missing_fireworks_api_key",
            "model": MODEL,
            "best_of_n": BEST_OF_N,
            "temperature": TEMPERATURE,
            "timeout_seconds": TIMEOUT_SECONDS,
            "error": "FIREWORKS_API_KEY is not set in this process",
        })
        print("blocked: FIREWORKS_API_KEY is not set in this process")
        print(f"wrote {OUT_PATH}")
        return

    client = Fireworks(api_key=api_key, timeout=TIMEOUT_SECONDS)
    print(f"model={MODEL}  best-of-{BEST_OF_N}\n")
    rates = []
    rows = []
    for module_id in testbench.MODULES:
        try:
            rate, info = run_module(client, module_id, n=BEST_OF_N)
        except Exception as exc:
            message = str(exc)
            _write_result({
                "status": "blocked",
                "blocked_on": "fireworks_model_access",
                "model": MODEL,
                "best_of_n": BEST_OF_N,
                "temperature": TEMPERATURE,
                "timeout_seconds": TIMEOUT_SECONDS,
                "error": message,
                "traceback": traceback.format_exc(limit=4),
                "completed_modules": rows,
            })
            print(f"blocked on Fireworks model access for {MODEL}: {message}")
            print(f"wrote {OUT_PATH}")
            return
        rates.append(rate)
        gate = "ok" if info.get("gate") else "GATE-FAIL"
        rows.append({
            "module_id": module_id,
            "kill_rate": rate,
            "killed": info.get("killed", 0),
            "mutants": info.get("mutants", 0),
            "gate": bool(info.get("gate")),
        })
        print(f"  {module_id:20s} score={rate:.3f}  "
              f"({info.get('killed', 0)}/{info.get('mutants', 0)} mutants, gate {gate})")
    mean_rate = sum(rates) / len(rates)
    _write_result({
        "status": "ok",
        "model": MODEL,
        "best_of_n": BEST_OF_N,
        "temperature": TEMPERATURE,
        "timeout_seconds": TIMEOUT_SECONDS,
        "mean_score_including_gate_failures": mean_rate,
        "modules": rows,
    })
    print(f"\n  mean baseline score incl. gate failures = {mean_rate:.3f}")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
