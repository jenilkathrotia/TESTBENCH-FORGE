# TestBench-Forge — demo console

An interactive Vite + React + TypeScript app for the TestBench-Forge demo video.
Dark "acid glass" console matching the RedDial design language, repurposed for our
content: a hero thesis plus three ~1-minute beats, navigable by the left stepper,
the NEXT button, arrow keys (← / →), space/enter, or number keys 1–4.

All numbers are real captured data from the repo root (`grpo_result.json`,
`suites_heldout.json`, `security_checks.py`, `selftest.py`, `README.md`), pinned in
`src/data.ts`.

## Beats

- **Hero** — the one-line thesis and four headline metrics (animated counters).
- **Beat 1 · Honest oracle** — lazy 0.62 vs thorough 1.00; one mutant walked past
  vs killed; base (0.000) vs trained (0.944) binary_search suites side by side.
- **Beat 2 · We broke our own reward** — the 12 cheat attacks flip from EXPLOIT to
  score 0.000 on reveal; the three fixes (allowlist, frame isolation, nonce verdict).
- **Beat 3 · It generalizes** — held-out kill-rate bars climbing base → trained
  (binary_search 0.31 → 0.93 hero), the 80-step GRPO reward curve drawing itself
  (0.17 → 1.0), train-module bars, and the RSI one-liner.
- **Footer** — sponsor stack + track, with the honest caveat.

## Run

```
cd /Users/charlie/events/YC---RL-Gym/web
npm install
npm run dev
```

Build: `npm run build` (runs `tsc -b && vite build`).
