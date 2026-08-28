"use client";

import { motion, useReducedMotion } from "framer-motion";

/** PROTOTYPE — sakura layer for the theme-lab. Colour via var(--liv-petal),
    set by the .liv-* ancestor. Deleted with this folder in Phase 5. */
const SakuraPetals = () => {
  const reduced = useReducedMotion();
  const petals = Array.from({ length: 14 }, (_, i) => ({
    left: `${(i * 7 + 5) % 100}%`,
    size: 8 + (i % 4) * 3,
    delay: (i % 7) * 1.2,
    duration: 14 + (i % 5) * 4,
    drift: ((i % 3) - 1) * 40,
  }));

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 }}>
      {petals.map((p, i) => (
        <motion.span
          key={i}
          style={{
            width: `${p.size}px`,
            height: `${p.size}px`,
            borderRadius: "50% 0 50% 50%",
            background: "var(--liv-petal)",
            opacity: 0.5,
            position: "absolute",
            top: reduced ? `${(i * 11) % 90}%` : "-5%",
            left: p.left,
          }}
          animate={reduced ? undefined : { y: ["0vh", "110vh"], x: [0, p.drift, 0], rotate: [0, 180, 360] }}
          transition={reduced ? undefined : { duration: p.duration, delay: p.delay, repeat: Infinity, ease: "linear" }}
        />
      ))}
    </div>
  );
};

export default SakuraPetals;
