"use client";
import { motion, useReducedMotion } from "framer-motion";
import type { WipeInProps } from "./types";

export function WipeIn({ children, delay = 0 }: WipeInProps) {
  const reduced = useReducedMotion();
  if (reduced) return <div>{children}</div>;
  return (
    <motion.div
      initial={{ clipPath: "inset(0 100% 0 0)", opacity: 0 }}
      animate={{ clipPath: "inset(0 0% 0 0)", opacity: 1 }}
      transition={{ duration: 0.38, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
