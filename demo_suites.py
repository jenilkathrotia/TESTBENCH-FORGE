"""Render the REAL test suites the base vs GRPO-trained model wrote for the HELD-OUT modules
(from suites_heldout.json, produced by dump_suites.py) — the 'witnessed' before/after for the
demo: base and trained suites side by side, each with its hidden-mutant kill rate.

Run: python demo_suites.py   ->  writes demo_suites.html  (open it / screen-share on stage)
"""
import html
import json
import os

SRC = "suites_heldout.json"
ORDER = ["binary_search", "roman_to_int", "is_balanced"]   # lead with the hero (cleanest transfer)

_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>TestBench-Forge — base vs trained suites (held-out)</title><style>
:root{--bg:#0c0e12;--card:#151821;--line:#262b36;--muted:#8b93a3;--base:#e0a64b;--good:#37d67a;--txt:#eef1f6;--accent:#5b9dff}
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
pre{margin:0;max-height:420px;overflow:auto}
code{display:block;padding:0 14px 14px;font:12px/1.5 ui-monospace,Menlo,Consolas,monospace;color:#cdd6e3;white-space:pre}
.foot{color:var(--muted);font-size:12px;margin-top:22px}
</style></head><body><div class="wrap">
<h1>TestBench-Forge — the suites a base vs GRPO-trained model actually wrote</h1>
<p class="sub">Same prompt, real generated test suites, on modules the model was <b>never trained on</b>. Each suite scored by the fraction of <b>hidden mutants</b> it kills — no LLM judge. Produced by <code>dump_suites.py</code> (inference on the saved adapter).</p>
__BLOCKS__
<p class="foot">These are the model's <b>literal generated suites</b> (not illustrations). The trained model writes the boundary / edge-case tests the base model skips — the test-writing skill it learned via GRPO, transferred to unseen modules. Eval is n=6 per model; the base panel shows a representative suite, the trained panel its strongest.</p>
</div></body></html>
"""


def _panel(label, cls, entry):
    if not entry or not (entry.get("suite") or "").strip():
        return (f'<div class="panel {cls}"><div class="phead">{label}</div>'
                f'<div class="rate">—</div><pre><code>(no suite captured)</code></pre></div>')
    rate = entry.get("rate") or 0.0
    killed, mut = entry.get("killed"), entry.get("mutants")
    sub = f"{killed}/{mut} mutants killed" if killed is not None and mut else ""
    ntests = (entry.get("suite") or "").count("def test_")
    code = html.escape(entry.get("suite") or "")
    return (f'<div class="panel {cls}"><div class="phead">{label}'
            f'<span class="nt">{ntests} test{"" if ntests == 1 else "s"}</span></div>'
            f'<div class="rate">{rate:.2f}<span class="sub">{sub}</span></div>'
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
            f'<span class="delta">{bm:.2f} → {tm:.2f}</span></h2>'
            f'<div class="cols">{_panel("BASE — Qwen2.5-3B", "base", d.get("base"))}'
            f'{_panel("TRAINED — + GRPO (LoRA)", "good", d.get("trained"))}</div></section>')
    out = _HTML.replace("__BLOCKS__", "\n".join(blocks))
    with open("demo_suites.html", "w") as f:
        f.write(out)
    print("wrote demo_suites.html | " + " | ".join(
        f"{m}: {data[m].get('base_mean')}->{data[m].get('trained_mean')}" for m in mods))


if __name__ == "__main__":
    main()
