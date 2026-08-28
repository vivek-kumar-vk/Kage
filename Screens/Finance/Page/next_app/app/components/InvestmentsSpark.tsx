"use client";

import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { useCountUp } from "@/app/lib/useCountUp";
import { formatINR } from "@/app/lib/formatINR";
import { motion } from "framer-motion";
import { usePrefersReducedMotion } from "@/app/lib/usePrefersReducedMotion";
import { TiltCard } from "./TiltCard";

/** Investments — a self-drawing line of the last 12 months with an area
    fade and a glowing leading dot. Seed data (P8). */
export function InvestmentsSpark() {
  const reduce = usePrefersReducedMotion();
  const { current, series } = BLUEPRINT_SEED.investments;
  const shown = useCountUp(current);

  const W = 240;
  const H = 80;
  const PAD = 6;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const coords = series.map((v, i) => {
    const x = (i / (series.length - 1)) * (W - PAD * 2) + PAD;
    const y = H - PAD - ((v - min) / span) * (H - PAD * 2);
    return [x, y] as const;
  });
  const line = `M ${coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L ")}`;
  const area = `${line} L ${coords[coords.length - 1][0].toFixed(1)},${H} L ${coords[0][0].toFixed(1)},${H} Z`;
  const [lx, ly] = coords[coords.length - 1];

  return (
    <TiltCard>
      <div aria-label="Investments">
        <div className="flex items-baseline justify-between">
          <p className="num text-[10px] tracking-[0.24em] text-dim">INVESTMENTS</p>
          <p className="num text-sm grad-text-wealth neon-glow-amber">{formatINR(Math.round(shown))}</p>
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 h-24 w-full" preserveAspectRatio="none">
          <defs>
            <linearGradient id="is-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F2A93B" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#F2A93B" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#is-area)" stroke="none" />
          <motion.path
            d={line}
            fill="none"
            stroke="var(--amber)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: reduce ? 1 : 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.4, ease: "easeInOut" as const }}
          />
          <circle cx={lx} cy={ly} r={3} fill="var(--gold)" className="neon-glow-amber" />
        </svg>
        <p className="num mt-1 text-[10px] text-dim">last 12 months</p>
      </div>
    </TiltCard>
  );
}
