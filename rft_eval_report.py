"""Generate a Markdown comparison report from TestBench-Forge eval result files.

Reads one or more `eval_schema` JSON results (Fireworks base, Fireworks RFT, local Gemma,
...) and writes a Markdown report: mean scores, per-module deltas versus a baseline, gate
failures, regressions, best-of-N / runs metadata, and an enforced caveats section.

The caveats are not optional decoration: a best-of-1 single-run sample with gate failures
is not a stable capability number, and this report says so whenever the inputs warrant it.

Run:
    .venv/bin/python rft_eval_report.py \\
        --baseline /tmp/fireworks_base.json \\
        --inputs /tmp/fireworks_rft.json /tmp/gemma4.json \\
        --out rft_report.md

With no --baseline, the first --inputs file is treated as the baseline column.
"""
import argparse

import eval_schema

REGRESSION_EPS = 5e-4  # only flag a regression visible at the 3-decimal display (matches _delta's near-zero snap)


def _label(res):
    prov = res.get("provider", "?")
    model = (res.get("model") or "?").split("/")[-1]
    return f"{prov}:{model}"


def _module_scores(res):
    """module_id -> module record, tolerant of blocked/partial results."""
    return {m["module"]: m for m in res.get("modules", [])}


def _fmt(x):
    return f"{x:.3f}" if isinstance(x, (int, float)) else str(x)


def _delta(cur, base):
    d = cur - base
    if abs(d) < 5e-4:  # rounds to 0.000 at 3dp; show a clean neutral zero (no "-0.000")
        return "+0.000"
    sign = "+" if d > 0 else "-"
    return f"{sign}{abs(d):.3f}"


def build_report(baseline, others):
    """baseline: result dict (or None). others: list of result dicts. Returns markdown str."""
    results = ([baseline] if baseline else []) + others
    lines = []
    lines.append("# TestBench-Forge RFT Eval Report")
    lines.append("")

    # 1. run metadata
    lines.append("## Runs")
    lines.append("")
    lines.append("| label | provider | model | status | best-of-N | runs | temp | mean | gate fails |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for res in results:
        lines.append(
            f"| {_label(res)} | {res.get('provider','?')} | `{res.get('model','?')}` | "
            f"{res.get('status','?')} | {res.get('best_of_n','?')} | {res.get('runs','?')} | "
            f"{res.get('temperature','?')} | {_fmt(res.get('mean_score', 0.0))} | "
            f"{res.get('n_gate_failures','?')}/{res.get('n_modules','?')} |")
    lines.append("")

    # 2. mean score + lift vs baseline
    if baseline:
        lines.append("## Mean score and lift vs baseline")
        lines.append("")
        lines.append(f"Baseline: **{_label(baseline)}** mean = {_fmt(baseline.get('mean_score', 0.0))}")
        lines.append("")
        lines.append("| model | mean | lift vs baseline |")
        lines.append("|---|---|---|")
        bmean = baseline.get("mean_score", 0.0)
        for res in others:
            lines.append(f"| {_label(res)} | {_fmt(res.get('mean_score', 0.0))} | "
                         f"{_delta(res.get('mean_score', 0.0), bmean)} |")
        lines.append("")

    # 3. per-module table
    all_modules = []
    for res in results:
        for m in res.get("modules", []):
            if m["module"] not in all_modules:
                all_modules.append(m["module"])
    if all_modules:
        lines.append("## Per-module scores")
        lines.append("")
        header = "| module | " + " | ".join(_label(r) for r in results) + " |"
        sep = "|---|" + "---|" * len(results)
        lines.append(header)
        lines.append(sep)
        score_maps = [_module_scores(r) for r in results]
        for mod in all_modules:
            cells = []
            for sm in score_maps:
                rec = sm.get(mod)
                if rec is None:
                    cells.append("-")
                elif rec.get("error"):
                    cells.append("err")
                else:
                    g = "" if rec.get("gate") else " (gate-fail)"
                    cells.append(f"{_fmt(rec['score'])}{g}")
            lines.append(f"| {mod} | " + " | ".join(cells) + " |")
        lines.append("")

    # 4. regressions vs baseline
    if baseline:
        bmap = _module_scores(baseline)
        lines.append("## Regressions vs baseline")
        lines.append("")
        any_reg = False
        for res in others:
            smap = _module_scores(res)
            regs = []
            for mod, rec in smap.items():
                if rec.get("error") or mod not in bmap or bmap[mod].get("error"):
                    continue
                if rec["score"] < bmap[mod]["score"] - REGRESSION_EPS:
                    regs.append(f"{mod} ({_fmt(bmap[mod]['score'])} -> {_fmt(rec['score'])})")
            if regs:
                any_reg = True
                lines.append(f"- **{_label(res)}**: " + "; ".join(regs))
        if not any_reg:
            lines.append("None: no module scored below baseline.")
        lines.append("")

    # 5. enforced caveats
    lines.append("## Caveats")
    lines.append("")
    caveats = [
        "A best-of-1 sample with gate failures is not a stable capability number. Treat any "
        "single-pass result as indicative, not as the model's capability, without repeated "
        "seeds and confidence intervals.",
        "Gate-failed modules score 0.0 (the suite failed the reference or a behaviour-equivalent "
        "refactor), so they pull the mean down by design; they are not measurement noise.",
    ]
    for res in results:
        if res.get("runs", 1) <= 1:
            caveats.append(f"`{_label(res)}` is a single run (runs=1): no variance or CI is available; "
                           f"re-run with `--runs >= 3` before quoting it.")
        if res.get("best_of_n", 1) > 1:
            caveats.append(f"`{_label(res)}` used best-of-{res.get('best_of_n')}: best-of-N inflates the "
                           f"score relative to single-sample capability.")
        if res.get("status") != "ok":
            caveats.append(f"`{_label(res)}` status is `{res.get('status')}` "
                           f"({res.get('error', 'see result file')}): numbers may be partial.")
    for c in caveats:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--baseline", default=None, help="baseline result JSON (eval_schema)")
    p.add_argument("--inputs", nargs="+", required=True, help="one or more result JSON files")
    p.add_argument("--out", default="rft_report.md", help="output Markdown path")
    args = p.parse_args()

    baseline = eval_schema.load(args.baseline) if args.baseline else None
    others = [eval_schema.load(p) for p in args.inputs]
    if baseline is None and others:
        baseline, others = others[0], others[1:]  # first input is the baseline column

    report = build_report(baseline, others)
    with open(args.out, "w") as f:
        f.write(report)
    print(f"wrote {args.out} ({len(report.splitlines())} lines, "
          f"{1 + len(others) if baseline else len(others)} result(s) compared)")


if __name__ == "__main__":
    main()
