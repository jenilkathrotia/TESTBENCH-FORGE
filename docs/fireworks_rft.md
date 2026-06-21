# Fireworks RFT: exact smoke-run procedure

End-to-end recipe to run a small Fireworks RFT (GRPO) job against the TestBench-Forge
evaluator, then compare base vs trained with a sanitized report. Every command was
checked against the installed toolchain (eval-protocol from `.venv`, firectl on PATH).

Model choice (verified against the live account, 2026-06-21):
- Smoke / pipeline validation: `accounts/fireworks/models/qwen3-0p6b` (tiny; confirmed
  trainable here, RFT is **free for models under 16B**).
- Bigger / more-believable lift: a larger supported base such as `qwen3-4b` (still <16B,
  free) or a >16B model from the supported list (billed per GPU-hour). NOTE:
  `llama-v3p1-8b-instruct` is NOT in the managed-RFT base list and 404s here; pick a
  model from the Managed Fine-Tuning supported-base table.
- A 0.6B model may be too small to show a large lift, so do not headline a qwen3-0p6b
  number as a capability claim.

Spending: RFT training is free under 16B params. The credits ($500 here) are spent per
GPU-second (H100 ~$7/hr) only on (a) >16B RFT and (b) on-demand deployments used for
inference. Mainstream models are NOT on this account's serverless pool (they 404), so any
direct inference needs a short-lived on-demand deployment (see step 9).

Never print `FIREWORKS_API_KEY`. Load it into the environment from `.env`; do not echo it.

## 0. Load credentials (never echo the value)

```bash
set -a; . ./.env; set +a            # exports FIREWORKS_API_KEY without printing it
.venv/bin/python -c "import os; assert os.environ.get('FIREWORKS_API_KEY'); print('key loaded')"
```

## 1. Preflight (merged main must be healthy)

```bash
.venv/bin/python --version                                  # expect Python 3.12.x
.venv/bin/eval-protocol --help >/dev/null && echo "eval-protocol OK"
.venv/bin/python -c "import testbench, reward, testbench_eval_protocol; print('imports OK')"

.venv/bin/python selftest.py            # arc weak < thorough = 1.0; non-gameable suites -> 0
.venv/bin/python stage_a_checks.py      # runner-hardening acceptance (all OK)
.venv/bin/python security_checks.py     # adversarial anti-gaming proof (ALL NEUTRALIZED)
```

## 2. Eval Protocol fixture check (no tokens, no API)

```bash
.venv/bin/eval-protocol local-test \
  --entry testbench_eval_protocol.py::test_testbench_forge_fixture \
  --ignore-docker -y
```

## 3. Dataset rebuild (must be deterministic)

```bash
.venv/bin/python build_dataset.py
git diff --exit-code -- dataset.jsonl   # exit 0 = unchanged/deterministic; inspect any diff
```

## 4. Base-model access + baseline

Check access first, then capture a baseline with variance (write to /tmp, never commit raw):

```bash
# smoke one module against the intended base model
.venv/bin/python fireworks_baseline.py \
  --model accounts/fireworks/models/llama-v3p1-8b-instruct \
  --modules binary_search --runs 1 --out /tmp/fw_access_check.json

# full baseline with repeated runs (for variance / CI), best-of-N as desired
.venv/bin/python fireworks_baseline.py \
  --model accounts/fireworks/models/llama-v3p1-8b-instruct \
  --runs 3 --best-of-n 1 --provider fireworks --out /tmp/fireworks_base.json
```

If access is blocked, the result file records `status: "blocked"` with `blocked_on`; try the
fallback `accounts/fireworks/models/qwen3-0p6b`. Do not silently switch to a large model.

Note: RFT *tuning eligibility* is separate from inference access. A model can answer
`fireworks_baseline.py` yet be ineligible as an RFT base; the dry run (step 6) confirms
eligibility before any spend.

## 5. Register the evaluator and dataset on Fireworks

```bash
.venv/bin/eval-protocol upload \
  --entry testbench_eval_protocol.py::test_testbench_forge_rft --force -y
firectl dataset create testbench-forge-dataset dataset.jsonl
```

This creates the evaluator resource (`testbench-eval-protocol-test-testbench-forge-rft`)
and the dataset (`testbench-forge-dataset`) referenced below.

## 6. RFT dry run (no training compute)

```bash
.venv/bin/eval-protocol create rft --dry-run -y --skip-validation \
  --dataset testbench-forge-dataset \
  --evaluator testbench-eval-protocol-test-testbench-forge-rft \
  --training-config-base-model accounts/fireworks/models/qwen3-0p6b \
  --training-config-output-model accounts/<ACCOUNT_ID>/models/testbench-forge-rft-smoke \
  --training-config-epochs 1 \
  --inference-parameters-response-candidates-count 4 \
  --inference-parameters-temperature 0.8 \
  --inference-parameters-max-output-tokens 4096 \
  --max-concurrent-rollouts 4 \
  --max-concurrent-evaluations 4
```

Two gotchas, verified on the live CLI:
- `--training-config-output-model` MUST be a full path `accounts/<ACCOUNT_ID>/models/<name>`
  (a bare name returns a 400 "name must be in the format ..." error).
- Do NOT pass `--loss-config-method grpo`: this CLI build rejects the literal (`invalid
  Literal value: 'grpo'`) even though `--help` lists `{grpo,dapo,gspo-token}`. Omit it; the
  default is the GRPO-style RL loss (the platform's own demo job trains with
  `Method: METHOD_UNSPECIFIED`).

## 7. Smoke RFT launch (first real spend gate)

Same command without `--dry-run`. With a <16B base (e.g. qwen3-0p6b) RFT is free; a >16B
base bills per GPU-hour.

```bash
.venv/bin/eval-protocol create rft -y --skip-validation \
  --dataset testbench-forge-dataset \
  --evaluator testbench-eval-protocol-test-testbench-forge-rft \
  --training-config-base-model accounts/fireworks/models/qwen3-0p6b \
  --training-config-output-model accounts/<ACCOUNT_ID>/models/testbench-forge-rft-smoke \
  --training-config-epochs 1 \
  --inference-parameters-response-candidates-count 4 \
  --inference-parameters-temperature 0.8 \
  --inference-parameters-max-output-tokens 4096 \
  --max-concurrent-rollouts 4 \
  --max-concurrent-evaluations 4
```

Note: `create rft` auto-syncs secrets from `.env` into your Fireworks account secret store.
Our evaluator needs no secrets, so pass `--env-file /dev/null` (or an empty file) if you do
not want keys like `HUD_API_KEY` synced to the platform.

## 8. Monitor (capture sanitized metadata only)

```bash
firectl reinforcement-fine-tuning-job get <JOB_ID> 2>&1 | grep -E '^State:|Percent:'
```

The job's own `Output Metrics.curves.average.Score` is the per-chunk reward trajectory
(step-0 vs final = before/after on the TestBench reward), captured for free during
training. Record only: job ID, output model name, base model, start/end time, final
status, failure reason if any. Do not commit provider logs or raw transient JSON.

## 9. Evaluate trained vs base and report

Direct inference needs an on-demand deployment (serverless 404s here), billed per
GPU-second. Deploy, evaluate, then DELETE to stop billing:

```bash
# stand up a short-lived deployment of the trained model (~$7/hr H100, billed per second)
firectl deployment create accounts/charliegillet/models/testbench-forge-rft-smoke \
  --region GLOBAL --wait                         # prints accounts/<acct>/deployments/<id>

# benchmark via the DEPLOYMENT path (not the model catalog path)
.venv/bin/python fireworks_baseline.py \
  --model accounts/charliegillet/deployments/<DEPLOYMENT_ID> \
  --provider fireworks-rft --runs 3 --out /tmp/fireworks_rft.json

firectl deployment delete accounts/charliegillet/deployments/<DEPLOYMENT_ID>   # stop billing

# Markdown comparison (sanitized; this .md is the committed artifact)
.venv/bin/python rft_eval_report.py \
  --baseline /tmp/fireworks_base.json \
  --inputs /tmp/fireworks_rft.json \
  --out rft_report.md
```

If you only need the lift number (not a standalone eval), the RFT job's own reward curve
(step 8) already gives before/after for free, no deployment required.

## 10. Decision and handoff

- If the smoke run improves or gives useful signal, run a larger RFT. If it fails or
  regresses, stop and document the blocker instead of spending more.
- Commit only code, docs, and the sanitized `rft_report.md`. Raw `*_base.json` /
  `*_rft.json` / `fireworks_results.json` are git-ignored on purpose.
- Real RFT numbers ship in a separate PR, only after the job actually completes.
