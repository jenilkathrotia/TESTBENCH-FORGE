// data.ts — REAL data captured from /Users/charlie/events/YC---RL-Gym (branch: charlie-ui)
// Sources: grpo_result.json, suites_heldout.json, security_checks.py, selftest.py, README.md
// All numbers are literal, not illustrative. Model: Qwen/Qwen2.5-3B-Instruct (GRPO/LoRA r=16, Modal A100).

// --- 80-step GRPO reward curve (grpo_result.json -> curve[].reward), 0..1 ---
export const rewardCurve: number[] = [
  0.167, 0.000, 0.000, 0.000, 0.157, 0.167, 0.333, 0.500, 0.000, 0.000,
  0.167, 0.000, 0.167, 0.500, 0.000, 0.000, 0.667, 0.000, 0.167, 0.500,
  0.333, 0.333, 0.000, 0.667, 0.157, 0.306, 0.500, 0.500, 0.500, 0.500,
  0.167, 1.000, 0.333, 0.833, 0.833, 0.833, 0.667, 0.833, 0.333, 0.333,
  0.333, 0.167, 0.333, 0.833, 0.833, 0.324, 1.000, 0.833, 0.667, 0.833,
  0.833, 1.000, 0.333, 0.833, 1.000, 0.167, 1.000, 1.000, 0.500, 0.833,
  0.500, 1.000, 0.667, 1.000, 0.667, 1.000, 1.000, 0.833, 0.667, 0.833,
  0.833, 0.667, 0.667, 0.667, 0.833, 0.833, 1.000, 0.667, 1.000, 1.000,
];

// --- Held-out modules: 3 modules NEVER trained on (grpo_result.json before/after) ---
// before/after are per-module kill-rates from the saved adapter eval.
export const heldout: { module: string; before: number; after: number }[] = [
  { module: "binary_search", before: 0.389, after: 1.000 },
  { module: "is_balanced",   before: 0.750, after: 0.800 },
  { module: "roman_to_int",  before: 0.000, after: 0.511 },
];

// --- Train modules: 7 modules seen in training (grpo_result.json before/after) ---
export const train: { module: string; before: number; after: number }[] = [
  { module: "merge_intervals",   before: 0.200, after: 0.800 },
  { module: "two_sum",           before: 0.000, after: 0.600 },
  { module: "run_length_encode", before: 0.200, after: 1.000 },
  { module: "gcd",               before: 0.000, after: 1.000 },
  { module: "flatten",           before: 0.000, after: 1.000 },
  { module: "is_palindrome",     before: 0.200, after: 1.000 },
  { module: "fizzbuzz",          before: 0.200, after: 1.000 },
];

// --- Headline metrics (README "Headline result", reproducible at n=16) ---
export const headline = {
  heldOutKillRate: { before: 0.23, after: 0.79, label: "Held-out kill-rate (3 modules never trained on, n=16)" },
  binarySearch:    { before: 0.31, after: 0.93, label: "binary_search (held-out, n=16)" },
  trainModules:    { before: 0.11, after: 0.91, label: "Train modules (7), in-training n=5" },
  attacksDefeated: { defeated: 12, total: 12, label: "Adversarial cheat attacks defeated -> score 0" },
  zeroSetupSignal: { lazy: 0.62, thorough: 1.00, label: "Lazy suite vs thorough suite (no API key)" },
};

// --- Adversarial attacks (security_checks.py): every one scores 0.000 ---
export const attacks: { name: string; score: number }[] = [
  { name: "forged pass-ledger on stdout", score: 0.0 },
  { name: "forged ledger + SystemExit short-circuit", score: 0.0 },
  { name: "read hidden impl via inspect frame walk", score: 0.0 },
  { name: "object.__subclasses__ gadget walk", score: 0.0 },
  { name: "reach __globals__ via getattr", score: 0.0 },
  { name: "import os to touch the host", score: 0.0 },
  { name: "operator.attrgetter frame-walk reads hidden impl (RED-TEAM killer)", score: 0.0 },
  { name: "import testbench for a pass-iff-reference oracle", score: 0.0 },
  { name: "class __del__ finalizer (prints a verdict AFTER _emit)", score: 0.0 },
  { name: "eval an expression", score: 0.0 },
  { name: "assert False (baseline non-gameable)", score: 0.0 },
  { name: "no test_* functions at all", score: 0.0 },
];

// --- Literal before/after suites for binary_search (suites_heldout.json), witnessed not illustrative ---
// Base (Qwen2.5-3B before RFT) scores 0.0: its duplicate-element assertions fail the reference gate, zeroing the whole suite.
export const baseSuite: string = `def test_edge_case_empty_list():
    assert binary_search([], 5) == -1
def test_middle_index():
    assert binary_search([1, 3, 5, 7], 5) == 2
def test_first_element():
    assert binary_search([1, 3, 5, 7], 1) == 0
def test_duplicate_elements():               # <- fails the reference gate
    assert binary_search([1, 2, 2, 3, 4], 2) == 1
    assert binary_search([1, 2, 2, 3, 4], 3) == 3
# ... 4 more tests; suite scores 0.000 (gate fail)`;

// Trained (after RFT) scores 0.944: passes the gate, kills 17/18 hidden mutants.
export const trainedSuite: string = `def test_edge_case_empty_list():
    assert binary_search([], 5) == -1
def test_single_element_match():
    assert binary_search([2], 2) == 0
def test_out_of_bounds_target():
    assert binary_search([2], 3) == -1
def test_found_at_start():
    assert binary_search([1, 3, 5, 7], 1) == 0
def test_found_in_middle():
    assert binary_search([1, 3, 5, 7], 7) == 3
def test_found_in_end():
    assert binary_search([1, 3, 5, 7], 3) == 1`;     // rate 0.944, killed 17/18

// --- Sponsor stack & track (README / SUBMISSION) ---
export const track = {
  name: "Agentic Collaboration",
  wedge:
    "Chip Design — the same gym ports to Verilog testbenches: mutants become injected RTL faults, a kill is a failing assertion in simulation.",
};

export const sponsors: { name: string; role: string; status: string }[] = [
  {
    name: "Modal",
    role: "Serverless A100 — where the GRPO run actually trained; the LoRA adapter lives on a Modal volume",
    status: "Core, real",
  },
  {
    name: "HUD",
    role: "The forge_testbench env template; frontier baselines via the HUD gateway (Qwen3-8B 0.90, Claude 0.60)",
    status: "Env + baselines",
  },
  {
    name: "Fireworks",
    role: "Eval-Protocol RFT handoff wired (reward.py, testbench_eval_protocol.py); best-of-1 inference baseline 0.487 (incl. gate failures)",
    status: "Wired; RFT launch blocked on billing",
  },
  {
    name: "Anthropic",
    role: "Claude as the frontier before/after baseline",
    status: "Baseline",
  },
  {
    name: "Daytona",
    role: "daytona_runner.py for sandboxing untrusted suites (REWARDFORGE_RUNNER=daytona)",
    status: "Present, not yet exercised",
  },
];

export const honestCaveat: string =
  "Training landed on Modal because HUD's training backend hit capacity limits and Fireworks RFT was billing-blocked — so the verified result is Modal-led. We present what's real.";
