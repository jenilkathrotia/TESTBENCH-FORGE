import { motion } from "framer-motion";

interface MutantWalkProps {
  active: boolean;
}

// Beat 1 visual: one mutant (an off-by-one in binary_search), shown as a diff.
// The lazy happy-path suite walks right past it (scores 0.62); the thorough
// edge-case suite kills it (scores 1.00). `assert False` scores 0.00 (gate fail).
export function MutantWalk({ active }: MutantWalkProps) {
  const lanes = [
    { label: "lazy suite (happy path)", score: 0.62, verdict: "walked past the off-by-one", tone: "warning" as const },
    { label: "thorough suite (edge cases)", score: 1.0, verdict: "killed the mutant", tone: "success" as const },
    { label: "assert False", score: 0.0, verdict: "fails the reference gate", tone: "danger" as const },
  ];

  return (
    <div className="mutant-walk">
      <div className="mutant-code">
        <div className="mutant-code-head">injected mutant · binary_search</div>
        <pre className="suite-pre">
{`-    mid = (lo + hi) // 2
+    mid = (lo + hi) // 2 + 1   # off-by-one`}
        </pre>
      </div>

      <div className="mutant-lanes">
        {lanes.map((lane, i) => (
          <motion.div
            key={lane.label}
            className={`mutant-lane ${lane.tone}`}
            initial={{ x: -8 }}
            animate={{ x: 0 }}
            transition={{ duration: 0.4, delay: 0.2 + i * 0.1, ease: [0.16, 1, 0.3, 1] }}
          >
            <span className="mutant-lane-label">{lane.label}</span>
            <span className="mutant-lane-track">
              <motion.span
                className={`mutant-lane-fill ${lane.tone}`}
                initial={{ scaleX: 0.001 }}
                animate={{ scaleX: active ? lane.score || 0.02 : 0.001 }}
                transition={{ duration: 0.8, delay: 0.3 + i * 0.12, ease: "easeOut" }}
                style={{ transformOrigin: "left" }}
              />
            </span>
            <span className={`mutant-lane-score ${lane.tone}`}>{lane.score.toFixed(2)}</span>
            <span className="mutant-lane-verdict">{lane.verdict}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
