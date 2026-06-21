"""Offline evaluation report for TestBench-Forge.

This script never calls model APIs. It reports what can be verified locally:

1. Environment scores for the built-in lazy and thorough suites.
2. A 20 to 50 percent band check on the available base proxy.
3. The real Modal GRPO training curve artifact, if present.

Live base-vs-best-of-N-vs-trained model evals remain credential-gated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

import selftest
import testbench


def _ci95(values: list[float]) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    # Deterministic bootstrap to avoid adding a dependency.
    import random

    rng = random.Random(0)
    draws = []
    for _ in range(2000):
        sample = [values[rng.randrange(len(values))] for _ in values]
        draws.append(mean(sample))
    draws.sort()
    return (round(draws[int(0.025 * len(draws))], 4), round(draws[int(0.975 * len(draws))], 4))


def _load_modal_curve(path: Path) -> dict | None:
    if not path.exists():
        return None
    values = [float(line.strip()) for line in path.read_text().splitlines() if line.strip()]
    if not values:
        return None
    first = values[:10]
    last = values[-10:]
    return {
        "source": str(path),
        "steps": len(values),
        "first10_mean": round(mean(first), 4),
        "last10_mean": round(mean(last), 4),
        "delta": round(mean(last) - mean(first), 4),
        "best": round(max(values), 4),
    }


def build_report() -> dict:
    modules = {}
    lazy_scores = []
    thorough_scores = []
    for module_id in testbench.MODULES:
        lazy, lazy_info = testbench.score_suite(module_id, selftest.WEAK[module_id])
        thorough, thorough_info = testbench.score_suite(module_id, selftest.THOROUGH[module_id])
        lazy_scores.append(lazy)
        thorough_scores.append(thorough)
        modules[module_id] = {
            "lazy_proxy": round(lazy, 4),
            "thorough_proxy": round(thorough, 4),
            "delta": round(thorough - lazy, 4),
            "mutants": lazy_info.get("mutants", 0),
            "ms_star_total": lazy_info.get("ms_star_total", 0),
            "saturated": lazy >= 0.8,
        }

    modal_curve = _load_modal_curve(Path("grpo_rewards.txt"))
    base_mean = mean(lazy_scores)
    return {
        "status": "offline_report",
        "honesty_note": (
            "lazy_proxy and thorough_proxy are hand-written suite endpoints, not live base "
            "or trained model evals. modal_grpo_curve is a real training reward artifact "
            "when present, not held-out eval."
        ),
        "lazy_proxy_mean": round(base_mean, 4),
        "lazy_proxy_ci95": _ci95(lazy_scores),
        "thorough_proxy_mean": round(mean(thorough_scores), 4),
        "thorough_proxy_ci95": _ci95(thorough_scores),
        "base_band_20_50": 0.2 <= base_mean <= 0.5,
        "modules": modules,
        "modal_grpo_curve": modal_curve,
        "credential_gated_next": {
            "base_vs_best_of_n": "Requires model API key to sample candidate suites.",
            "trained_eval": "Requires a trained endpoint or saved model completions.",
            "hud_training": "Requires HUD_API_KEY.",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="eval_results.json")
    args = parser.parse_args()

    report = build_report()
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    curve = report.get("modal_grpo_curve") or {}
    curve_text = (
        f"modal curve {curve.get('first10_mean')} -> {curve.get('last10_mean')}"
        if curve
        else "modal curve missing"
    )
    print(
        f"wrote {args.out} | lazy proxy mean={report['lazy_proxy_mean']:.3f} "
        f"band_20_50={report['base_band_20_50']} | {curve_text}"
    )


if __name__ == "__main__":
    main()
