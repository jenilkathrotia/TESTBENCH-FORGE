import { motion } from "framer-motion";
import { ShieldOff, ShieldCheck } from "lucide-react";

interface AttackListProps {
  attacks: { name: string; score: number }[];
  // When false, every row shows its menacing "EXPLOIT" state; when true each
  // row flips (staggered) to the neutralized "0.000" state.
  defeated: boolean;
}

// The 12 adversarial cheat attacks. Pre-reveal each row reads as a live exploit
// (red, "EXPLOIT", a fake 1.000). On reveal they flip one by one to the defeated
// state: acid border, ShieldCheck, score 0.000. This is the "we broke our own
// reward, then fixed it" payload, made literal.
export function AttackList({ attacks, defeated }: AttackListProps) {
  return (
    <div className="attack-grid">
      {attacks.map((a, i) => {
        const killer = a.name.includes("RED-TEAM");
        return (
          <motion.div
            key={a.name}
            className={`attack-row ${defeated ? "defeated" : "live"} ${killer ? "killer" : ""}`}
            initial={{ x: -8 }}
            animate={{ x: 0 }}
            transition={{ duration: 0.3, delay: 0.05 * i, ease: [0.16, 1, 0.3, 1] }}
          >
            <span className="attack-row-icon">
              {defeated ? <ShieldCheck size={16} /> : <ShieldOff size={16} />}
            </span>
            <span className="attack-row-name">{a.name}</span>
            <motion.span
              className="attack-row-score"
              key={defeated ? "d" : "l"}
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.05 * i + 0.1 }}
            >
              {defeated ? "0.000" : "1.000✗"}
            </motion.span>
            <span className="attack-row-tag">{defeated ? "NEUTRALIZED" : "EXPLOIT"}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
