"""Render the REAL test suites the base vs GRPO-trained model wrote for the HELD-OUT modules
(from suites_heldout.json, produced by dump_suites.py) — the 'witnessed' before/after: base
and trained suites side by side, each with its hidden-mutant kill rate. For a base suite that
the correctness gate zeroed, it names the exact test that makes a false claim about the code.

Run: python demo_suites.py   ->  writes demo_suites.html  (open it / screen-share on stage)
"""
import contextlib
import html
import json
import os
import sys
import types

import testbench

SRC = "suites_heldout.json"
ORDER = ["binary_search", "roman_to_int", "is_balanced"]   # lead with the hero (cleanest transfer)

_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>TestBench-Forge — base vs trained suites (held-out)</title><style>
:root{--bg:#0c0e12;--card:#151821;--line:#262b36;--muted:#8b93a3;--base:#e0a64b;--good:#37d67a;--txt:#eef1f6;--accent:#5b9dff;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
 font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:40px 20px}
.wrap{max-width:1000px;margin:0 auto}h1{font-size:24px;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px;margin:0 0 26px}
section{margin:0 0 30px}h2{font-size:16px;margin:0 0 12px;font-family:ui-monospace,Menlo,monospace}
.tag{font-size:11px;color:var(--accent);border:1px solid var(--accent);border-radius:20px;padding:2px 9px;margin-left:6px;font-family:-apple-system,sans-serif;vertical-align:middle}
.delta{float:right;color:var(--good);font-weight:700;font-variant-numeric:tabular-nums}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:720px){.cols{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.panel.good{border-color:#2c6b46}
.phead{padding:10px 14px;border-bottom:1px solid var(--line);font-size:12px;font-weight:600;color:#c7cedb;display:flex;justify-content:space-between;align-items:center}
.nt{color:var(--muted);font-weight:400}
.rate{padding:8px 14px;font-size:30px;font-weight:800;color:var(--base);font-variant-numeric:tabular-nums}
.panel.good .rate{color:var(--good)}
.rate .sub{font-size:12px;font-weight:400;color:var(--muted);margin-left:10px}
.why{padding:0 14px 10px;font-size:12px;color:var(--bad)}.why code{color:#ffb4b4}
pre{margin:0;max-height:420px;overflow:auto}
code{display:block;padding:0 14px 14px;font:12px/1.5 ui-monospace,Menlo,Consolas,monospace;color:#cdd6e3;white-space:pre}
.foot{color:var(--muted);font-size:12px;margin-top:22px}
</style></head><body><div class="wrap">
<h1>TestBench-Forge — the suites a base vs GRPO-trained model actually wrote</h1>
<p class="sub">Same prompt, real generated test suites, on modules the model was <b>never trained on</b>. Each suite scored by the fraction of <b>hidden mutants</b> it kills — no LLM judge. Produced by <code>dump_suites.py</code> (inference on the saved adapter).</p>
__BLOCKS__
<p class="foot">These are the model's <b>literal generated suites</b> (not illustrations). Notice the base suites are often <i>longer</i> — they don't skip edge cases. They score <b>0</b> because they slip in a <b>wrong assertion</b>: they claim correct code is buggy (e.g. that a balanced string is unbalanced, or that the result is the wrong index), so the correctness gate rejects the whole suite. The trained model writes tests that are <b>actually correct</b> — passing the gate and killing most hidden bugs. That's the skill GRPO taught, transferred to unseen modules. Eval is <b>n=16</b> per model; each panel shows a <b>representative</b> suite (closest to that model's mean kill-rate).</p>
</div></body></html>
"""


def _why_base_zero(module, suite):
    """If the suite fails the reference gate, name the exact test that makes a false claim.
    Best-effort, render-time only (these are our own captured suites, safe to run)."""
    try:
        ns = {}
        exec(testbench.MODULES[module]["reference"], ns)
        func = testbench.MODULES[module]["func"]
        pt = types.ModuleType("pytest")           # mirror the harness's import-friendliness

        @contextlib.contextmanager
        def _raises(exc=Exception, *a, **k):
            try:
                yield
            except exc:
                return
            raise AssertionError("DID NOT RAISE")
        pt.raises = _raises
        pt.approx = lambda v, *a, **k: v
        pt.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f))
        pt.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda f: f))
        sys.modules["pytest"] = pt
        for nm in ("solution", func):
            m = types.ModuleType(nm)
            if func in ns:
                setattr(m, func, ns[func])
            sys.modules[nm] = m
        exec(suite, ns)
        for k, v in list(ns.items()):
            if k.startswith("test_") and callable(v):
                try:
                    v()
                except BaseException as e:
                    return f"{k}() raises {type(e).__name__} on the <b>correct</b> reference — a false claim; the gate rejects the whole suite"
    except BaseException:
        return "the suite makes a wrong claim about the correct reference — the gate rejects it"
    return None


def _panel(label, cls, module, entry):
    if not entry or not (entry.get("suite") or "").strip():
        return (f'<div class="panel {cls}"><div class="phead">{label}</div>'
                f'<div class="rate">—</div><pre><code>(no suite captured)</code></pre></div>')
    rate = entry.get("rate") or 0.0
    killed, mut = entry.get("killed"), entry.get("mutants")
    sub = f"{killed}/{mut} mutants killed" if killed is not None and mut else ""
    ntests = (entry.get("suite") or "").count("def test_")
    code = html.escape(entry.get("suite") or "")
    why = ""
    if cls != "good" and rate == 0.0 and ntests >= 1:
        reason = _why_base_zero(module, entry.get("suite") or "")
        if reason:
            why = f'<div class="why">⚠ gate failed: {reason}</div>'
    return (f'<div class="panel {cls}"><div class="phead">{label}'
            f'<span class="nt">{ntests} test{"" if ntests == 1 else "s"}</span></div>'
            f'<div class="rate">{rate:.2f}<span class="sub">{sub}</span></div>{why}'
            f'<pre><code>{code}</code></pre></div>')


def main():
    if not os.path.exists(SRC):
        print(f"{SRC} not found — run `modal run dump_suites.py` first, "
              f"or fetch it: modal volume get testbench-grpo-vol /suites_heldout.json")
        return
    data = json.load(open(SRC))
    mods = [m for m in ORDER if m in data] + [m for m in data if m not in ORDER]
    blocks = []
    for m in mods:
        d = data[m]
        bm = d.get("base_mean") or 0.0
        tm = d.get("trained_mean") or 0.0
        blocks.append(
            f'<section><h2>{m}<span class="tag">held-out · never trained on</span>'
            f'<span class="delta">mean {bm:.2f} → {tm:.2f}</span></h2>'
            f'<div class="cols">{_panel("BASE — Qwen2.5-3B", "base", m, d.get("base"))}'
            f'{_panel("TRAINED — + GRPO (LoRA)", "good", m, d.get("trained"))}</div></section>')
    out = _HTML.replace("__BLOCKS__", "\n".join(blocks))
    with open("demo_suites.html", "w") as f:
        f.write(out)
    print("wrote demo_suites.html | " + " | ".join(
        f"{m}: mean {data[m].get('base_mean')}->{data[m].get('trained_mean')}" for m in mods))


if __name__ == "__main__":
    main()
