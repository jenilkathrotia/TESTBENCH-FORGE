import { motion, useSpring, useTransform, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

interface AnimatedCounterProps {
  value: number;
  suffix?: string;
  prefix?: string;
  // Number of decimal places to render (0 = integer, like the reddial original).
  decimals?: number;
}

// Spring-eased number rollup — the engine behind every metric box. Mirrors the
// reddial AnimatedCounter: motion is enhancement, never a visibility gate, so we
// render the real number until the spring is allowed to tick. Adds an optional
// `decimals` so we can roll up kill-rates like 0.79 (not just integers).
export function AnimatedCounter({ value, suffix = "", prefix = "", decimals = 0 }: AnimatedCounterProps) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const reduce = useReducedMotion();

  const spring = useSpring(safeValue, { mass: 1, stiffness: 75, damping: 20 });
  const fmt = (v: number) => (Number.isFinite(v) ? v : 0).toFixed(decimals);
  const display = useTransform(spring, (current) => prefix + fmt(current) + suffix);

  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    spring.set(safeValue);
  }, [safeValue, spring]);

  useEffect(() => {
    if (!reduce) setAnimate(true);
  }, [reduce]);

  if (!animate) {
    return <span>{prefix + fmt(safeValue) + suffix}</span>;
  }

  return <motion.span>{display}</motion.span>;
}
