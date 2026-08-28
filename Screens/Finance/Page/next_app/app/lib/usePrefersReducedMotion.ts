"use client";

import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/** True when the OS asks for reduced motion. Read straight off
    matchMedia (not framer-motion's hook) so it is deterministic on the
    first client render and in headless/background tabs. SSR-safe:
    starts false, corrects on mount. */
export function usePrefersReducedMotion(): boolean {
  // Lazy initializer so the very first client render is already correct
  // (an effect-only read lets a mount animation start before it fires).
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const mq = window.matchMedia(QUERY);
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
