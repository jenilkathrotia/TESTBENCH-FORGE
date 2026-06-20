"""Daytona sandbox runner for TestBench-Forge — the untrusted-code prize moment (Daytona $100).

Drop-in for `testbench._run_suite_local`: same `(impl_src, suite_src) -> bool` interface, but
executes the impl + agent-authored suite inside an isolated Daytona sandbox instead of a local
subprocess. Activate with:

    pip install daytona-sdk          # confirm exact package name at install time
    export DAYTONA_API_KEY=...
    export REWARDFORGE_RUNNER=daytona

Import-safe: importing this module never requires the SDK — it is only imported (lazily) when a
suite is actually run through Daytona. The Daytona API symbols below match its documented Python
SDK; confirm them on the day (a 2-minute check at the sponsor table).

Why it matters: the agent's test suite AND the mutants are untrusted code we execute at scale.
A local subprocess is fine for the offline self-test; Daytona is the real isolation boundary and
the concrete "best use of Daytona" story for the prize.
"""
from __future__ import annotations

import base64
import json
import os

# Reuse the exact in-sandbox harness used locally (prints {"passed": bool, "n": int}).
from testbench import _SUITE_RUNNER

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        # Confirm symbol names on install — Daytona's documented Python SDK.
        from daytona_sdk import Daytona, DaytonaConfig
        _CLIENT = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
    return _CLIENT


def run_suite_once(impl_src: str, suite_src: str, timeout: float = 8.0) -> bool:
    """Execute impl + suite in a fresh Daytona sandbox; True iff the suite passes."""
    payload = json.dumps({"impl": impl_src, "suite": suite_src})
    b64 = base64.b64encode(payload.encode()).decode()
    # The shared runner reads its payload from stdin; inject it since code_run has no stdin.
    program = (
        "import base64, io, sys\n"
        f"sys.stdin = io.StringIO(base64.b64decode('{b64}').decode())\n"
        + _SUITE_RUNNER
    )
    daytona = _client()
    sandbox = daytona.create()
    try:
        resp = sandbox.process.code_run(program)
        out = (getattr(resp, "result", "") or "").strip().splitlines()
        return bool(json.loads(out[-1]).get("passed")) if out else False
    except Exception:
        return False
    finally:
        try:
            daytona.remove(sandbox)
        except Exception:
            pass
