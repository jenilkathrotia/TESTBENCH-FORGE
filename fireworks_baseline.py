"""Baseline / best-of-N runner for TestBench-Forge using the Fireworks inference SDK.

Produces a raw baseline sample for a base model and doubles as the demo fallback:
best-of-N suites selected by score. Gate-failed suites are included as 0.0 scores.
Output uses the shared `eval_schema` so baselines and RFT runs compare directly.

A baseline sample is NOT a stable capability number: a single best-of-1 pass with gate
failures should not be presented as the model's capability without repeated seeds and
confidence intervals. Use `--runs` to capture variance.

Uses the exact SDK shape:
    from fireworks import Fireworks
    client = Fireworks()
    client.chat.completions.create(model=..., messages=[...])

Setup:
    pip install fireworks-ai
    export FIREWORKS_API_KEY=fw-...

Examples:
    .venv/bin/python fireworks_baseline.py                                   # all modules, 1 pass
    .venv/bin/python fireworks_baseline.py --modules binary_search --runs 1  # smoke one module
    .venv/bin/python fireworks_baseline.py \\
        --model accounts/fireworks/models/llama-v3p1-8b-instruct \\
        --runs 3 --best-of-n 4 --out /tmp/fireworks_base.json               # variance + best-of-N

CLI flags override the matching env vars (FW_MODEL, FW_MODULES, BEST_OF_N, FW_RUNS,
FW_TEMP, FW_TIMEOUT, FW_RESULTS, FW_PROVIDER) so old invocations keep working.
"""
import argparse
import os
import traceback
from datetime import datetime, timezone

import eval_schema
import families
import testbench


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default=os.environ.get("FW_MODEL", "accounts/fireworks/models/gpt-oss-120b"),
                   help="Fireworks base model to baseline")
    p.add_argument("--modules", default=os.environ.get("FW_MODULES", ""),
                   help="comma-separated module subset; default = all")
    p.add_argument("--best-of-n", type=int, default=int(os.environ.get("BEST_OF_N", "1")),
                   help="candidates sampled per prompt, best kept (within one run)")
    p.add_argument("--runs", type=int, default=int(os.environ.get("FW_RUNS", "1")),
                   help="repeated full passes for variance / CI")
    p.add_argument("--temperature", type=float, default=float(os.environ.get("FW_TEMP", "0.7")))
    p.add_argument("--timeout", type=float, default=float(os.environ.get("FW_TIMEOUT", "90")),
                   help="per-call timeout (seconds)")
    p.add_argument("--out", default=os.environ.get("FW_RESULTS", "fireworks_results.json"),
                   help="output path (eval_schema JSON)")
    p.add_argument("--provider", default=os.environ.get("FW_PROVIDER", "fireworks"),
                   help="provider label recorded in the result")
    return p.parse_args()


def select_modules(spec):
    if not spec.strip():
        return list(testbench.MODULES)
    wanted = [m.strip() for m in spec.split(",") if m.strip()]
    unknown = [m for m in wanted if m not in testbench.MODULES]
    if unknown:
        raise SystemExit(f"unknown modules: {unknown}. known: {list(testbench.MODULES)}")
    return wanted


def run_module_once(client, model, module_id, n, temperature):
    """Best-of-n within a single pass: returns (best_rate, best_info)."""
    prompt = testbench.build_testbench_prompt(module_id)
    best_rate, best_info = -1.0, {}
    for _ in range(n):
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        suite = families.extract_code(resp.choices[0].message.content)
        rate, info = testbench.score_suite(module_id, suite)
        if rate > best_rate:
            best_rate, best_info = rate, info
    return best_rate, best_info


def _now():
    return datetime.now(timezone.utc).isoformat()


def main():
    args = parse_args()
    modules = select_modules(args.modules)
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1 (a run that never executes is not a 0.0 result)")
    if args.best_of_n < 1:
        raise SystemExit("--best-of-n must be >= 1")

    api_key = os.environ.get("FIREWORKS_API_KEY")
    if not api_key:
        eval_schema.write(args.out, eval_schema.benchmark_result(
            args.provider, args.model, [], status="blocked",
            best_of_n=args.best_of_n, runs=args.runs, temperature=args.temperature,
            created_at=_now(), error="FIREWORKS_API_KEY is not set in this process",
            blocked_on="missing_fireworks_api_key", timeout_seconds=args.timeout))
        print("blocked: FIREWORKS_API_KEY is not set in this process")
        print(f"wrote {args.out}")
        return

    from fireworks import Fireworks

    client = Fireworks(api_key=api_key, timeout=args.timeout)
    print(f"provider={args.provider}  model={args.model}  best-of-{args.best_of_n}  runs={args.runs}\n")

    # accumulate per-module scores across runs so the result carries variance
    acc = {m: {"scores": [], "killed": 0, "mutants": 0, "gate": False, "best_rate": -1.0} for m in modules}
    for r in range(args.runs):
        for module_id in modules:
            try:
                rate, info = run_module_once(client, args.model, module_id, args.best_of_n, args.temperature)
            except Exception as exc:
                partial = [eval_schema.module_result(
                    m, eval_schema.run_stats(acc[m]["scores"])["mean"],
                    acc[m]["killed"], acc[m]["mutants"], acc[m]["gate"],
                    best_of_n=args.best_of_n, runs=args.runs, scores=acc[m]["scores"],
                    error=None if acc[m]["scores"] else "not evaluated before failure") for m in modules]
                eval_schema.write(args.out, eval_schema.benchmark_result(
                    args.provider, args.model, partial, status="blocked",
                    best_of_n=args.best_of_n, runs=args.runs, temperature=args.temperature,
                    created_at=_now(), error=str(exc), traceback=traceback.format_exc(limit=4),
                    blocked_on="fireworks_model_access", timeout_seconds=args.timeout, completed_runs=r))
                print(f"blocked on Fireworks model access for {args.model}: {exc}")
                print(f"wrote {args.out}")
                return
            cur = acc[module_id]
            cur["scores"].append(rate)
            if rate > cur["best_rate"]:  # keep killed/mutants/gate from the best-scoring run, not just the last
                cur["best_rate"] = rate
                cur["killed"], cur["mutants"], cur["gate"] = info.get("killed", 0), info.get("mutants", 0), bool(info.get("gate"))
            gate = "ok" if info.get("gate") else "GATE-FAIL"
            print(f"  run {r + 1}/{args.runs}  {module_id:20s} score={rate:.3f}  "
                  f"({info.get('killed', 0)}/{info.get('mutants', 0)} mutants, gate {gate})")

    mod_results = []
    for module_id in modules:
        cur = acc[module_id]
        stats = eval_schema.run_stats(cur["scores"])
        mod_results.append(eval_schema.module_result(
            module_id, stats["mean"], cur["killed"], cur["mutants"], cur["gate"],
            best_of_n=args.best_of_n, runs=args.runs, scores=cur["scores"]))
    payload = eval_schema.benchmark_result(
        args.provider, args.model, mod_results, status="ok",
        best_of_n=args.best_of_n, runs=args.runs, temperature=args.temperature,
        created_at=_now(), timeout_seconds=args.timeout)
    eval_schema.write(args.out, payload)
    print(f"\n  mean score incl. gate failures (mean over {args.runs} run(s)) = {payload['mean_score']:.3f}")
    print(f"  gate failures: {payload['n_gate_failures']}/{payload['n_modules']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
