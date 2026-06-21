# TestBench-Forge: Hackathon Cheat Sheet

**Golden rule:** your API keys are passwords. Never screen-share, screenshot, or post them.

The project lives at `~/Downloads/YC---RL-Gym`. Open Terminal and run this once each session:
```bash
cd ~/Downloads/YC---RL-Gym
source .venv/bin/activate
```

---

## The plan (do it in THIS order)

### 0: Lock in a guaranteed win first (5 min, no keys)
```bash
python selftest.py      # should end with: weak 0.451 vs thorough 1.000
python stage_a_checks.py
python eval_bench.py --out eval_results.json
python demo.py
open demo.html          # click "Reveal a thorough suite", bars climb to 100%
```
Now you have a working, presentable project no matter what happens next.

### 1: Get your keys early (training is slow)
- **HUD table**: say: *"Hi, I'm building an RL environment on HUD. Can I get my API key?"*
  ```bash
  hud login
  ```
- **Fireworks table**: say: *"Hi, can I get my $500 credits and API key? And later, can someone help me start an RFT job that uses a reward function I deploy with reward-kit?"*
  ```bash
  export FIREWORKS_API_KEY=fw-PASTE_YOURS_HERE
  ```

### 2: Get your "before" number
```bash
pip install fireworks-ai reward-kit
python fireworks_baseline.py     # write down the "mean baseline kill_rate"
```

### 3: Deploy the reward + start training early
```bash
python build_dataset.py
reward-kit preview --metrics-folders "kill=." --samples dataset.jsonl
reward-kit deploy  --id testbench-forge --metrics-folders "kill=." --force
```
Then **go to the Fireworks booth** and say:
> *"I deployed a reward function with reward-kit. How do I start an RFT job using it, with my `dataset.jsonl` and base model **Qwen2.5-32B**?"*

Let it train in the background. This is the long pole, the earlier you start, the better.

### 4: While it trains
- Rehearse the demo + the one-line pitch (below).
- Optional, with HUD key: `hud eval tasks.py claude`
- Optional booth check: *"Does my `daytona_runner.py` / `modal_runner.py` use your current SDK?"*

### 5: After training finishes
- Get a real trained-model eval number only after Fireworks or HUD returns a trained endpoint.
- Make `results.json` (ask Claude, or copy this and fill in your two numbers):
  ```json
  { "binary_search": {"base": 0.44, "trained": 0.95} }
  ```
- Rebuild the demo with real numbers:
  ```bash
  python demo.py
  open demo.html
  ```

### 6: Present
Open `demo.html`, click **"Reveal a thorough suite"**, and say:
> *"TestBench-Forge scores tests by hidden bugs killed, with a refactor gate that rejects brittle over-specification. The local environment sits in the target band, and our real Modal GRPO reward curve moved from 0.233 to 0.750 over 80 steps."*

---

## If something breaks
- Read the terminal message : it usually says what's wrong.
- Paste the red error text to Claude and ask for a fix.
- **Fallback:** Step 0 (the `demo.html` with weak-to-thorough) always works and still proves the idea. You can present that alone.

## What each sponsor does (for the judges' questions)
- **HUD**: hosts the environment. **Fireworks**: does the training (RFT). **Modal**: GPUs / parallel runs. **Daytona**: optional sandbox for running untrusted code. **Anthropic**: Claude as the comparison baseline.
