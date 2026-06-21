# TestBench-Forge — 90-Second Demo Script

Source of record: `docs/TECHNICAL_DEEP_DIVE.md`. UI: `./run.sh` → `http://localhost:5173`.
Advance beats with `→` / `space` (or `1`–`4` to jump). ~225 spoken words = ~90s at a calm pace.

**Before recording:** full-screen browser, hide bookmarks bar, start on the Hero (step 1). Numbers
spoken are the README n=16 headline (held-out 0.23 → 0.79, binary_search 0.31 → 0.93). Note: the
on-screen per-module bars in Beat 3 use the saved-adapter n=5 set (binary_search 0.389 → 1.00), so
narrate the headline number, not the bar tooltip.

---

## [0:00–0:12] HERO / Thesis — hook, track, problem

**SHOW:** Hero screen. Title "We built an RL reward we couldn't game." 4 metric counters animate in.

**SAY (phrases):**
- HUD × YC Frontier RL Environments hackathon. Track: **Agentic Collaboration**.
- The problem: self-improvement is bottlenecked on **trustworthy verification**, not generation.
- An LLM-judge reward is gameable. The only durable RL signal is an **execution oracle**.

## [0:12–0:24] HERO — how we solve it

**SHOW:** gesture across the 4 counters (lazy 0.62 · thorough 1.00 · 12 attacks → 0 · held-out 0.79).

**SAY:**
- Our gym: the model writes the **pytest suite that kills the most hidden bugs** (mutants).
- Reward = mutants killed, gated by first passing the reference. No LLM judge, no human labels.

## [0:24–0:42] BEAT 1 — Honest oracle

**SHOW:** press `→`. The "Watch one mutant" lanes (lazy 0.62 / thorough 1.00 / assert-False 0.00),
then the base-vs-trained `binary_search` suite diff (0.000 vs 0.944).

**SAY:**
- Pure execution oracle. Run `selftest.py` on system Python: same numbers in 5 seconds, no key, no GPU.
- Lazy suite 0.62, thorough 1.00, `assert False` 0.00 (it fails the gate).
- Frontier baselines (**Anthropic** Claude, Qwen3-8B) scored live through the **HUD** gateway.

## [0:42–1:02] BEAT 2 — We broke our own reward

**SHOW:** press `→`. The 12-attack list auto-flips red **EXPLOIT** → green **0.000**; then the three fixes.

**SAY:**
- The suite is untrusted code, so we attacked our own reward, and broke it.
- A frame-walk exploit read the hidden answer and faked a perfect 1.0 with zero real tests.
- Fixed: **import allowlist + frame isolation + nonce-signed verdict**. 12 of 12 attacks now score 0.
- **Daytona** sandboxes the untrusted suites for safe execution.

## [1:02–1:22] BEAT 3 — It generalizes (the RSI signal)

**SHOW:** press `→`. Held-out kill-meter bars climb (binary_search hero), the GRPO reward curve
draws itself 0.17 → 1.0, train-module bars fill.

**SAY:**
- Trained Qwen2.5-3B with GRPO on a single **Modal** A100, on 7 modules.
- Evaluated on **3 it never trained on**: held-out 0.23 → 0.79, `binary_search` 0.31 → 0.93.
- Same reward is wired to **Fireworks** Eval-Protocol RFT (a qwen3 RFT runs free end-to-end).
- You don't label outputs, you train the **grader**, and the grading generalizes.

## [1:22–1:30] CLOSE — sponsors + wedge

**SHOW:** point to the footer: sponsor grid + TRACK + chip-design wedge.

**SAY:**
- **Modal** trained it, **HUD** hosts the env and baselines, **Fireworks** the RFT handoff,
  **Anthropic** the baseline, **Daytona** the sandbox.
- Ports to chip design: mutants become injected RTL faults, a kill is a failing assertion.
- TestBench-Forge: train the test that catches the bug a human reviewer misses.

---

## Sponsor integration at a glance (say each at its beat)

| Sponsor | How it's integrated | Where on screen |
| --- | --- | --- |
| **HUD** | The `forge_testbench` RL env + frontier baselines via the HUD gateway; the hackathon track | Beat 1 (baselines), footer |
| **Modal** | Serverless A100 where the GRPO run actually trained; adapter on a Modal volume | Beat 3 (training + curve) |
| **Fireworks** | Eval-Protocol RFT handoff wired to the same reward (`reward.py`); a qwen3 RFT runs free | Beat 3, footer |
| **Anthropic** | Claude as the frontier before/after baseline | Beat 1, footer |
| **Daytona** | `daytona_runner.py` sandbox for untrusted suites | Beat 2, footer |

## Presenter notes
- One honest line if asked: training landed on Modal because HUD's backend hit capacity and the
  Fireworks RFT was billing-blocked at the time; the verified headline is the Modal run.
- If short on time, cut Beat 1's suite-diff and the train-module bars; keep the attack-flip and the
  held-out curve (those are the two strongest visuals).
- Backup proof, no slides: a terminal running `python3 selftest.py` and `python3 security_checks.py`.
