"use client";

import { motion } from "framer-motion";
import { usePrefersReducedMotion } from "@/app/lib/usePrefersReducedMotion";

/** The hero "portfolio core" for the TELEMETRY tab: concentric rings, a
    rotating radar sweep and a pulsing centre. Pure SVG + framer-motion;
    goes still under reduced motion. Decorative — no real data bound. */
export function PulseCore() {
  const reduce = usePrefersReducedMotion();
  const spin = reduce
    ? {}
    : { animate: { rotate: 360 }, transition: { duration: 7, repeat: Infinity, ease: "linear" as const } };
  const pulse = reduce
    ? {}
    : {
        animate: { scale: [1, 1.25, 1], opacity: [0.9, 0.5, 0.9] },
        transition: { duration: 2.4, repeat: Infinity, ease: "easeInOut" as const },
      };

  return (
    <section
      aria-label="Portfolio core"
      className="glass spin-border relative overflow-hidden rounded-[18px] p-6"
    >
      <div className="flex items-center gap-6">
        <svg viewBox="0 0 200 200" className="h-32 w-32 shrink-0">
          <defs>
            <radialGradient id="pc-sweep" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#3DE1FF" stopOpacity="0.55" />
              <stop offset="100%" stopColor="#3DE1FF" stopOpacity="0" />
            </radialGradient>
          </defs>
          <circle cx="100" cy="100" r="82" fill="none" stroke="var(--sumi-line)" strokeWidth="1" />
          <circle cx="100" cy="100" r="56" fill="none" stroke="var(--sumi-line)" strokeWidth="1" />
          <circle cx="100" cy="100" r="30" fill="none" stroke="var(--sumi-line)" strokeWidth="1" />
          <motion.g style={{ transformOrigin: "100px 100px" }} {...spin}>
            <path d="M100 100 L100 18 A82 82 0 0 1 171 60 Z" fill="url(#pc-sweep)" />
          </motion.g>
          <motion.circle
            cx="100"
            cy="100"
            r="8"
            fill="#8B7BFF"
            style={{ transformOrigin: "100px 100px" }}
            {...pulse}
          />
        </svg>
        <div>
          <p className="num text-[10px] tracking-[0.24em] text-dim">PORTFOLIO CORE</p>
          <p className="num mt-1 grad-text-flow neon-glow-cyan text-2xl font-bold">SYNCED</p>
          <p className="num mt-1 text-[10px] text-dim">telemetry stream nominal</p>
        </div>
      </div>
    </section>
  );
}
