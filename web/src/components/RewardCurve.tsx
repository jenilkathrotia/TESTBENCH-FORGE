import { motion } from "framer-motion";

interface RewardCurveProps {
  curve: number[];
  active: boolean;
}

// Inline-SVG line chart of the 80-step GRPO reward curve (0..1). The acid
// polyline draws itself via `pathLength` on reveal (0.17 -> 1.0 over 80 steps).
// Mirrors reddial's ImprovementCurve, but Y is NOT inverted here: reward rising
// to the top = the grader getting better. Visibility never gated on opacity.
export function RewardCurve({ curve, active }: RewardCurveProps) {
  const n = curve.length;

  const W = 640;
  const H = 220;
  const padL = 40;
  const padR = 20;
  const padT = 20;
  const padB = 32;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const x = (i: number) => padL + (n <= 1 ? 0 : (i / (n - 1)) * plotW);
  // reward 1 -> top (y = padT), reward 0 -> bottom.
  const y = (r: number) => padT + (1 - r) * plotH;

  const points = curve.map((r, i) => [x(i), y(r)] as const);
  const polyPoints = points.map(([px, py]) => `${px},${py}`).join(" ");

  // Smoothed trend (windowed mean) so the eye reads "0.17 -> 1.0" through noise.
  const win = 8;
  const trend = curve.map((_, i) => {
    const lo = Math.max(0, i - win + 1);
    const slice = curve.slice(lo, i + 1);
    return slice.reduce((a, b) => a + b, 0) / slice.length;
  });
  const trendPoints = trend.map((r, i) => `${x(i)},${y(r)}`).join(" ");

  const first = curve[0];
  const last = curve[n - 1];

  // Horizontal gridlines at 0 / 0.5 / 1.0.
  const grid = [0, 0.5, 1];

  return (
    <div className="improvement-curve">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="GRPO reward per step, rising toward 1.0 over 80 steps"
        preserveAspectRatio="xMidYMid meet"
      >
        {grid.map((g) => (
          <g key={g}>
            <line
              x1={padL}
              y1={y(g)}
              x2={padL + plotW}
              y2={y(g)}
              stroke="var(--glass-border)"
              strokeWidth={1}
              strokeDasharray={g === 0 || g === 1 ? undefined : "3 4"}
              opacity={g === 1 ? 0.6 : 0.4}
            />
            <text
              x={padL - 8}
              y={y(g) + 3}
              fill="var(--text-faint)"
              fontSize={10}
              fontFamily="var(--font-mono)"
              textAnchor="end"
            >
              {g.toFixed(1)}
            </text>
          </g>
        ))}

        {/* raw per-step reward, faint */}
        <motion.polyline
          points={polyPoints}
          fill="none"
          stroke="var(--accent-acid)"
          strokeWidth={1}
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity={0.28}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: active ? 1 : 0 }}
          transition={{ duration: 1.1, ease: "easeOut" }}
        />

        {/* smoothed trend, bold acid with glow */}
        <motion.polyline
          points={trendPoints}
          fill="none"
          stroke="var(--accent-acid)"
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: active ? 1 : 0 }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 0.1 }}
          style={{ filter: "drop-shadow(0 0 6px var(--accent-acid-dim))" }}
        />

        {/* endpoint markers */}
        <circle cx={x(0)} cy={y(first)} r={4} fill="var(--bg-color)" stroke="var(--accent-acid)" strokeWidth={2} />
        <circle cx={x(n - 1)} cy={y(last)} r={4} fill="var(--bg-color)" stroke="var(--accent-acid)" strokeWidth={2} />

        <text x={x(0) + 6} y={y(first) - 8} fill="var(--text-faint)" fontSize={10} fontFamily="var(--font-mono)">
          step 0 · {first.toFixed(2)}
        </text>
        <text
          x={x(n - 1) - 6}
          y={y(last) - 10}
          fill="var(--accent-acid)"
          fontSize={10}
          fontFamily="var(--font-mono)"
          textAnchor="end"
        >
          step {n} · 1.00
        </text>
      </svg>
      <p className="curve-caption">GRPO reward per step (grpo_result.json) · 0.17 → 1.0 over 80 steps</p>
    </div>
  );
}
