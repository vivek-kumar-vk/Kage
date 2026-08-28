"use client";

import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { useCountUp } from "@/app/lib/useCountUp";
import { formatINR } from "@/app/lib/formatINR";
import { motion } from "framer-motion";
import { usePrefersReducedMotion } from "@/app/lib/usePrefersReducedMotion";
import { TiltCard } from "./TiltCard";

/** Portfolio value — current market value, counting up on load with the
    gradient fill and neon glow. Seed data (P8). */
export function PortfolioReadout() {
  const reduce = usePrefersReducedMotion();
  const shown = useCountUp(BLUEPRINT_SEED.portfolioValue);

  return (
    <TiltCard>
      <div aria-label="Portfolio value">
        <p className="num text-[10px] tracking-[0.24em] text-dim">PORTFOLIO VALUE</p>
        <p className="num mt-1 text-3xl font-bold grad-text-wealth neon-glow-amber">
          {formatINR(Math.round(shown))}
        </p>
        <p className="num mt-1 text-[10px] text-dim">current market value</p>
        <motion.div
          className="mt-4 h-[3px] rounded"
          style={{ transformOrigin: "left", background: "var(--grad-wealth)" }}
          initial={{ scaleX: reduce ? 1 : 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
    </TiltCard>
  );
}
