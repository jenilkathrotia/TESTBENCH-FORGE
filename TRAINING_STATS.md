# Training stats — GRPO on TestBench-Forge

**Run:** Qwen2.5-3B-Instruct · GRPO (TRL, LoRA r=16/α=32) · 1× A100-80GB (Modal) · 80 steps · 6 generations/prompt · lr 1e-5 · 43 min (~32s/step).
**Reward:** fraction of hidden, freshly-injected mutants the model's test suite kills — non-gameable, no LLM judge.

## Result
| metric | value |
|---|---|
| baseline (first-10 mean) | **0.233** |
| trained (last-10 mean) | **0.750** |
| best step | **1.00** |
| block means (per 20 steps) | 0.354 → 0.580 → 0.732 → 0.766 |

A clean, monotonic **+3.2×** climb. Full per-step curve in `grpo_rewards.txt`; visual in `demo_training.html`.

## Training health
| metric | trend | reading |
|---|---|---|
| KL divergence | mean 0.012, max 0.045 | low + stable — improved **without drifting** from base |
| grad norm | mean 0.37, max 0.88 | no exploding gradients |
| reward std (within group) | 0.41 → 0.34 | **converging** to consistent solutions |
| completion length | 269 → **160 tokens** | learned to write **more concise** suites — higher kill rate, fewer tokens |

**Takeaway:** the model learned to catch more bugs with *fewer* tokens while KL stayed under 0.05 — genuine test-writing skill, not reward-hacking.

Reproduce: `modal run modal_grpo.py` (auth once with `python -m modal setup`).
