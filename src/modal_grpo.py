"""Self-contained GRPO training of a small open model on TestBench-Forge — on a Modal GPU.

No HUD/tinker dependency: this owns the GPU (your $250 Modal credits). TRL's GRPOTrainer
samples completions, our reward (hidden-mutant kill rate) scores them, GRPO updates a LoRA
adapter. The reward runs in-container (our testbench/families code + a subprocess sandbox).

This version proves GENERALIZATION: it trains on 7 modules and evaluates the lift on 3
HELD-OUT modules the model never trained on — and saves the trained adapter to a Modal Volume.

Auth once (your terminal):  source .venv/bin/activate && python -m modal setup
Smoke:  modal run modal_grpo.py --smoke
Full:   modal run modal_grpo.py
Results -> ./modal_grpo_result.json (per-module before->after, incl. held-out generalization).
"""
import modal

MODEL = "Qwen/Qwen2.5-3B-Instruct"
GPU = "A100-80GB"
HELD_OUT = ["roman_to_int", "binary_search", "is_balanced"]   # never trained on -> tests generalization

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1", "transformers>=4.48,<4.52", "trl>=0.14,<0.16",
        "peft>=0.13", "accelerate>=1.0", "datasets>=3.0", "numpy<2.3",
    )
    .add_local_python_source("testbench", "families")
)

app = modal.App("testbench-grpo", image=image)
vol = modal.Volume.from_name("testbench-grpo-vol", create_if_missing=True)


@app.function(gpu=GPU, volumes={"/vol": vol}, timeout=60 * 60 * 6)
def train(smoke: bool = False, steps: int = 80):
    import os
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    import random
    import torch
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer

    import testbench
    import families

    all_mods = list(testbench.MODULES)
    held = [m for m in all_mods if m in HELD_OUT]
    train_mods = [m for m in all_mods if m not in HELD_OUT]
    if smoke:
        train_mods = train_mods[:2]
        held = held[:1]
        all_mods = train_mods + held

    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def eval_modules(mdl, modules, n=5):
        mdl.eval()
        out = {}
        for m in modules:
            msgs = [{"role": "user", "content": testbench.build_testbench_prompt(m)}]
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inp = tok([text] * n, return_tensors="pt").to(mdl.device)
            with torch.no_grad():
                g = mdl.generate(**inp, max_new_tokens=512, do_sample=True,
                                 temperature=0.7, top_p=0.95, pad_token_id=tok.pad_token_id)
            scores = []
            plen = inp["input_ids"].shape[1]
            for j in range(n):
                comp = tok.decode(g[j][plen:], skip_special_tokens=True)
                try:
                    r, _ = testbench.score_suite(m, families.extract_code(comp))
                except Exception:
                    r = 0.0
                scores.append(float(r))
            out[m] = round(sum(scores) / len(scores), 3)
        return out

    # BEFORE: baseline per-module on a fresh copy, then free it
    base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to("cuda")
    before = eval_modules(base, all_mods)
    del base
    torch.cuda.empty_cache()

    # dataset: TRAIN modules only (held-out never appears)
    reps = 2 if smoke else 12
    rows = []
    for _ in range(reps):
        for m in train_mods:
            rows.append({"prompt": [{"role": "user", "content": testbench.build_testbench_prompt(m)}],
                         "module_id": m})
    random.Random(0).shuffle(rows)
    ds = Dataset.from_list(rows)

    def tb_reward(completions, module_id, **kwargs):
        out = []
        for comp, mid in zip(completions, module_id):
            text = comp[-1]["content"] if isinstance(comp, list) else str(comp)
            try:
                r, _ = testbench.score_suite(mid, families.extract_code(text or ""))
            except Exception:
                r = 0.0
            out.append(float(r))
        return out

    num_gen = 4 if smoke else 6
    cfg = GRPOConfig(
        output_dir="/tmp/grpo", num_generations=num_gen, per_device_train_batch_size=num_gen,
        gradient_accumulation_steps=1, max_prompt_length=1024, max_completion_length=512,
        temperature=1.0, learning_rate=1e-5, max_steps=4 if smoke else steps, logging_steps=1,
        bf16=True, gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
        save_strategy="no", report_to=[], use_vllm=False,
    )
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0,
                      target_modules="all-linear", task_type="CAUSAL_LM")
    trainer = GRPOTrainer(model=MODEL, reward_funcs=[tb_reward], args=cfg,
                          train_dataset=ds, peft_config=lora)
    trainer.train()

    # AFTER: same eval on the trained model
    after = eval_modules(trainer.model, all_mods)

    # persist the trained adapter
    trainer.save_model("/vol/testbench-q3-adapter")
    vol.commit()

    hist = trainer.state.log_history
    curve = [{"step": h.get("step"), "reward": h.get("reward")} for h in hist if "reward" in h]
    result = {
        "model": MODEL, "train_modules": train_mods, "held_out": held,
        "before": before, "after": after, "curve": curve,
        "adapter": "/vol/testbench-q3-adapter (Modal volume 'testbench-grpo-vol')",
    }
    import json as _json
    with open("/vol/result.json", "w") as _f:        # persist remotely so a local disconnect can't lose it
        _json.dump(result, _f, indent=2)
    vol.commit()
    return result


@app.local_entrypoint()
def main(smoke: bool = False, steps: int = 80):
    import json
    res = train.remote(smoke=smoke, steps=steps)
    with open("modal_grpo_result.json", "w") as f:
        json.dump(res, f, indent=2)
    b, a, held = res["before"], res["after"], res["held_out"]
    tr = res["train_modules"]
    mean = lambda d, ks: (round(sum(d[k] for k in ks) / len(ks), 3) if ks else 0.0)
    print("\n=== per-module  before -> after ===")
    for m in b:
        print(f"  {m:18s} {b[m]:.3f} -> {a[m]:.3f}{'   [HELD-OUT]' if m in held else ''}")
    print(f"\nTRAIN modules:      {mean(b, tr)} -> {mean(a, tr)}")
    print(f"HELD-OUT (unseen):  {mean(b, held)} -> {mean(a, held)}   <-- generalization")
    print("adapter saved:", res["adapter"])
    print("wrote modal_grpo_result.json")
