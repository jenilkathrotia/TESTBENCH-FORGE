# TestBench-Forge

**An RL gym that trains agents to write the test suite that catches the most bugs** — rewarded by how many hidden, freshly-injected bugs (mutants) their tests kill.

> The thesis: recursive self-improvement is bottlenecked on *trustworthy verification*. The scarcest verifier of all is a **test suite that isn't fooled by a bug that passes the easy cases.** TestBench-Forge trains models to write exactly that — and proves it by mutation testing: run the suite over a hidden pool of buggy variants and count the kills.

Track fit: **Agentic Collaboration** (the pytest variant you present) with a **Chip Design** moat (the same gym ports to Verilog testbenches — mention it, build software).

## Status (what's proven, honestly)
- ✅ **Verifiable, non-gameable environment** — 10 modules, hidden mutants, automatic kill-rate reward (no LLM judge).
- ✅ **Reproducible discrimination (no API key):** a lazy suite scores **0.62**, a thorough suite **1.0**, `assert False` → **0** (`python selftest.py`).
- ✅ **Real models scored live through it:** Qwen3-8B **0.90**, Claude (HUD gateway) **0.60**.
- ✅ **RL training completed, with held-out generalization** — trained Qwen2.5-3B with GRPO on a single A100 (Modal, `modal_grpo.py`) on **7 modules**, evaluated on **3 modules it never trained on**. Mean mutant-kill rate: train modules **0.11 → 0.91**, and **held-out (unseen) 0.38 → 0.77** — `binary_search` went **0.39 → 1.00** without ever being trained on. That's a *transferable* test-writing skill, not memorization (KL < 0.05; completions got shorter, not padded). See `TRAINING_STATS.md` + `grpo_result.json` + `demo_training.html`.

## The loop

1. Agent sees a module + its **reference implementation**.
2. It writes a **pytest-style test suite** (functions named `test_*`).
3. The harness runs the suite against a **hidden pool of mutants** (buggy variants).
4. **Reward = #mutants killed / #mutants**, gated by the suite passing the reference + behavior-equivalent refactors (the over-specification penalty).

## Why it's a strong RL environment (not an eval)

- **Multi-signal, verifiable reward** with a clean execution oracle — no LLM judge anywhere.
- **Non-gameable** (validated): `assert False` → fails the reference gate → **0**; mutants are never shown, so you can't target them — *you cannot fake killing a bug you've never seen*; the over-spec gate kills brittle snapshot tests.
- **Infinite data**: AST mutation operators auto-generate buggy variants × unlimited modules. Mutants are differentially filtered against the reference so the pool is all **non-equivalent** (killable) — giving a clean 1.0 ceiling.

## Files

| file | what | touched? |
|---|---|---|
| `testbench.py` | **10 modules** + reference impls, **AST mutation engine**, differential filter, suite-runner dispatch, kill-rate scorer, prompt | the new core |
| `env.py` | HUD `forge_testbench` template + `run_tests` MCP tool (gate-only dry-run) | + template |
| `reward.py` | **Fireworks reward-kit adapter** — wraps `score_suite` as an `@reward_function` (imports without the SDK via shims) | new |
| `build_dataset.py` | emits `dataset.jsonl` (prompt + `ground_truth_for_eval.module_id`) for RFT | new |
| `fireworks_baseline.py` | baseline / best-of-N runner via the Fireworks inference SDK | new |
| `daytona_runner.py` | Daytona sandbox runner for untrusted code (`REWARDFORGE_RUNNER=daytona`) | new |
| `modal_runner.py` | Modal parallel-scoring + GPU entrypoint (`REWARDFORGE_RUNNER=modal`) | new |
| `demo.py` → `demo.html` | interactive bug-kill-meter dashboard ("Run RFT ▶" animates base→trained) | new |
| `selftest.py` | proves weak→thorough kill-rate headroom + non-gameability, **no API key** | updated |
| `tasks.py` | the 10 modules under test for `hud eval` | updated |
| `scorer.py` | (legacy verifier scoring; unused by this task) | unchanged |

## Run it

```bash
cd ~/Downloads/YC---RL-Gym          # the project's own folder (outside JaanHealth)
source .venv/bin/activate           # turn on the project's tools

# 1. validate the signal — NO API key needed
.venv/bin/python selftest.py
#    => 10 modules, weak mean 0.62 vs thorough 1.00 (clean ceiling); assert-False => 0.0;
#       thorough suite catches the bracket-type bug the weak one misses.

# 2. build the demo dashboard (open demo.html — "Run RFT ▶" animates base->trained)
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
roman_to_int         18     0.222    1.000
binary_search        18     0.444    1.000
is_balanced           4     0.500    1.000   <- hero demo module
flatten               1     0.000    1.000
two_sum               4     0.750    1.000
is_palindrome         4     0.750    1.000
merge_intervals      18     0.778    1.000
fizzbuzz             18     0.833    1.000
run_length_encode    14     0.929    1.000
gcd                   1     1.000    1.000
mean (10 modules)           0.621    1.000   <- the live RFT demo arc
```
Every module reaches a clean **1.000** ceiling (all mutants killable); `assert False` and
no-test suites score **0.0** (fail the reference gate).

## Training (Fireworks RFT/GRPO)

The same `score_suite` both evaluates and trains — wired through `reward.py`.

```bash
pip install fireworks-ai reward-kit         # into the venv
export FIREWORKS_API_KEY=fw-...

# 1. baseline ("before" number) with the inference SDK — also the best-of-N fallback
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

> Verified against docs.fireworks.ai (Jun 2026): the `@reward_function` signature, `EvaluateResult`, `ground_truth` passing, `reward-kit preview/deploy`, and JSONL `ground_truth_for_eval` are exact. The final RFT-job-create step is driven from the Fireworks RFT console once the evaluator is deployed — confirm the current `firectl`/console flow on the day.

## Sponsor stack ($1,075; the full $950 trio)

| sponsor | $ | role in TestBench-Forge |
|---|---|---|
| **HUD** | 200 | host; the `forge_testbench` template *is* the env |
| **Fireworks** | 500 | **GRPO/RFT** — train an open model to write higher-kill-rate suites; the dense kill-rate reward is GRPO-ideal (the centerpiece) |
| **Modal** | 250 | serverless GPU + parallel sandboxed execution of suites × mutants (embarrassingly parallel) |
| **Daytona** | 100 | isolated sandboxes for running untrusted agent test code AND untrusted mutants — **load-bearing here** |
| **Anthropic** | 25 | Claude as the frontier baseline in the before/after |

## The demo

Split-screen, one module (`is_balanced`). The **bug-kill meter** climbs as the model trains. Base model writes a happy-path suite → kills **~50%**, and live it **fails to catch** the bug that accepts `(]`. The RFT'd model writes boundary/edge tests → **100%**, catches it. Diff on screen: *"this bug slipped past the base model's tests; the trained model's tests caught it."* Fallback: pre-recorded curve.

> "We trained a model to write the test that catches the bug a human reviewer misses — scored only by bugs it has never seen."

## 24h plan

| block | goal |
|---|---|
| **0–3h** | ✅ done — mutation engine, differential filter, suite runner, 4 modules; `selftest` proves headroom + non-gameability + clean 1.0 ceiling. |
| **3–7h** | baseline eval (`hud eval tasks.py claude` + base open model); confirm Fireworks `reward-kit` wraps `score_suite` identically; add 4–6 more modules for training volume. |
| **7–15h** | kick off Fireworks GRPO/RFT on Modal — dense reward + fast eval = many episodes overnight; stream the bug-kill curve into the demo dashboard. |
| **15–22h** | route `_run_suite_once` through a Daytona/Modal sandbox (the untrusted-code prize moment); pull the checkpoint, held-out eval for the "after" number. |
| **22–24h** | rehearse the split-screen kill-meter demo; fallback = best-of-N suites with kill-rate as selector. |

## Notes / stretch

- **Python 3.12** (hud-python needs `>=3.11,<3.13`); the venv is pinned.
- **Determinism** via `hashlib` seeds — the mutant pool is fixed at eval time so before/after is comparable. (Regenerate fresh mutants per episode during *training* as an anti-overfit measure.)
- **Verilog portability** is the moat: same gym, mutants = injected RTL faults, kill = a failing assertion in simulation. Present software; pitch hardware.
- **Stretch:** richer subtle mutants (lower the base kill rate for a more dramatic curve); multi-turn variant (agent adds tests over turns with coverage feedback).
