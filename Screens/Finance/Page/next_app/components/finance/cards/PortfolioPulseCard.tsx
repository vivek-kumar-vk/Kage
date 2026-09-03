"use client";
import { useFinanceData } from "@/lib/api";
import { num, pct } from "@/lib/format";
import type { PortfolioPulseData } from "@/lib/types";

function PulseSparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null;
  const W = 460;
  const H = 120;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const coords = points.map(
    (p, i) => [(i / (points.length - 1)) * W, H - 8 - ((p - min) / range) * (H - 24)] as const
  );
  const line = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");
  const area = `${line} L${W},${H} L0,${H} Z`;
  const [lx, ly] = coords[coords.length - 1];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 h-[110px] w-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id="au-pfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8B93FF" stopOpacity=".3" />
          <stop offset="1" stopColor="#8B93FF" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#au-pfill)" />
      <path d={line} fill="none" stroke="#8B93FF" strokeWidth="2" />
      <circle cx={lx} cy={ly} r="4" fill="#8B93FF" />
      <line x1="0" y1={H - 8} x2={W} y2={H - 8} stroke="rgba(255,255,255,.08)" strokeDasharray="2 5" />
    </svg>
  );
}

export default function PortfolioPulseCard() {
  const { data, isLoading, error } = useFinanceData<PortfolioPulseData>("/overview/portfolio-pulse");

  // A series of zeros with today's value tacked on is an artifact of missing
  // lots, not a trend — don't draw a cliff and call it history.
  const points = (data?.history ?? []).map((h) => h.value);
  const distinct = new Set(points.filter((v) => v > 0)).size;

  return (
    <section className="panel flex h-full min-h-[280px] flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">
            Portfolio Pulse <span className="tag dim">today</span>
          </div>
          <div className="mt-3 flex items-baseline gap-3">
            <div className="value-lg">
              <span className="cur">₹</span>
              {num(data.total_value)}
            </div>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {data.day_change !== null ? (
              <div className={`delta ${data.day_change >= 0 ? "up" : "down"}`}>
                {data.day_change >= 0 ? "▲" : "▼"} ₹{num(Math.abs(data.day_change))}
                {data.day_change_pct !== null ? ` (${pct(data.day_change_pct, 2)})` : ""}
              </div>
            ) : (
              <div className="delta gold">day change pending prices</div>
            )}
            {data.xirr_pct !== null && <div className="delta gold">XIRR {pct(data.xirr_pct, 1)}</div>}
          </div>
          {distinct >= 3 ? (
            <PulseSparkline points={points} />
          ) : (
            <p className="mt-4 text-[11.5px] leading-[1.5] text-aurum-muted">
              No value history to plot yet — snapshots price past months from
              purchase lots, and none are recorded. Import a CAS with lot detail
              to fill the curve.
            </p>
          )}
          <div className="mt-auto">
            <div className="aurum-row">
              <span className="k">Holdings</span>
              <span className="v">
                {data.holdings_count} across {data.asset_classes} asset{" "}
                {data.asset_classes === 1 ? "class" : "classes"}
              </span>
            </div>
            <div className="aurum-row">
              <span className="k">Best today</span>
              <span className={`v ${data.best_today ? "pos" : ""}`}>
                {data.best_today
                  ? `${data.best_today.name} · ${data.best_today.change_pct >= 0 ? "+" : ""}${data.best_today.change_pct}%`
                  : "—"}
              </span>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
