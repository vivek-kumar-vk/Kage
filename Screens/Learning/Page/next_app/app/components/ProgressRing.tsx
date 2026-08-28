"use client";

/** A conic-gradient ring, no chart library. 0% reads as an honestly
    empty ring, never hidden. */
export function ProgressRing({ pct, label }: { pct: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className="flex items-center gap-3">
      <div
        className="progress-ring num flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-xs text-bone"
        style={{ "--pct": clamped } as React.CSSProperties}
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-panel">
          {clamped}%
        </div>
      </div>
      <span className="text-xs text-dim">{label}</span>
    </div>
  );
}
