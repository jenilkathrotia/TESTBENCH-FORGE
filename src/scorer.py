"""Sandboxed execution of agent-submitted code + scoring.

The agent's answer is *code* (an untrusted `reward()` or `solve()` function). We run
it in a subprocess with a timeout so a crash/hang/`while True` can't take down the env.

PRODUCTION HARDENING (this is the Daytona $100 / Modal $250 prize angle): swap the
local subprocess in `run_calls` for a Daytona or Modal sandbox — same interface,
real isolation against malicious submissions.
"""
from __future__ import annotations

import json
import subprocess
import sys

# Runs in a child process: exec the code, call `func` on each arg-tuple, emit JSON.
_RUNNER = r'''
import json, sys
data = json.loads(sys.stdin.read())
code, func, calls = data["code"], data["func"], data["calls"]
ns = {}
try:
    exec(code, ns)
except Exception as e:
    print(json.dumps({"error": "compile: %r" % (e,), "results": [None] * len(calls)}))
    raise SystemExit
fn = ns.get(func)
if not callable(fn):
    print(json.dumps({"error": "no %s() defined" % func, "results": [None] * len(calls)}))
    raise SystemExit
res = []
for args in calls:
    try:
        v = fn(*args)
        try:
            json.dumps(v); sv = v
        except Exception:
            sv = str(v)
        res.append({"ok": True, "value": sv})
    except Exception as e:
        res.append({"ok": False, "error": "%r" % (e,)})
print(json.dumps({"results": res}))
'''


def run_calls(code: str, func: str, calls: list, timeout: float = 6.0) -> dict:
    """Execute `code`, then call func(*args) for each args in `calls`.

    Returns {"results": [ {"ok": True, "value": ...} | {"ok": False, "error": ...} | None ],
             "error": <optional global error>}.
    """
    payload = json.dumps({"code": code, "func": func, "calls": calls})
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _RUNNER],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "results": [None] * len(calls)}
    out = (proc.stdout or "").strip().splitlines()
    if not out:
        return {"error": "exec_failed: %s" % ((proc.stderr or "")[-300:]), "results": [None] * len(calls)}
    try:
        return json.loads(out[-1])
    except Exception:
        return {"error": "parse_failed: %s" % (out[-1][:300]), "results": [None] * len(calls)}


def _to_unit_float(v):
    try:
        f = float(v)
    except Exception:
        return None
    if f != f:  # NaN
        return 0.0
    return max(0.0, min(1.0, f))


def balanced_accuracy(code: str, bank: list, timeout: float = 8.0):
    """Score a `reward(prompt, completion)` verifier on a labeled bank.

    bank: list of (prompt, completion, label) with label in {0, 1}.
    Returns (balanced_accuracy in [0,1], info dict). A verifier that crashes on a
    case is counted as a wrong prediction for that case. A degenerate verifier that
    returns the SAME value for every case is hard-zeroed.
    """
    calls = [[p, c] for (p, c, _l) in bank]
    res = run_calls(code, "reward", calls, timeout=timeout)
    results = res.get("results") or [None] * len(bank)

    raws, preds, labels = [], [], []
    for (p, c, label), r in zip(bank, results):
        val = _to_unit_float(r.get("value")) if isinstance(r, dict) and r.get("ok") else None
        if val is None:
            preds.append(1 - label)  # crash/garbage => treat as a miss
            labels.append(label)
            continue
        raws.append(val)
        preds.append(1 if val >= 0.5 else 0)
        labels.append(label)

    if not raws:
        return 0.0, {"error": res.get("error", "all calls failed"), "n": len(bank)}
    if len(raws) == len(bank) and len({round(x, 6) for x in raws}) == 1:
        return 0.0, {"reason": "constant output (degenerate verifier)", "n": len(bank)}

    pos = [pr for pr, la in zip(preds, labels) if la == 1]
    neg = [pr for pr, la in zip(preds, labels) if la == 0]
    tpr = sum(1 for pr in pos if pr == 1) / len(pos) if pos else 0.0
    tnr = sum(1 for pr in neg if pr == 0) / len(neg) if neg else 0.0
    bal = (tpr + tnr) / 2.0
    return bal, {"tpr": round(tpr, 3), "tnr": round(tnr, 3), "n": len(bank), "ok_calls": len(raws)}


def solver_accuracy(code: str, bank: list, timeout: float = 8.0):
    """Score a `solve(text) -> str` tool by exact-match accuracy on held-out (text, gold)."""
    calls = [[text] for (text, _g) in bank]
    res = run_calls(code, "solve", calls, timeout=timeout)
    results = res.get("results") or [None] * len(bank)
    correct = 0
    for (text, gold), r in zip(bank, results):
        if isinstance(r, dict) and r.get("ok"):
            v = r.get("value")
            if isinstance(v, str) and v.strip() == str(gold).strip():
                correct += 1
    return correct / len(bank), {"correct": correct, "n": len(bank), "error": res.get("error")}


def dry_run(code: str, func: str, calls: list, timeout: float = 6.0) -> dict:
    """Run code on caller-provided calls and return raw outputs (no labels). For the MCP tool."""
    return run_calls(code, func, calls, timeout=timeout)
