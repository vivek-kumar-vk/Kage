import type { TimingRowProps } from "./types";

export function TimingRow({ rank, name, value, pct, tone = "flat", iconSrc, delta }: TimingRowProps) {
  const toneColour = { best: "var(--f1-best)", ahead: "var(--f1-ahead)", flat: "var(--f1-flat)", alert: "var(--f1-alert)" }[tone];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "34px 1fr auto", gap: 12, alignItems: "center", padding: "10px 0", borderTop: "1px solid var(--liv-line)" }}>
      {iconSrc ? (
        <img src={iconSrc} alt="" width={28} height={28} style={{ borderRadius: 6, objectFit: "cover" }} />
      ) : (
        <span style={{ fontFamily: "ui-monospace, monospace", fontSize: 12, color: "var(--liv-text-dim)", borderLeft: `2px solid ${toneColour}`, paddingLeft: 6 }}>{rank}</span>
      )}
      <div>
        <div style={{ fontSize: 13, color: "var(--liv-text)" }}>{name}</div>
        {typeof pct === "number" && (
          <div style={{ height: 4, marginTop: 6, borderRadius: 999, background: "var(--liv-bg-2)", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, pct))}%`, background: toneColour }} />
          </div>
        )}
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontFamily: "ui-monospace, monospace", fontVariantNumeric: "tabular-nums", fontSize: 12, color: "var(--liv-text)" }}>{value}</div>
        {delta && <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 10, color: "var(--liv-text-dim)" }}>{delta}</div>}
      </div>
    </div>
  );
}
