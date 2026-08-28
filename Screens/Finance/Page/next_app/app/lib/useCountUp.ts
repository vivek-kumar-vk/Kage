"use client";

import { animate } from "framer-motion";
import { useEffect, useState } from "react";

/** Eases a number from 0 up to `target` on mount. Until the first
    animation frame lands (and always, under reduced motion or a
    frame-starved background tab) it reports `target` — so the figure is
    never shown as a misleading 0. */
export function useCountUp(target: number, durationMs = 1100): number {
  const [live, setLive] = useState<number | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const controls = animate(0, target, {
      duration: durationMs / 1000,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setLive(v),
    });
    return () => controls.stop();
  }, [target, durationMs]);

  return live ?? target;
}
