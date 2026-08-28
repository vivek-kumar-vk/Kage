"use client";

import type { CSSProperties } from "react";

/** PROTOTYPE — sample F1-feel content, judged once per livery. Colours only via
    var(--liv-*) / var(--f1-*), set by the .liv-* ancestor. Deleted in Phase 5. */

const SERIES = [180, 176, 190, 205, 198, 214, 222, 219, 231, 228, 236, 240];

function sparkPaths(series: number[]) {
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const pts = series.map((v, i) => {
    const x = (i * 240) / (series.length - 1);
    const y = 54 - ((v - min) / span) * 48;
    return [x, y] as const;
  });
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  return { line, area: `${line} L240,60 L0,60 Z` };
}

const card: CSSProperties = {
  background: "var(--liv-surface)",
  border: "1px solid var(--liv-line)",
  borderRadius: 14,
  padding: 20,
  position: "relative",
};

const label: CSSProperties = {
  color: "var(--liv-text-dim)",
  fontSize: 11,
  letterSpacing: 1.5,
  textTransform: "uppercase",
  marginBottom: 8,
};

const num: CSSProperties = {
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  fontVariantNumeric: "tabular-nums",
};

const ThemeLabStage = () => {
  const { line, area } = sparkPaths(SERIES);
  return (
    <div
      style={{
        position: "relative",
        zIndex: 1,
        maxWidth: 920,
        margin: "0 auto",
        padding: 32,
        display: "grid",
        gridTemplateColumns: "160px 1fr",
        gap: 20,
      }}
    >
      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {["Overview", "Investments", "Debt", "Portfolio"].map((t, i) => (
          <div
            key={t}
            style={{
              padding: "8px 12px",
              fontSize: 14,
              color: i === 0 ? "var(--liv-text)" : "var(--liv-text-dim)",
              borderLeft: `2px solid ${i === 0 ? "var(--liv-accent)" : "transparent"}`,
              background: i === 0 ? "var(--liv-surface)" : "transparent",
            }}
          >
            {t}
          </div>
        ))}
      </nav>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ ...card }} className="livery-edge">
          <div style={label}>Total Balance</div>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
            <div style={{ ...num, fontSize: 34, fontWeight: 700, color: "var(--liv-text)" }}>₹1,50,000</div>
            <div style={{ ...num, fontSize: 13, color: "var(--f1-ahead)" }}>▲ 4.2%</div>
          </div>
          <svg viewBox="0 0 240 60" style={{ width: "100%", height: 60, marginTop: 12, display: "block" }}>
            <path d={area} fill="var(--liv-accent)" fillOpacity={0.15} />
            <path d={line} fill="none" stroke="var(--liv-accent)" strokeWidth={2} />
          </svg>
        </div>

        <div style={{ ...card }} className="livery-edge">
          <div style={label}>Savings Rate</div>
          <div style={{ height: 10, borderRadius: 999, background: "var(--liv-bg-2)", overflow: "hidden" }}>
            <div style={{ height: "100%", width: "68%", borderRadius: 999, background: "var(--liv-accent)", boxShadow: "0 0 12px var(--liv-glow)" }} />
          </div>
          <div style={{ ...num, color: "var(--liv-text-dim)", fontSize: 12, marginTop: 8 }}>68% of income kept</div>
        </div>

        <div style={{ ...card }} className="livery-edge">
          <div style={label}>Goals — timing tower</div>
          {[
            ["01", "Emergency fund", "₹1,80,000 / ₹3,00,000", 60, "var(--f1-ahead)"],
            ["02", "Japan trip", "₹90,000 / ₹2,00,000", 45, "var(--f1-flat)"],
            ["03", "New laptop", "₹1,10,000 / ₹1,20,000", 92, "var(--f1-best)"],
          ].map(([rank, name, val, pct, tone]) => (
            <div key={rank as string} style={{ display: "grid", gridTemplateColumns: "28px 1fr auto", gap: 12, alignItems: "center", padding: "8px 0", borderTop: "1px solid var(--liv-line)" }}>
              <span style={{ ...num, fontSize: 12, color: "var(--liv-text-dim)", borderLeft: `2px solid ${tone as string}`, paddingLeft: 6 }}>{rank}</span>
              <div>
                <div style={{ fontSize: 13, color: "var(--liv-text)" }}>{name}</div>
                <div style={{ height: 4, marginTop: 5, borderRadius: 999, background: "var(--liv-bg-2)", overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${pct}%`, background: tone as string }} />
                </div>
              </div>
              <span style={{ ...num, fontSize: 11, color: "var(--liv-text-dim)" }}>{val}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ThemeLabStage;
