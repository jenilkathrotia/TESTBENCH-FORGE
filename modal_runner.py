"""Modal runner for TestBench-Forge — parallel sandboxed scoring + GPU entrypoint (Modal $250).

Kill-rate scoring is embarrassingly parallel: a candidate suite is run against the reference +
equivalents + every mutant independently. Modal fans those out across containers, which is the
real bottleneck during RFT (thousands of rollouts × ~20 impls each).

Roles:
  1. run_suite_once(impl, suite) -> bool        — drop-in for the local runner (REWARDFORGE_RUNNER=modal)
  2. score_suites_parallel(module_id, suites)   — score many candidate suites for a module in parallel
  3. (GPU) the same image can host a vLLM / rollout worker for the training loop

Setup:
    pip install modal
    modal token new
    modal run modal_runner.py        # smoke test
    # or: REWARDFORGE_RUNNER=modal with a deployed app

Import-safe: `import modal_runner` works without modal installed; the SDK is only needed to run.
Confirm the current Modal API (App / Image / .remote / .map) at install time.
"""
from __future__ import annotations

try:
    import modal
    _HAS_MODAL = True
except Exception:
    _HAS_MODAL = False


if _HAS_MODAL:
    app = modal.App("testbench-forge")
    # Ship the gym into the image so the remote functions can import it.
    image = (
        modal.Image.debian_slim(python_version="3.12")
        .pip_install("hud-python")
        .add_local_python_source("testbench")
    )

    @app.function(image=image)
    def _run_remote(impl_src: str, suite_src: str) -> bool:
        import testbench
        return testbench._run_suite_local(impl_src, suite_src)

    @app.function(image=image)
    def _score_remote(args) -> float:
        module_id, suite_src = args
        import testbench
        rate, _info = testbench.score_suite(module_id, suite_src)
        return rate


def run_suite_once(impl_src: str, suite_src: str, timeout: float = 8.0) -> bool:
    """Single isolated run on Modal. Illustrative — for scale use score_suites_parallel."""
    if not _HAS_MODAL:
        raise RuntimeError("modal not installed; `pip install modal`")
    with app.run():
        return _run_remote.remote(impl_src, suite_src)


def score_suites_parallel(module_id: str, suites: list) -> list:
    """Score many candidate suites for one module in parallel across Modal containers."""
    if not _HAS_MODAL:
        raise RuntimeError("modal not installed; `pip install modal`")
    with app.run():
        return list(_score_remote.map([(module_id, s) for s in suites]))


if _HAS_MODAL:
    @app.local_entrypoint()
    def _smoke():
        import testbench
        mid = next(iter(testbench.MODULES))
        ref = testbench.MODULES[mid]["reference"]
        # a trivially-passing suite for the reference (sanity check the remote path)
        suite = f"def test_smoke():\n    assert {testbench.MODULES[mid]['func']} is not None\n"
        print(mid, "remote suite-run passed:", _run_remote.remote(ref, suite))
