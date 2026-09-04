"use client";

/** Cards that cannot yet be scoped to a historical month say so plainly
 * instead of silently showing live numbers under a back-dated label (D28.3,
 * AGENTS.md) — the backend does not support `?through=` yet. */
export default function HistoricalMarker({ label }: { label: string }) {
  return <span className="text-[9px] uppercase tracking-[.1em] text-aurum-faint">AS OF {label} — not yet historical</span>;
}
