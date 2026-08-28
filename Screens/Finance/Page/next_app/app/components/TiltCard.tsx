"use client";

import type { ReactNode } from "react";
import { useTilt } from "@/app/lib/useTilt";

/** A glass panel that tilts toward the pointer with a cursor-tracking
    specular highlight and a hover scan-pulse. Wrap any telemetry block
    in it. `aria-label` and role stay on the caller's inner content. */
export function TiltCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const { ref, style, onPointerMove, onPointerLeave } = useTilt(6);

  return (
    <div
      ref={ref}
      style={{ ...style, transition: "transform 220ms cubic-bezier(.22,1,.36,1)" }}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      className={`glass scan-pulse relative overflow-hidden p-5 ${className}`}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(220px circle at var(--mx,50%) var(--my,50%), rgba(255,255,255,.07), transparent 60%)",
        }}
      />
      <div className="relative">{children}</div>
    </div>
  );
}
