"use client";

import { useCountUp } from "@/app/lib/useCountUp";
import { formatINR } from "@/app/lib/formatINR";

/** A figure that counts up on mount and wears a gradient fill + neon
    glow. `grad` picks the palette: "wealth" (amber→gold) or "flow"
    (cyan→violet). Always monospace tabular via `.num`. */
export function NeonNumber({
  value,
  grad = "wealth",
  format = formatINR,
  className = "",
}: {
  value: number;
  grad?: "wealth" | "flow";
  format?: (n: number) => string;
  className?: string;
}) {
  const shown = useCountUp(value);
  const gradClass = grad === "flow" ? "grad-text-flow" : "grad-text-wealth";
  const glowClass = grad === "flow" ? "neon-glow-cyan" : "neon-glow-amber";

  return (
    <span className={`num inline-block ${gradClass} ${glowClass} ${className}`}>
      {format(Math.round(shown))}
    </span>
  );
}
