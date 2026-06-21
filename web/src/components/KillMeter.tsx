import { motion } from "framer-motion";
import { AnimatedCounter } from "./AnimatedCounter";

export interface KillRow {
  module: string;
  before: number;
  after: number;
}

interface KillMeterProps {
  rows: KillRow[];
  // When true (the beat is visible) the trained bars grow from base -> trained.
  active: boolean;
  // Highlight a single hero module (e.g. binary_search).
  hero?: string;
}

// A bug-kill METER: per-module twin bars. The faint "before" bar sits underneath
// the acid "after" bar, which grows from the base level up to the trained level
// on reveal. Mirrors reddial's VectorTable progress-fill (4px track, glow,
// scaleX grow) but repurposed for kill-rate before -> after.
export function KillMeter({ rows, active, hero }: KillMeterProps) {
  return (
    <div className="kill-meter">
      {rows.map((r, index) => {
        const beforePct = Math.round(r.before * 100);
        const afterPct = Math.round(r.after * 100);
        const isHero = hero === r.module;
        const delta = r.after - r.before;
        const col =
          r.after >= 0.9 ? "var(--accent-acid)" : r.after >= 0.5 ? "var(--grade-b)" : "var(--status-warning)";

        return (
          <motion.div
            key={r.module}
            className={`kill-row ${isHero ? "hero" : ""}`}
            initial={{ x: -8 }}
            animate={{ x: 0 }}
            transition={{ duration: 0.4, delay: 0.2 + index * 0.06, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="kill-row-head">
              <span className="kill-module">{r.module}</span>
              <span className="kill-numbers">
                <span className="kill-before">{r.before.toFixed(2)}</span>
                <span className="kill-arrow">→</span>
                <span className="kill-after" style={{ color: col }}>
                  {active ? <AnimatedCounter value={r.after} decimals={2} /> : r.before.toFixed(2)}
                </span>
              </span>
            </div>
            <div className="kill-track">
              {/* faint baseline bar */}
              <div className="kill-fill-base" style={{ width: `${beforePct}%` }} />
              {/* trained bar grows base -> trained on reveal */}
              <motion.div
                className="kill-fill-after"
                style={{ backgroundColor: col, boxShadow: `0 0 12px ${col}` }}
                initial={{ width: `${beforePct}%` }}
                animate={{ width: active ? `${afterPct}%` : `${beforePct}%` }}
                transition={{ duration: 0.9, delay: 0.35 + index * 0.08, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <div className="kill-delta" style={{ color: col }}>
              +{Math.round(delta * 100)} pts
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
