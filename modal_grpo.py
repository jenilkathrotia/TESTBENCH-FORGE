"""Self-contained GRPO training of a small open model on TestBench-Forge — on a Modal GPU.

No HUD/tinker dependency: this owns the GPU (your $250 Modal credits). TRL's GRPOTrainer
samples completions, our reward (hidden-mutant kill rate) scores them, GRPO updates a LoRA
adapter. The reward runs in-container (our testbench/families code + a subprocess sandbox).

Auth first (your terminal):  source .venv/bin/activate && python -m modal setup
Smoke (cheap, validates end-to-end):  modal run modal_grpo.py --smoke
Full run:                              modal run modal_grpo.py
Results land in ./modal_grpo_result.json (curve + before/after reward).
"""
import modal

MODEL = "Qwen/Qwen2.5-3B-Instruct"   # small, non-reasoning (clean output), trains fast, real headroom
GPU = "A100-80GB"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1",
        "transformers>=4.48,<4.52",
        "trl>=0.14,<0.16",
        "peft>=0.13",
        "accelerate>=1.0",
        "datasets>=3.0",
        "numpy<2.3",
    )
    .add_local_python_source("testbench", "families")   # our reward code (pure stdlib + subprocess)
)

app = modal.App("testbench-grpo", image=image)


@app.function(gpu=GPU, timeout=60 * 60 * 6)
def train(smoke: bool = False):
    import random
    import torch  # noqa: F401
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer
    from peft import LoraConfig

    import testbench
    import families

    modules = list(testbench.MODULES)
    if smoke:
        modules = modules[:3]
    reps = 2 if smoke else 10
    rows = []
    for _ in range(reps):
        for m in modules:
            rows.append({
                "prompt": [{"role": "user", "content": testbench.build_testbench_prompt(m)}],
                "module_id": m,
            })
    random.Random(0).shuffle(rows)
    ds = Dataset.from_list(rows)

    def tb_reward(completions, module_id, **kwargs):
        scores = []
        for comp, mid in zip(completions, module_id):
            text = comp[-1]["content"] if isinstance(comp, list) else str(comp)
            suite = families.extract_code(text or "")
            try:
                rate, _ = testbench.score_suite(mid, suite)
            except Exception:
                rate = 0.0
            scores.append(float(rate))
        return scores

    num_gen = 4 if smoke else 8
    cfg = GRPOConfig(
        output_dir="/tmp/grpo",
        num_generations=num_gen,
        per_device_train_batch_size=num_gen,
        gradient_accumulation_steps=1,
        max_prompt_length=1024,
        max_completion_length=512 if smoke else 768,
        temperature=1.0,
        learning_rate=1e-5,
        max_steps=4 if smoke else 80,
        logging_steps=1,
        bf16=True,
        save_strategy="no",
        report_to=[],
        use_vllm=False,
    )
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0,
                      target_modules="all-linear", task_type="CAUSAL_LM")

    trainer = GRPOTrainer(model=MODEL, reward_funcs=[tb_reward], args=cfg,
                          train_dataset=ds, peft_config=lora)
    trainer.train()

    hist = trainer.state.log_history
    curve = [{"step": h.get("step"), "reward": h.get("reward")} for h in hist if "reward" in h]
    return {
        "model": MODEL, "gpu": GPU, "smoke": smoke, "modules": modules,
        "num_generations": num_gen, "max_steps": cfg.max_steps,
        "curve": curve,
        "first_reward": (curve[0]["reward"] if curve else None),
        "last_reward": (curve[-1]["reward"] if curve else None),
        "best_reward": (max((c["reward"] for c in curve), default=None)),
    }


@app.local_entrypoint()
def main(smoke: bool = False):
    import json
    res = train.remote(smoke=smoke)
    with open("modal_grpo_result.json", "w") as f:
        json.dump(res, f, indent=2)
    fr, lr = res.get("first_reward"), res.get("last_reward")
    print(f"\n=== GRPO done ({'SMOKE' if smoke else 'FULL'}) ===")
    print(f"model={res['model']} steps={res['max_steps']} num_gen={res['num_generations']}")
    print(f"reward: first={fr} -> last={lr} (best={res.get('best_reward')})")
    print("curve:", [round(c["reward"], 3) for c in res["curve"]])
    print("wrote modal_grpo_result.json")
