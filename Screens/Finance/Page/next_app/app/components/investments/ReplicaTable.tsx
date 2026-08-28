import { REPLICA_HOLDINGS } from "@/app/lib/replicaHoldings";
import { formatINR } from "@/app/lib/formatINR";

export function ReplicaTable() {
  return (
    <div className="scroll-x">
      <table style={{ width: "100%", minWidth: 720, borderCollapse: "collapse", fontFamily: "ui-monospace, monospace", fontVariantNumeric: "tabular-nums", fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>Fund</th>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>Units</th>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>Invested</th>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>Current</th>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>Gain</th>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>Gain %</th>
            <th style={{ padding: "8px 10px", color: "var(--liv-text-dim)", borderBottom: "1px solid var(--liv-line)", fontWeight: 400, letterSpacing: 1 }}>NAV</th>
          </tr>
        </thead>
        <tbody>
          {REPLICA_HOLDINGS.map((h) => (
            <tr key={h.name} style={{ borderBottom: "1px solid var(--liv-line)" }}>
              <td style={{ padding: "8px 10px", color: "var(--liv-text)" }}>{h.name}</td>
              <td style={{ padding: "8px 10px", color: "var(--liv-text)", textAlign: "right" }}>
                <input readOnly defaultValue={h.units} style={{ width: 80, textAlign: "right", background: "transparent", border: "none", borderBottom: "1px dashed var(--liv-line)", color: "var(--liv-text)", font: "inherit" }} />
              </td>
              <td style={{ padding: "8px 10px", color: "var(--liv-text-dim)", textAlign: "right" }}>{formatINR(h.invested)}</td>
              <td style={{ padding: "8px 10px", color: "var(--liv-text)", textAlign: "right" }}>
                <input readOnly defaultValue={Math.round(h.current)} style={{ width: 90, textAlign: "right", background: "transparent", border: "none", borderBottom: "1px dashed var(--liv-line)", color: "var(--liv-text)", font: "inherit" }} />
              </td>
              <td style={{ padding: "8px 10px", color: h.gainAbs >= 0 ? "var(--f1-ahead)" : "var(--liv-neg)", textAlign: "right" }}>{formatINR(h.gainAbs)}</td>
              <td style={{ padding: "8px 10px", color: h.gainAbs >= 0 ? "var(--f1-ahead)" : "var(--liv-neg)", textAlign: "right" }}>{`${h.gainPct}%`}</td>
              <td style={{ padding: "8px 10px", color: h.navStatus === "fresh2d" ? "var(--f1-ahead)" : "var(--liv-text-dim)", textAlign: "right" }}>
                <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, border: `1px solid ${h.navStatus === "fresh2d" ? "var(--f1-ahead)" : "var(--liv-text-dim)"}`, color: h.navStatus === "fresh2d" ? "var(--f1-ahead)" : "var(--liv-text-dim)" }}>{h.navStatus === "fresh2d" ? "2D" : "\u2014"}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button type="button" style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid var(--liv-line)", background: "var(--liv-surface)", color: "var(--liv-text-dim)", fontFamily: "ui-monospace, monospace", fontSize: 12, cursor: "pointer" }}>Analysis</button>
        <button type="button" style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid var(--liv-line)", background: "var(--liv-surface)", color: "var(--liv-text-dim)", fontFamily: "ui-monospace, monospace", fontSize: 12, cursor: "pointer" }}>Save</button>
        <button type="button" style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid var(--liv-line)", background: "var(--liv-surface)", color: "var(--liv-text-dim)", fontFamily: "ui-monospace, monospace", fontSize: 12, cursor: "pointer" }}>Delete</button>
      </div>
    </div>
  );
}
