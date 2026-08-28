import type { StatDialProps } from "./types";

export function StatDial({ pct, value, label, size = 128 }: StatDialProps) {
  const p = Math.max(0, Math.min(100, pct));
  const c = size / 2;
  const r = c - 8;
  const C = 2 * Math.PI * r;

  return (
    <svg width={size} height={size} style={{ display: "block" }}>
      <circle cx={c} cy={c} r={r} fill="none" stroke="var(--liv-line)" strokeWidth={8} />
      <circle
        cx={c}
        cy={c}
        r={r}
        fill="none"
        stroke="var(--liv-accent)"
        strokeWidth={8}
        strokeLinecap="round"
        strokeDasharray={C}
        strokeDashoffset={C * (1 - p / 100)}
        transform={`rotate(-90 ${c} ${c})`}
      />
      <text
        x={c}
        y={c}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="var(--liv-text)"
        style={{ fontFamily: "ui-monospace, monospace", fontVariantNumeric: "tabular-nums", fontSize: size * 0.2 }}
      >
        {value ?? `${Math.round(p)}%`}
      </text>
      {label && (
        <text
          x={c}
          y={c + size * 0.18}
          textAnchor="middle"
          fill="var(--liv-text-dim)"
          style={{ fontFamily: "ui-monospace, monospace", fontSize: size * 0.1 }}
        >
          {label}
        </text>
      )}
    </svg>
  );
}
