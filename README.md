# TestBench-Forge

**An RL gym that trains agents to write the test suite that catches the most bugs**: rewarded by MS* hidden-mutant kill rate over held-out buggy variants, with light suite-size control.

> The thesis: recursive self-improvement is bottlenecked on *trustworthy verification*. The scarcest verifier of all is a **test suite that isn't fooled by a bug that passes the easy cases.** TestBench-Forge trains models to write exactly that, and proves it by mutation testing: run the suite over a hidden pool of buggy variants and count the kills.

Track fit: **Agentic Collaboration** (the pytest variant you present) with a **Chip Design** moat (the same gym ports to Verilog testbenches as a roadmap).

## Status (what's proven, honestly)
- ✅ **Verifiable, hard-to-game environment**: 10 modules, hidden mutants, automatic MS* kill-rate reward with suite-size control, no LLM judge.
- ✅ **Reproducible discrimination (no API key):** a lazy suite scores **0.451**, a thorough suite **1.000**, `assert False` scores **0** (`python selftest.py`). The lazy mean is a local calibration proxy, not a final base-model statistic.
- ✅ **Real GRPO training artifact:** Modal A100 GRPO on Qwen2.5-3B improved training reward first-10 mean **0.233** to last-10 mean **0.750** over 80 steps (`grpo_result.json`, `grpo_rewards.txt`).
- ✅ **Honest eval boundary:** the dashboard fallback is lazy-vs-thorough, not a trained-model eval. Live base-vs-best-of-N-vs-trained model eval still requires API credentials.

## The loop

1. Agent sees a module + its **reference implementation**.
2. It writes a **pytest-style test suite** (functions named `test_*`).
3. The harness runs the suite against a **hidden pool of mutants** (buggy variants).
4. **Reward = MS* behavioral mutant clusters killed / clusters total, minus a light suite-size penalty**, gated by the suite passing the reference plus behavior-equivalent refactors.

## Why it's a strong RL environment (not an eval)

- **Multi-signal, verifiable reward** with a clean execution oracle: no LLM judge anywhere.
- **Hard to game** (validated): `assert False`, no-test suites, fake stdout pass ledgers, `sys.exit`, and frame/import escapes score **0**.
- **Richer hidden pool**: AST mutation operators, curated hard mutants, bytecode-equivalence filtering, and differentially certified behavior-equivalent refactors. The current pool is deterministic for comparable before/after scoring, with hard-first ordering calibrated against one lazy reference suite per module.

## Files

| file | what | touched? |
|---|---|---|
| `testbench.py` | **10 modules** + reference impls, **AST mutation engine**, differential filter, suite-runner dispatch, kill-rate scorer, prompt | the new core |
| `env.py` | HUD `forge_testbench` template + `run_tests` MCP tool (gate-only dry-run) | + template |
| `reward.py` | **Fireworks reward-kit adapter**: wraps `score_suite` as an `@reward_function` (imports without the SDK via shims) | new |
| `build_dataset.py` | emits `dataset.jsonl` (prompt + `ground_truth_for_eval.module_id`) for RFT | new |
| `fireworks_baseline.py` | baseline / best-of-N runner via the Fireworks inference SDK | new |
| `daytona_runner.py` | Daytona sandbox runner for untrusted code (`REWARDFORGE_RUNNER=daytona`) | new |
| `modal_runner.py` | Modal parallel-scoring + GPU entrypoint (`REWARDFORGE_RUNNER=modal`) | new |
| `eval_bench.py` | offline eval report with bootstrap CIs, band check, and real Modal GRPO curve summary | new |
| `stage_a_checks.py` | API-key-free Stage A regression checks for runner hardening, MS*, and refactor FP rate | new |
| `demo.py` → `demo.html` | interactive bug-kill-meter dashboard, labeled lazy-vs-thorough fallback unless `results.json` exists | updated |
| `selftest.py` | proves lazy-to-thorough kill-rate headroom + hard-to-game checks, **no API key** | updated |
| `tasks.py` | the 10 modules under test for `hud eval` | updated |
| `scorer.py` | (legacy verifier scoring; unused by this task) | unchanged |

## Run it

```bash
cd ~/Downloads/YC---RL-Gym          # the project's own folder (outside JaanHealth)
source .venv/bin/activate           # turn on the project's tools

# 1. validate the signal: NO API key needed
.venv/bin/python selftest.py
#    => 10 modules, weak mean 0.451 vs thorough 1.000; assert-False => 0.0;
#       thorough suite catches the bracket-type bug the weak one misses.

# 2. run Stage A regression checks
python3 stage_a_checks.py

# 3. build the offline eval report
python3 eval_bench.py --out eval_results.json

# 4. build the demo dashboard
.venv/bin/python demo.py

# 3. keys
hud login                                # HUD_API_KEY -> ~/.hud/.env
hud set ANTHROPIC_API_KEY=sk-ant-...

# 4. baseline eval across the modules
hud eval tasks.py claude

# (optional) execute untrusted code in a real sandbox instead of a local subprocess:
#   export REWARDFORGE_RUNNER=daytona     # or: modal
```

## Validated numbers

```
module             mutants  weak    thorough
merge_intervals      18     0.312    1.000
is_balanced          16     0.571    1.000
two_sum              13     0.600    1.000
run_length_encode    18     0.625    1.000
binary_search        18     0.133    1.000
roman_to_int         18     0.000    1.000
gcd                   8     0.625    1.000
flatten              11     0.556    1.000
is_palindrome        10     0.556    1.000
fizzbuzz             18     0.533    1.000
mean (10 modules)           0.451    1.000
```
`assert False`, no-test suites, and fake pass ledgers score **0.0**.

## Training (Fireworks RFT/GRPO)

The same `score_suite` both evaluates and trains through `reward.py`.

Verified local GRPO artifact:

```bash
python3 eval_bench.py --out eval_results.json
# modal curve 0.2333 -> 0.75
```

```bash
pip install fireworks-ai reward-kit         # into the venv
export FIREWORKS_API_KEY=fw-...

# 1. baseline ("before" number) with the inference SDK: also the best-of-N fallback
.venv/bin/python fireworks_baseline.py            # BEST_OF_N=4 for best-of-N

# 2. build the RFT dataset (prompt + ground_truth_for_eval.module_id)
.venv/bin/python build_dataset.py                 # -> dataset.jsonl

# 3. sanity-check the reward locally, then deploy it
reward-kit preview --metrics-folders "kill=." --samples dataset.jsonl
reward-kit deploy  --id testbench-forge --metrics-folders "kill=." --force

# 4. launch the RFT/GRPO job: point Fireworks RFT at the deployed evaluator
#    + dataset.jsonl + a trainable base (e.g. Qwen2.5-32B). Use reward_function(mode="batch")
#    for GRPO pairwise rollout comparison. (Create via the Fireworks RFT dashboard / firectl.)
```

> Verified against docs.fireworks.ai (Jun 2026): the `@reward_function` signature, `EvaluateResult`, `ground_truth` passing, `reward-kit preview/deploy`, and JSONL `ground_truth_for_eval` are exact. The final RFT-job-create step is driven from the Fireworks RFT console once the evaluator is deployed. Confirm the current `firectl`/console flow on the day.

## Sponsor stack ($1,075; the full $950 trio)

| sponsor | $ | role in TestBench-Forge |
|---|---|---|
| **HUD** | 200 | host; the `forge_testbench` template *is* the env |
| **Fireworks** | 500 | **GRPO/RFT**: train an open model to write higher-kill-rate suites; the dense kill-rate reward is GRPO-ideal (the centerpiece) |
| **Modal** | 250 | serverless GPU + parallel sandboxed execution of suites × mutants (embarrassingly parallel) |
| **Daytona** | 100 | optional isolated sandbox for running untrusted agent test code |
| **Anthropic** | 25 | Claude as the frontier baseline in the before/after |

## The demo

Split-screen, one module (`is_balanced`). The **bug-kill meter** can use real `results.json` when model evals exist. Without credentials it shows the honest lazy-vs-thorough fallback: lazy misses the `(]` bug, thorough catches it. The real Modal GRPO curve is presented separately as a training reward artifact, not a held-out trained-model eval.

> "We train models to write tests that catch bugs the easy suite misses, scored only by hidden bugs and guarded by equivalent refactors."

## 24h plan

| block | goal |
|---|---|
| **0-3h** | done: mutation engine, differential filter, hardened suite runner, 10 modules; `selftest` proves headroom and hard-to-game checks. |
| **3–7h** | baseline eval (`hud eval tasks.py claude` + base open model); confirm Fireworks `reward-kit` wraps `score_suite` identically; add 4–6 more modules for training volume. |
| **7-15h** | kick off Fireworks GRPO/RFT on Modal: dense reward + fast eval = many episodes overnight; stream the bug-kill curve into the demo dashboard. |
| **15-22h** | route `_run_suite_once` through a Daytona/Modal sandbox if credentials are available; pull held-out eval for the "after" number. |
| **22-24h** | rehearse the split-screen kill-meter demo; fallback = best-of-N suites with kill-rate as selector. |

## Notes / stretch

- **Python 3.12** (hud-python needs `>=3.11,<3.13`); the venv is pinned.
- **Determinism** via `hashlib` seeds: the mutant pool is fixed at eval time so before/after is comparable. Fresh per-episode mutants are future work, not current behavior.
- **Verilog portability** is the moat: same gym, mutants = injected RTL faults, kill = a failing assertion in simulation. Present software; pitch hardware.
- **Stretch:** richer subtle mutants (lower the base kill rate for a more dramatic curve); multi-turn variant (agent adds tests over turns with coverage feedback).
