"""RewardForge — a HUD RL environment that trains models to WRITE verifiers.

The RSI thesis (cf. SIA, arXiv 2026): self-improvement needs a trustworthy reward
signal. RewardForge is the environment that *manufactures* those signals — and trains
models to author them better than humans.

Two task types:
  • forge_verifier(family_id)  [CORE / grand-prize]
        The agent authors `reward(prompt, completion)` for a task family. Reward =
        balanced accuracy of that verifier on a HIDDEN bank of correct + adversarial
        completions it never sees. Non-gameable: the agent never sees the answer key,
        and the meta-check ("did your verdicts match the hidden labels?") is a plain
        set comparison — no LLM judge anywhere.
  • forge_harness(task_id)     [OPTIONAL / SIA "harness lever"]
        The agent rewrites a brittle base tool; reward = the base agent's held-out
        accuracy with the improvement applied. Same env, one extra task type.

Run locally (no API key needed): .venv/bin/python selftest.py
Run an agent over the env:        hud eval tasks.py claude
Single local smoke test:          .venv/bin/python env.py
"""
import asyncio

from hud.environment import Environment
from hud.capabilities import Capability
from fastmcp import FastMCP

import families
import testbench
from scorer import balanced_accuracy, solver_accuracy, dry_run

env = Environment(name="rewardforge")

# =============================================================================
# MCP TOOLS — let the agent dry-run a draft before it commits to an answer
# =============================================================================
server = FastMCP(name="rewardforge-tools")


@server.tool()
async def test_verifier(code: str, cases: list[dict]) -> dict:
    """Dry-run a candidate `reward(prompt, completion)` on cases you invent.

    cases = [{"prompt": str, "completion": str}, ...]
    Returns the verifier's raw score for each case (NO labels) so you can debug
    before submitting your final answer.
    """
    calls = [[c.get("prompt", ""), c.get("completion", "")] for c in cases]
    return dry_run(code, "reward", calls)


@server.tool()
async def test_solver(code: str, texts: list[str]) -> dict:
    """Dry-run a candidate `solve(text)` on sample texts. Returns each output."""
    return dry_run(code, "solve", [[t] for t in texts])


@server.tool()
async def run_tests(module_id: str, suite_code: str) -> dict:
    """Dry-run a candidate test suite against the REFERENCE implementation only (no mutants).

    Returns whether your suite passes the reference + equivalent refactors (the gate). Use
    this to make sure your tests aren't over-specified before you submit. The hidden mutant
    kill-rate (your actual reward) is NOT revealed here.
    """
    m = testbench.MODULES.get(module_id)
    if not m:
        return {"error": f"unknown module_id; choose from {list(testbench.MODULES)}"}
    gate = all(testbench._run_suite_once(impl, suite_code)
               for impl in [m["reference"]] + m["equivalents"])
    return {"passes_gate": gate, "module": module_id}


@env.initialize
async def _start():
    # Stand up the tool server and publish it as an MCP capability the agent can use.
    asyncio.create_task(server.run_http_async(host="127.0.0.1", port=8765))
    await asyncio.sleep(0.3)  # let it bind
    env.add_capability(Capability.mcp(name="tools", url="http://127.0.0.1:8765/mcp"))


# =============================================================================
# TASK 1 (CORE) — write a verifier; reward = balanced accuracy on a hidden bank
# =============================================================================
@env.template(id="forge_verifier")
async def forge_verifier(family_id: str):
    answer = yield families.build_verifier_prompt(family_id)
    code = families.extract_code(answer or "")
    bank = families.get_hidden_bank(family_id)
    score, _info = balanced_accuracy(code, bank)
    yield score


# =============================================================================
# TASK 2 (OPTIONAL, SIA harness lever) — improve a base tool; reward = accuracy
# =============================================================================
@env.template(id="forge_harness")
async def forge_harness(task_id: str = "extract_total"):
    answer = yield families.build_harness_prompt(task_id)
    code = families.extract_code(answer or "")
    bank = families.harness_bank("hidden")
    score, _info = solver_accuracy(code, bank)
    yield score


# =============================================================================
# TASK 3 (TestBench-Forge) — write a test suite; reward = hidden-mutant kill rate
# =============================================================================
@env.template(id="forge_testbench")
async def forge_testbench(module_id: str):
    answer = yield testbench.build_testbench_prompt(module_id)
    suite = families.extract_code(answer or "")
    rate, _info = testbench.score_suite(module_id, suite)
    yield rate


# =============================================================================
# TEST — single local rollout (needs ANTHROPIC_API_KEY)
# =============================================================================
async def test():
    from hud.agents.claude import ClaudeAgent
    from hud import LocalRuntime

    agent = ClaudeAgent()
    task = forge_verifier(family_id="count_letter")
    job = await task.run(agent, runtime=LocalRuntime(__file__))
    print("forge_verifier[count_letter] reward:", job.reward)


if __name__ == "__main__":
    asyncio.run(test())
