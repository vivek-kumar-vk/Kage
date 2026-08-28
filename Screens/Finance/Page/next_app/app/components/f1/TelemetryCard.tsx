import type { TelemetryCardProps } from "./types";

export function TelemetryCard({ label, value, sub, edge = true, children }: TelemetryCardProps) {
  return (
    <div className={edge ? "livery-edge" : undefined} style={{ background: "var(--liv-surface)", border: "1px solid var(--liv-line)", borderRadius: 14, padding: 20, position: "relative" }}>
      <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 11, letterSpacing: 1.5, textTransform: "uppercase", color: "var(--liv-text-dim)", marginBottom: value ? 6 : 12 }}>{label}</div>
      {value && <div style={{ fontFamily: "ui-monospace, monospace", fontVariantNumeric: "tabular-nums", fontSize: 30, fontWeight: 700, color: "var(--liv-text)" }}>{value}</div>}
      {sub && <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 11, color: "var(--liv-text-dim)", marginTop: 4 }}>{sub}</div>}
      {children && <div style={{ marginTop: 14 }}>{children}</div>}
    </div>
  );
}
