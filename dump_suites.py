"""Inference-only: capture the ACTUAL test suites the base vs GRPO-trained model write for
the HELD-OUT modules, so the demo shows the real before/after suite TEXT — not a hand-written
illustration. This is NOT a retrain: it loads the saved LoRA adapter from the Modal volume.

Run:    modal run dump_suites.py
Writes: ./suites_heldout.json  AND  /vol/suites_heldout.json (so a local-write failure can't lose it)
"""
import modal

MODEL = "Qwen/Qwen2.5-3B-Instruct"
GPU = "A100-80GB"
ADAPTER = "/vol/testbench-q3-adapter"          # saved by modal_grpo.py
HELD_OUT = ["binary_search", "roman_to_int", "is_balanced"]   # never trained on
N = 16

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.5.1", "transformers>=4.48,<4.52", "peft>=0.13",
                 "accelerate>=1.0", "numpy<2.3")
    .add_local_python_source("testbench", "families")
)
app = modal.App("testbench-dump-suites", image=image)
vol = modal.Volume.from_name("testbench-grpo-vol")


@app.function(gpu=GPU, volumes={"/vol": vol}, timeout=60 * 30)
def dump(n: int = N, modules=None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import testbench
    import families

    mods = modules or HELD_OUT
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def gen_scored(mdl, module):
        mdl.eval()
        msgs = [{"role": "user", "content": testbench.build_testbench_prompt(module)}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inp = tok([text] * n, return_tensors="pt").to(mdl.device)
        with torch.no_grad():
            g = mdl.generate(**inp, max_new_tokens=512, do_sample=True,
                             temperature=0.7, top_p=0.95, pad_token_id=tok.pad_token_id)
        plen = inp["input_ids"].shape[1]
        out = []
        for j in range(n):
            comp = tok.decode(g[j][plen:], skip_special_tokens=True)
            suite = families.extract_code(comp or "")
            try:
                r, info = testbench.score_suite(module, suite)
            except Exception:
                r, info = 0.0, {}
            out.append({"suite": suite, "rate": round(float(r), 3),
                        "killed": info.get("killed"), "mutants": info.get("mutants")})
        return out

    # BASE model suites first (before wrapping with the adapter)
    base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to("cuda")
    base_out = {m: gen_scored(base, m) for m in mods}

    # TRAINED = the same base with the saved LoRA adapter loaded (inference only, no training)
    from peft import PeftModel
    trained = PeftModel.from_pretrained(base, ADAPTER)
    trained_out = {m: gen_scored(trained, m) for m in mods}

    def pick(samples, mode):
        samples = [s for s in samples if s["suite"].strip()]
        if not samples:
            return None
        if mode == "best":                       # trained: show its strongest suite
            return max(samples, key=lambda s: s["rate"])
        mean = sum(s["rate"] for s in samples) / len(samples)   # base: show a representative one
        return min(samples, key=lambda s: abs(s["rate"] - mean))

    result = {}
    for m in mods:
        result[m] = {
            "base": pick(base_out[m], "representative"),
            "trained": pick(trained_out[m], "representative"),   # honest: representative, not cherry-picked best
            "base_mean": round(sum(s["rate"] for s in base_out[m]) / len(base_out[m]), 3),
            "trained_mean": round(sum(s["rate"] for s in trained_out[m]) / len(trained_out[m]), 3),
            "all_base": base_out[m],
            "all_trained": trained_out[m],
        }
    import json as _json
    with open("/vol/suites_heldout.json", "w") as f:
        _json.dump(result, f, indent=2)
    vol.commit()
    return result


@app.local_entrypoint()
def main(n: int = N):
    import json
    res = dump.remote(n=n)
    try:
        with open("suites_heldout.json", "w") as f:
            json.dump(res, f, indent=2)
        print("wrote suites_heldout.json")
    except Exception as e:
        print("local write failed (%s) — fetch with: modal volume get testbench-grpo-vol /suites_heldout.json" % e)
    for m, d in res.items():
        b, t = d.get("base") or {}, d.get("trained") or {}
        print(f"  {m:16s} base {d.get('base_mean')} (shown {b.get('rate')}) -> trained {d.get('trained_mean')} (shown {t.get('rate')})")
