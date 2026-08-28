import type { SegmentMeterProps } from "./types";

export function SegmentMeter({ segments }: SegmentMeterProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {segments.map((s, i) => (
        <div key={i}>
          <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "ui-monospace, monospace", fontVariantNumeric: "tabular-nums", fontSize: 11, color: "var(--liv-text-dim)", marginBottom: 4 }}>
            <span>{s.label}</span>
            <span>{Math.round(s.pct)}%</span>
          </div>
          <div style={{ height: 8, borderRadius: 999, background: "var(--liv-bg-2)", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, s.pct))}%`, background: "var(--liv-accent)", boxShadow: "0 0 10px var(--liv-glow)" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
