# TestBench-Forge Submission Handoff

## What Is Validated

TestBench-Forge is a Python test-generation RL environment. A model sees a reference implementation and writes `test_*` functions. The reward is MS* hidden-mutant kill rate with light suite-size control, gated by reference execution and behavior-equivalent refactors.

Local validation, no API keys:

```bash
python3 stage_a_checks.py
python3 selftest.py
python3 eval_bench.py --out eval_results.json
python3 demo.py
```

Verified outputs from this run:

- Stage A checks: 6/6 passing.
- Lazy proxy mean: 0.451.
- Thorough proxy mean: 1.000.
- Base-band check: true, the lazy proxy mean is inside the 20 to 50 percent target band. Its bootstrap CI crosses the upper bound, so present this as a useful local calibration, not a statistically final base-model result.
- Fake stdout pass ledger, `SystemExit`, and frame/import escapes score 0.
- Known-good suite false-positive rate: 0.
- Modal GRPO reward artifact: first-10 mean 0.233 to last-10 mean 0.750 over 80 steps on Qwen2.5-3B with TRL GRPO and LoRA.

## Demo Steps

```bash
cd /Users/charlie/events/YC---RL-Gym
python3 demo.py
open demo.html
```

Click **Reveal a thorough suite**. The dashboard is labeled honestly:

- Without `results.json`, it shows offline lazy-vs-thorough environment endpoints.
- It separately reports the real Modal GRPO reward curve.
- It does not claim held-out trained-model eval lift unless a real `results.json` exists.

## What To Say

> TestBench-Forge trains models to write tests that catch hidden bugs. The reward is executable, not judged by an LLM: hidden-mutant MS* kill rate with light suite-size control, guarded by behavior-equivalent refactors so brittle over-specified tests score zero. Locally, the lazy-suite proxy mean is 0.451 and the thorough-suite proxy is 1.000. We also have a real Modal GRPO reward curve from 0.233 to 0.750 over 80 steps.

## Blocked Items

- HUD deploy and HUD eval need `HUD_API_KEY`.
- Fireworks RFT and best-of-N baseline need `FIREWORKS_API_KEY`.
- A fresh Modal rerun needs Modal auth/credits, but the real artifact is already checked in.
- Live base-vs-best-of-N-vs-trained held-out eval is not available yet. Do not claim it.

## Files To Review

- `testbench.py`: runner hardening, mutation engine, refactor gate, MS* scorer with suite-size control.
- `stage_a_checks.py`: no-key Stage A regression checks.
- `eval_bench.py`: offline report and Modal curve summary.
- `demo.py` and `demo.html`: honest dashboard.
- `README.md`, `CHEATSHEET.md`, `docs/plans/PROGRESS.md`: updated claims and instructions.
