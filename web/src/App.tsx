import { useCallback, useEffect, useState, type ReactNode } from "react";
import { motion, AnimatePresence, MotionConfig } from "framer-motion";
import {
  FlaskConical,
  ChevronRight,
  ChevronLeft,
  Cpu,
  ShieldAlert,
  TrendingUp,
  Gauge,
  Beaker,
  KeyRound,
  Skull,
  Lock,
  Eye,
  Hash,
} from "lucide-react";
import {
  rewardCurve,
  heldout,
  train,
  headline,
  attacks,
  baseSuite,
  trainedSuite,
  track,
  sponsors,
  honestCaveat,
} from "./data";
import { AnimatedCounter } from "./components/AnimatedCounter";
import { KillMeter } from "./components/KillMeter";
import { RewardCurve } from "./components/RewardCurve";
import { AttackList } from "./components/AttackList";
import { SuiteDiff } from "./components/SuiteDiff";
import { MutantWalk } from "./components/MutantWalk";
import "./styles.css";

type StepId = "hero" | "beat1" | "beat2" | "beat3";

const STEPS: { id: StepId; label: string; icon: typeof FlaskConical }[] = [
  { id: "hero", label: "Thesis", icon: FlaskConical },
  { id: "beat1", label: "Honest Oracle", icon: Gauge },
  { id: "beat2", label: "We Broke It", icon: ShieldAlert },
  { id: "beat3", label: "It Generalizes", icon: TrendingUp },
];

export function App() {
  const [step, setStep] = useState(0);
  const current = STEPS[step].id;

  const go = useCallback(
    (dir: 1 | -1) => setStep((s) => Math.max(0, Math.min(STEPS.length - 1, s + dir))),
    [],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "Enter") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(-1);
      } else if (e.key >= "1" && e.key <= "4") {
        setStep(Number(e.key) - 1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  return (
    <MotionConfig reducedMotion="user">
      <div className="app-container">
        {/* ── Nav rail / stepper (left) ── */}
        <nav className="nav-rail">
          <div className="rail-brand">
            <div className="brand-orb">
              <FlaskConical size={18} strokeWidth={2.5} />
            </div>
          </div>
          <div className="rail-links">
            {STEPS.map(({ id, label, icon: Icon }, i) => (
              <button
                key={id}
                type="button"
                className={`rail-item ${step === i ? "active" : ""}`}
                aria-label={label}
                aria-current={step === i ? "page" : undefined}
                title={`${i === 0 ? "Hero" : "Beat " + i} · ${label}`}
                onClick={() => setStep(i)}
              >
                <Icon size={20} />
              </button>
            ))}
          </div>
          <div className="rail-bottom">
            <div className="rail-step-count" aria-hidden="true">
              {step === 0 ? "00" : `0${step}`}
            </div>
          </div>
        </nav>

        <div className="app-main">
          {/* ── Topbar ── */}
          <header className="topbar">
            <div className="topbar-left">
              <h1>
                TestBench-Forge / <span>{STEPS[step].label}</span>
              </h1>
            </div>
            <div className="topbar-right">
              <div className="health-status" role="status">
                <span className="health-indicator up" aria-hidden="true" />
                EXECUTION ORACLE · NO LLM JUDGE
              </div>
              <div className="step-dots" role="tablist" aria-label="Demo beats">
                {STEPS.map((s, i) => (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    aria-selected={step === i}
                    aria-label={s.label}
                    className={`step-dot ${step === i ? "active" : ""} ${i < step ? "done" : ""}`}
                    onClick={() => setStep(i)}
                  />
                ))}
              </div>
            </div>
          </header>

          {/* ── Stage ── */}
          <main className="stage">
            <div className="stage-wrapper">
              <AnimatePresence mode="wait">
                <motion.section
                  key={current}
                  className="beat"
                  initial={{ y: 14 }}
                  animate={{ y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                >
                  {current === "hero" && <Hero />}
                  {current === "beat1" && <Beat1 />}
                  {current === "beat2" && <Beat2 />}
                  {current === "beat3" && <Beat3 />}
                </motion.section>
              </AnimatePresence>
            </div>

            {/* ── Footer: sponsor stack + track ── */}
            <Footer />
          </main>

          {/* ── Advance controls ── */}
          <div className="advance-bar">
            <button
              type="button"
              className="advance-btn ghost"
              onClick={() => go(-1)}
              disabled={step === 0}
              aria-label="Previous beat"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="advance-hint">← / → or space to advance · 1–4 to jump</span>
            <button
              type="button"
              className="advance-btn primary"
              onClick={() => go(1)}
              disabled={step === STEPS.length - 1}
              aria-label="Next beat"
            >
              {step === STEPS.length - 1 ? "END" : "NEXT"} <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </MotionConfig>
  );
}

/* ─────────────────────────────────────────────────────────── HERO ── */
function Hero() {
  return (
    <div className="hero">
      <motion.div
        className="hero-kicker"
        initial={{ y: 8 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        RSI · TRAIN THE GRADER, NOT THE OUTPUT
      </motion.div>
      <motion.h1
        className="hero-title"
        initial={{ y: 12 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
      >
        We built an RL reward we couldn't game.
      </motion.h1>
      <motion.p
        className="hero-thesis"
        initial={{ y: 12 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, delay: 0.12, ease: [0.16, 1, 0.3, 1] }}
      >
        We broke it ourselves with a frame-walk exploit that faked a perfect score, fixed it so all{" "}
        <strong>12 attacks now score zero</strong>, and the test-writing skill it trains generalizes to modules it
        never saw (held-out mean <span className="acid">0.23 → 0.79</span>, reproducible at n=16;{" "}
        <code>binary_search</code> <span className="acid">0.31 → 0.93</span>).
      </motion.p>
      <motion.p
        className="hero-sub"
        initial={{ y: 12 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, delay: 0.18, ease: [0.16, 1, 0.3, 1] }}
      >
        Train the test that catches the bug a human reviewer misses.
      </motion.p>

      <div className="hero-metrics">
        {[
          { v: headline.zeroSetupSignal.lazy, suf: "", dec: 2, label: "lazy suite", tone: "warning" },
          { v: headline.zeroSetupSignal.thorough, suf: "", dec: 2, label: "thorough suite", tone: "acid" },
          { v: headline.attacksDefeated.defeated, suf: "/12", dec: 0, label: "cheat attacks → 0", tone: "acid" },
          { v: headline.heldOutKillRate.after, suf: "", dec: 2, label: "held-out (from 0.23)", tone: "acid" },
        ].map((m, i) => (
          <motion.div
            key={m.label}
            className="hero-metric"
            initial={{ y: 10 }}
            animate={{ y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className={`hero-metric-value ${m.tone}`}>
              <AnimatedCounter value={m.v} suffix={m.suf} decimals={m.dec} />
            </div>
            <div className="hero-metric-label">{m.label}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────────────────────────────────────── BEAT 1 ── */
function Beat1() {
  return (
    <BeatShell
      n={1}
      icon={Gauge}
      title="Honest oracle"
      lede="No LLM judge — a pure execution oracle. A lazy happy-path suite scores 0.62; a thorough edge-case suite scores 1.00. assert False scores 0.00 because it fails the reference gate. Clone, run python3 selftest.py on system Python — no venv, no key, no GPU — and you see the exact same numbers in five seconds."
      feature={{ before: null, after: "0.62 vs 1.00", label: "lazy vs thorough — no API key" }}
    >
      <div className="card">
        <div className="card-header">
          <Beaker size={18} />
          <span className="card-title">Watch one mutant</span>
          <span className="card-tag mono">selftest.py · system python · ~5s</span>
        </div>
        <div className="card-body">
          <MutantWalk active />
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <KeyRound size={18} />
          <span className="card-title">Base suite vs trained suite (binary_search)</span>
          <span className="card-tag mono">suites_heldout.json · witnessed, not illustrative</span>
        </div>
        <div className="card-body">
          <SuiteDiff baseSuite={baseSuite} trainedSuite={trainedSuite} baseScore={0.0} trainedScore={0.944} />
        </div>
      </div>
    </BeatShell>
  );
}

/* ───────────────────────────────────────────────────── BEAT 2 ── */
function Beat2() {
  const [defeated, setDefeated] = useState(false);

  // Auto-flip shortly after the beat mounts so a screen recording captures the
  // exploit -> neutralized transition without a click; the toggle stays for live demos.
  useEffect(() => {
    const t = setTimeout(() => setDefeated(true), 900);
    return () => clearTimeout(t);
  }, []);

  const fixes = [
    { icon: Lock, title: "Import allowlist", body: "A denylist is a sieve, so we allowlist. Untrusted suites can't reach os, inspect, or operator." },
    { icon: Eye, title: "Frame isolation", body: "The impl source is deleted before the suite runs, so a stack walk finds nothing to read." },
    { icon: Hash, title: "Nonce-authenticated verdict", body: "A forged pass-ledger is ignored: only a nonce-signed verdict counts." },
  ];

  return (
    <BeatShell
      n={2}
      icon={ShieldAlert}
      title="We broke our own reward"
      lede='The suite is untrusted code, so we attacked it ourselves — and broke it. A content-free suite used operator.attrgetter("f_back") to walk the call stack, read the hidden reference source, and faked a perfect 1.0 with zero real tests. We fixed it: run python3 security_checks.py — 12 adversarial attacks all score 0, legitimate suites stay 1.00.'
      feature={{ before: null, after: "12 / 12", label: "attacks → score 0" }}
    >
      <div className="card">
        <div className="card-header">
          <Skull size={18} />
          <span className="card-title">The 12 adversarial cheat attacks</span>
          <button
            type="button"
            className={`flip-toggle ${defeated ? "on" : ""}`}
            onClick={() => setDefeated((d) => !d)}
          >
            {defeated ? "show exploit" : "run security_checks.py"}
          </button>
        </div>
        <div className="card-body">
          <AttackList attacks={attacks} defeated={defeated} />
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <Lock size={18} />
          <span className="card-title">The three fixes</span>
          <span className="card-tag mono">untrusted-code hardening</span>
        </div>
        <div className="card-body">
          <div className="fix-grid">
            {fixes.map((f, i) => (
              <motion.div
                key={f.title}
                className="fix-card"
                initial={{ y: 10 }}
                animate={{ y: 0 }}
                transition={{ duration: 0.45, delay: 0.2 + i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              >
                <span className="fix-icon">
                  <f.icon size={18} />
                </span>
                <div className="fix-title">{f.title}</div>
                <div className="fix-body">{f.body}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </BeatShell>
  );
}

/* ───────────────────────────────────────────────────── BEAT 3 ── */
function Beat3() {
  return (
    <BeatShell
      n={3}
      icon={TrendingUp}
      title="It generalizes — the RSI signal"
      lede="We trained Qwen2.5-3B with GRPO on a single Modal A100, on 7 modules, then evaluated on 3 modules it never trained on. Held-out mean climbed 0.23 → 0.79, binary_search 0.31 → 0.93, and the GRPO reward curve went 0.17 → 1.0 over 80 steps. The skill — write boundary tests that kill bugs — transferred to tasks it never saw."
      feature={{ before: "0.23", after: "0.79", label: "held-out mean · binary_search 0.31 → 0.93" }}
    >
      <div className="card hero-card">
        <div className="card-header">
          <TrendingUp size={18} />
          <span className="card-title">Held-out kill-rate — 3 modules never trained on</span>
          <span className="card-tag mono">grpo_result.json · saved-adapter eval</span>
        </div>
        <div className="card-body">
          <KillMeter rows={heldout} active hero="binary_search" />
        </div>
      </div>

      <div className="beat3-grid">
        <div className="card">
          <div className="card-header">
            <Cpu size={18} />
            <span className="card-title">GRPO reward curve</span>
          </div>
          <div className="card-body">
            <RewardCurve curve={rewardCurve} active />
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <Beaker size={18} />
            <span className="card-title">Train modules (7) — seen in training</span>
          </div>
          <div className="card-body">
            <KillMeter rows={train} active />
          </div>
        </div>
      </div>

      <div className="rsi-statement">
        That's the RSI thesis made concrete: you don't label outputs, you train the grader, and the grading
        generalizes.
      </div>
    </BeatShell>
  );
}

/* ───────────────────────────────────────────── shared beat shell ── */
interface BeatShellProps {
  n: number;
  icon: typeof Gauge;
  title: string;
  lede: string;
  feature: { before: string | null; after: string; label: string };
  children: ReactNode;
}

function BeatShell({ n, icon: Icon, title, lede, feature, children }: BeatShellProps) {
  return (
    <div className="beat-shell">
      <div className="beat-head">
        <div className="beat-head-left">
          <span className="beat-num mono">BEAT {n}</span>
          <h2 className="beat-title">
            <Icon size={26} /> {title}
          </h2>
          <p className="beat-lede">{lede}</p>
        </div>
        <motion.div
          className="beat-feature"
          initial={{ scale: 0.94 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="beat-feature-label">{feature.label}</div>
          <div className="beat-feature-value">
            {feature.before && <span className="beat-feature-before">{feature.before} →</span>}
            <span className="acid">{feature.after}</span>
          </div>
        </motion.div>
      </div>
      <div className="beat-body">{children}</div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────── footer ── */
function Footer() {
  return (
    <footer className="sponsor-footer">
      <div className="sponsor-track">
        <span className="sponsor-track-label mono">TRACK</span>
        <span className="sponsor-track-name">{track.name}</span>
        <span className="sponsor-track-wedge">{track.wedge}</span>
      </div>
      <div className="sponsor-grid">
        {sponsors.map((s) => (
          <div className="sponsor-card" key={s.name}>
            <div className="sponsor-name">{s.name}</div>
            <div className="sponsor-role">{s.role}</div>
            <div className="sponsor-status mono">{s.status}</div>
          </div>
        ))}
      </div>
      <div className="sponsor-caveat">
        <strong>Honest caveat:</strong> {honestCaveat}
      </div>
    </footer>
  );
}
