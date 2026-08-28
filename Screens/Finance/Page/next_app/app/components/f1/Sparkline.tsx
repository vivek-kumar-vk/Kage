import type { SparklineProps } from "./types";

export function Sparkline({ series, height = 60, stroke = "var(--liv-accent)", fill }: SparklineProps) {
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = (max - min) || 1;
  const line = series.map((value, index) => {
    const x = (index * 240) / (series.length - 1);
    const y = (height - 6) - ((value - min) / span) * (height - 12);
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const area = `${line} L240,${height} L0,${height} Z`;

  return (
    <svg viewBox={`0 0 240 ${height}`} style={{ width: "100%", height, display: "block" }}>
      <path d={area} fill={fill || stroke} fillOpacity={0.15} stroke="none" />
      <path d={line} fill="none" stroke={stroke} strokeWidth={2} strokeLinejoin="round" />
    </svg>
  );
}
