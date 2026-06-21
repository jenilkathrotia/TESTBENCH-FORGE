"""Standardized result schema for TestBench-Forge evaluations.

One shape for every provider (Fireworks base, Fireworks RFT, local Gemma, ...) so that
`fireworks_baseline.py` and `rft_eval_report.py` speak the same language and runs compare
apples-to-apples. The scorer stays in `testbench.py`; this module only shapes its output.

A benchmark result:
    {
      "schema_version": "1",
      "provider": "fireworks",                # fireworks | fireworks-rft | local-gemma | ...
      "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
      "status": "ok",                          # ok | blocked | error
      "best_of_n": 1,                          # candidates sampled per prompt, best kept
      "runs": 3,                               # repeated full passes (for variance / CI)
      "temperature": 0.7,
      "mean_score": 0.42,                      # mean over scored modules (errors excluded)
      "n_modules": 10,
      "n_gate_failures": 4,                    # modules that failed the over-spec gate (score 0)
      "created_at": "2026-06-21T...Z",
      "modules": [ <module_result>, ... ],
      "error": null,
    }

A module result:
    {
      "module": "binary_search",
      "score": 0.83,                           # representative kill rate in [0, 1]
      "killed": 15, "mutants": 18,
      "gate": true,                            # passed reference + behaviour-equivalent refactors
      "best_of_n": 1,
      "runs": 3,
      "scores": [0.78, 0.83, 0.83],            # per-run scores (empty if not captured)
      "error": null,
    }
"""
from __future__ import annotations

import json
import statistics

SCHEMA_VERSION = "1"


def module_result(module_id, score, killed, mutants, gate, *,
                  best_of_n=1, runs=1, scores=None, error=None):
    """Build one standardized per-module record."""
    return {
        "module": module_id,
        "score": round(float(score), 6),
        "killed": int(killed),
        "mutants": int(mutants),
        "gate": bool(gate),
        "best_of_n": int(best_of_n),
        "runs": int(runs),
        "scores": [round(float(s), 6) for s in (scores or [])],
        "error": error,
    }


def benchmark_result(provider, model, modules, *, status="ok", best_of_n=1, runs=1,
                     temperature=None, created_at=None, error=None, **extra):
    """Build a top-level benchmark result; mean/gate-failure counts derive from `modules`."""
    scored = [m for m in modules if m.get("error") is None]
    mean = sum(m["score"] for m in scored) / len(scored) if scored else 0.0
    payload = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "model": model,
        "status": status,
        "best_of_n": int(best_of_n),
        "runs": int(runs),
        "temperature": temperature,
        "mean_score": round(mean, 6),
        "n_modules": len(modules),
        "n_gate_failures": sum(1 for m in scored if not m["gate"]),
        "modules": modules,
        "error": error,
    }
    if created_at is not None:
        payload["created_at"] = created_at
    payload.update(extra)  # provider-specific extras (blocked_on, timeout_seconds, traceback, ...)
    return payload


def run_stats(scores):
    """mean/min/max/stdev for a list of per-run scores (stdev is 0.0 for fewer than 2 runs)."""
    vals = [float(s) for s in scores]
    if not vals:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "stdev": 0.0, "n": 0}
    return {
        "mean": round(statistics.fmean(vals), 6),
        "min": round(min(vals), 6),
        "max": round(max(vals), 6),
        "stdev": round(statistics.stdev(vals), 6) if len(vals) > 1 else 0.0,
        "n": len(vals),
    }


def load(path):
    """Load a benchmark result JSON file."""
    with open(path) as f:
        return json.load(f)


def write(path, payload):
    """Write a benchmark result deterministically (sorted keys, trailing newline)."""
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
