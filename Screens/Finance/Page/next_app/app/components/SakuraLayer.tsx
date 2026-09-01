"use client";

import { motion, useReducedMotion } from "framer-motion";

/** App-wide drifting sakura layer, fixed behind all content. Petal colour
    is var(--liv-petal); the layer carries the livery class itself since it
    sits outside the grid wrapper that normally sets it. Reduced motion →
    petals rendered static and faint. Evening tone. */
export function SakuraLayer({ livery }: { livery: string }) {
  const reduce = useReducedMotion();
  const petals = Array.from({ length: 16 }, (_, i) => ({
    left: `${(i * 6 + 4) % 100}%`,
    size: 7 + (i % 4) * 3,
    delay: (i % 8) * 1.4,
    duration: 16 + (i % 5) * 4,
    drift: ((i % 3) - 1) * 44,
  }));

  return (
    <div
      className={livery}
      aria-hidden
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
        pointerEvents: "none",
      }}
    >
      {petals.map((p, i) => (
        <motion.span
          key={i}
          style={{
            width: `${p.size}px`,
            height: `${p.size}px`,
            borderRadius: "50% 0 50% 50%",
            background: "var(--liv-petal)",
            opacity: reduce ? 0.28 : 0.42,
            position: "absolute",
            top: reduce ? `${(i * 13) % 92}%` : "-6%",
            left: p.left,
          }}
          animate={reduce ? undefined : { y: ["0vh", "112vh"], x: [0, p.drift, 0], rotate: [0, 180, 360] }}
          transition={reduce ? undefined : { duration: p.duration, delay: p.delay, repeat: Infinity, ease: "linear" }}
        />
      ))}
    </div>
  );
}
