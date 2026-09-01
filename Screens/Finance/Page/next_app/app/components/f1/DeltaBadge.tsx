import type { DeltaBadgeProps } from "./types";

export function DeltaBadge({ value, tone, title }: DeltaBadgeProps) {
  const colour = { best: "var(--f1-best)", ahead: "var(--f1-ahead)", flat: "var(--f1-flat)", alert: "var(--f1-alert)" }[tone];
  const glyph = tone === "alert" ? "\u25BC" : tone === "flat" ? "\u25AC" : "\u25B2";
  return <span title={title} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontFamily: "ui-monospace, monospace", fontVariantNumeric: "tabular-nums", fontSize: 12, color: colour }}><span aria-hidden>{glyph}</span>{value}</span>;
}
