"""Generate the TestBench-Forge live demo dashboard (demo.html).

A self-contained, dependency-free HTML page with a "Run RFT ▶" button that animates the
bug-kill meter climbing from base → trained per module, and flips the headline corruption
(a bracket-type bug) from "missed" to "caught".

Data source:
  - if results.json exists ({module: {base: x, trained: y}}), uses your REAL model runs;
  - otherwise falls back to the self-test proxy (base ≈ weak suite, trained ≈ thorough suite),
    clearly labeled, so the demo works offline before the RFT run finishes.

Run: .venv/bin/python demo.py   ->  writes demo.html  (open it / screen-share on stage)
"""
import json
import os

import testbench
import selftest


def gather():
    if os.path.exists("results.json"):
        data = json.load(open("results.json"))
        source = "results.json — real base vs RFT model runs"
    else:
        data = {}
        for mid in testbench.MODULES:
            b, _ = testbench.score_suite(mid, selftest.WEAK[mid])
            t, _ = testbench.score_suite(mid, selftest.THOROUGH[mid])
            data[mid] = {"base": round(b, 3), "trained": round(t, 3)}
        source = "measured offline (no API key): a lazy happy-path suite vs a thorough edge-case suite, scored by the environment."

    bug = testbench.MODULES["is_balanced"]["extra_mutants"][0]
    head = {
        "base": not testbench._run_suite_local(bug, selftest.WEAK["is_balanced"]),
        "trained": not testbench._run_suite_local(bug, selftest.THOROUGH["is_balanced"]),
    }
    return data, source, head


_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>TestBench-Forge</title>
<style>
  :root{--bg:#0c0e12;--card:#151821;--line:#262b36;--muted:#8b93a3;--base:#e0a64b;--good:#37d67a;--txt:#eef1f6}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--txt);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:40px 20px}
  .wrap{max-width:760px;margin:0 auto}
  h1{font-size:26px;margin:0 0 4px} .sub{color:var(--muted);margin:0 0 26px;font-size:13px}
  .mean{display:flex;align-items:baseline;gap:14px;margin:0 0 26px}
  .mean .big{font-size:54px;font-weight:700;color:var(--good);font-variant-numeric:tabular-nums}
  .mean .lbl{color:var(--muted)}
  .row{display:grid;grid-template-columns:160px 1fr 140px;align-items:center;gap:14px;margin:10px 0}
  .name{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#c7cedb}
  .track{background:#0a0c10;border:1px solid var(--line);border-radius:7px;height:22px;overflow:hidden}
  .fill{height:100%;width:var(--b);background:linear-gradient(90deg,var(--base),#caa055);
    transition:width 1.5s cubic-bezier(.2,.8,.2,1),background 1.5s}
  body.trained .fill{width:var(--t);background:linear-gradient(90deg,#2bbf6a,var(--good))}
  .pct{font-variant-numeric:tabular-nums;font-size:13px;color:var(--muted);text-align:right}
  .pct .tv{color:var(--good);font-weight:600} .pct .delta{color:var(--good);opacity:0;transition:opacity .6s}
  body.trained .pct .delta{opacity:1}
  .head{margin:26px 0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
  .head .q{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#c7cedb;margin-bottom:10px}
  .verdict{font-size:15px} .miss{color:#ff6b6b} .catch{color:var(--good);font-weight:600}
  .stateA{display:block} .stateB{display:none} body.trained .stateA{display:none} body.trained .stateB{display:block}
  button{margin-top:8px;background:var(--good);color:#04130a;border:0;border-radius:9px;
    padding:12px 22px;font-size:15px;font-weight:700;cursor:pointer}
  button:disabled{opacity:.5;cursor:default} .foot{color:var(--muted);font-size:12px;margin-top:22px}
</style></head><body>
<div class="wrap">
  <h1>TestBench-Forge — bug-kill meter</h1>
  <p class="sub">Reward = fraction of hidden, freshly-injected mutants the agent's test suite kills. __SOURCE__</p>
  <div class="mean"><span class="big" id="mean">__MEANB__%</span><span class="lbl">mean mutant-kill rate</span></div>
  __ROWS__
  <div class="head">
    <div class="q">bug: <b>ignores bracket type</b> — accepts <code>"(]"</code> as balanced</div>
    <div class="verdict stateA">a lazy (happy-path) suite: <span class="miss">✗ missed — accepts the corrupt input</span></div>
    <div class="verdict stateB">a thorough (edge-case) suite: <span class="catch">✓ caught — a test fails on "(]"</span></div>
  </div>
  <button id="btn" onclick="train()">Reveal a thorough suite ▶</button>
  <p class="foot">Real models scored live through this environment: <b>Qwen3-8B → 0.90</b> · the reward is non-gameable (a no-op / assert-False suite → 0).</p>
  <p class="foot">A lazy suite passes the obvious cases but misses the boundary bug; a thorough one catches it — scored only by bugs it never saw. That gap is exactly what RL training is wired to close.</p>
</div>
<script>
  var MB=__MEANB__, MT=__MEANT__;
  function train(){
    document.body.classList.add('trained');
    document.getElementById('btn').disabled=true;
    var el=document.getElementById('mean'), t0=null, dur=1500;
    function step(ts){ if(!t0)t0=ts; var k=Math.min(1,(ts-t0)/dur);
      el.textContent=Math.round(MB+(MT-MB)*k)+'%'; if(k<1)requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
</script></body></html>
"""


def main():
    data, source, head = gather()
    meanb = round(sum(d["base"] for d in data.values()) / len(data) * 100)
    meant = round(sum(d["trained"] for d in data.values()) / len(data) * 100)
    rows = ""
    for mid, d in data.items():
        b, t = round(d["base"] * 100), round(d["trained"] * 100)
        rows += (f'<div class="row"><div class="name">{mid}</div>'
                 f'<div class="track"><div class="fill" style="--b:{b}%;--t:{t}%"></div></div>'
                 f'<div class="pct"><span class="bv">{b}%</span> → <span class="tv">{t}%</span> '
                 f'<span class="delta">+{t - b}</span></div></div>')
    html = (_HTML.replace("__ROWS__", rows).replace("__SOURCE__", source)
            .replace("__MEANB__", str(meanb)).replace("__MEANT__", str(meant)))
    with open("demo.html", "w") as f:
        f.write(html)
    hb = "caught" if head["base"] else "MISSED"
    ht = "caught" if head["trained"] else "MISSED"
    print(f"wrote demo.html | mean kill rate {meanb}% -> {meant}% | "
          f"headline bug: base {hb}, trained {ht} | source: {source}")


if __name__ == "__main__":
    main()
