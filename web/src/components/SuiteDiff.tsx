import { motion } from "framer-motion";
import { XCircle, CheckCircle2 } from "lucide-react";

interface SuiteDiffProps {
  baseSuite: string;
  trainedSuite: string;
  baseScore: number;
  trainedScore: number;
}

// Side-by-side code panes: the base (pre-RFT) suite that fails the reference gate
// and scores 0.000, beside the trained suite that passes and scores 0.944.
// Dark-inset evidence cards with acid mono <pre>, mirroring reddial's EvidenceLog.
export function SuiteDiff({ baseSuite, trainedSuite, baseScore, trainedScore }: SuiteDiffProps) {
  return (
    <div className="suite-diff">
      <motion.div
        className="suite-pane base"
        initial={{ x: -8 }}
        animate={{ x: 0 }}
        transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="suite-pane-head danger">
          <span className="suite-pane-icon">
            <XCircle size={16} />
          </span>
          <span className="suite-pane-title">base · Qwen2.5-3B before RFT</span>
          <span className="suite-score danger">{baseScore.toFixed(3)}</span>
        </div>
        <pre className="suite-pre">{baseSuite}</pre>
        <div className="suite-pane-foot">duplicate-element asserts fail the reference gate → whole suite zeroes</div>
      </motion.div>

      <motion.div
        className="suite-pane trained"
        initial={{ x: 8 }}
        animate={{ x: 0 }}
        transition={{ duration: 0.5, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="suite-pane-head success">
          <span className="suite-pane-icon">
            <CheckCircle2 size={16} />
          </span>
          <span className="suite-pane-title">trained · after RFT</span>
          <span className="suite-score success">{trainedScore.toFixed(3)}</span>
        </div>
        <pre className="suite-pre">{trainedSuite}</pre>
        <div className="suite-pane-foot success">passes the gate · kills 17/18 hidden mutants</div>
      </motion.div>
    </div>
  );
}
