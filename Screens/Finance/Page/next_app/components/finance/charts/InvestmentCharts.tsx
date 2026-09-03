"use client";
import { useId } from "react";

/**
 * Hand-rolled SVG charts. No chart lib, no framer-motion. Any motion is a CSS
 * class gated by `motion-reduce:`.
 */

function linePath(points: number[], w: number, h: number): string {
  if (points.length < 2) return "";
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  return points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((p - min) / range) * h;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function RollingReturnsLine({ points }: { points: number[] }) {
  const w = 300;
  const h = 80;
  const d = linePath(points, w, h);
  if (!d) return <p className="text-sm text-racing-silver">Not enough points.</p>;
  const zeroBand = points.some((p) => p < 0) && points.some((p) => p >= 0);
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="mt-2 h-20 w-full"
      preserveAspectRatio="none"
      role="img"
      aria-label="Rolling returns"
    >
      {zeroBand && (
        <line x1="0" y1={h / 2} x2={w} y2={h / 2} stroke="#2d2d2d" strokeWidth="1" />
      )}
      <path d={d} fill="none" stroke="#00d2ff" strokeWidth="2" />
    </svg>
  );
}

export function DrawdownArea({ points }: { points: number[] }) {
  const w = 300;
  const h = 80;
  const line = linePath(points, w, h);
  if (!line) return <p className="text-sm text-racing-silver">Not enough points.</p>;
  const area = `${line} L${w} ${h} L0 ${h} Z`;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="mt-2 h-20 w-full"
      preserveAspectRatio="none"
      role="img"
      aria-label="Drawdown"
    >
      <path d={area} fill="#e10600" fillOpacity="0.18" />
      <path d={line} fill="none" stroke="#e10600" strokeWidth="2" />
    </svg>
  );
}

export function AllocationDonut({
  slices,
}: {
  slices: { label: string; weight: number }[];
}) {
  const gid = useId();
  const total = slices.reduce((s, x) => s + x.weight, 0) || 1;
  const colors = ["#00d2ff", "#00ff87", "#f9a800", "#e10600", "#c0c0c0"];
  const r = 40;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 100 100" className="h-28 w-28 motion-reduce:transition-none">
        <g transform="rotate(-90 50 50)">
          {slices.map((s, i) => {
            const frac = s.weight / total;
            const dash = frac * c;
            const el = (
              <circle
                key={`${gid}-${i}`}
                cx="50"
                cy="50"
                r={r}
                fill="none"
                stroke={colors[i % colors.length]}
                strokeWidth="14"
                strokeDasharray={`${dash.toFixed(2)} ${(c - dash).toFixed(2)}`}
                strokeDashoffset={(-offset).toFixed(2)}
              />
            );
            offset += dash;
            return el;
          })}
        </g>
      </svg>
      <ul className="space-y-1 text-xs">
        {slices.map((s, i) => (
          <li key={`${gid}-l-${i}`} className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: colors[i % colors.length] }}
            />
            <span className="text-racing-silver">{s.label}</span>
            <span className="font-mono">{Math.round((s.weight / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
