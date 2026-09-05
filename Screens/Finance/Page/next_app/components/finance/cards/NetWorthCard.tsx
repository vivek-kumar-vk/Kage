"use client";
import dynamic from "next/dynamic";
import { useCallback, useMemo, useState } from "react";
import { useFinanceData } from "@/lib/api";
import { inr, num, pct } from "@/lib/format";
import { rebaseBenchmark } from "@/lib/benchmark";
import { useOverviewScope } from "@/lib/useOverviewScope";
import HistoricalMarker from "@/components/finance/HistoricalMarker";
import type { RidgeMode } from "@/components/finance/three/NetWorthRidge";
import type { BenchmarkData, NetWorthData } from "@/lib/types";

const NetWorthRidge = dynamic(() => import("@/components/finance/three/NetWorthRidge"), {
  ssr: false,
  loading: () => null,
});

// Frozen for now — no per-user index setting yet (D28.4, AGENTS.md).
const BENCHMARK_SYMBOL = "^NSEI";

function Ministat({
  label,
  value,
  cls,
}: {
  label: string;
  value: string;
  cls: string;
}) {
  return (
    <div className="text-right">
      <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">{label}</div>
      <div className={`mt-[3px] font-mono text-[15px] ${cls}`}>{value}</div>
    </div>
  );
}

function pctChange(current: number, previous: number): number | null {
  if (previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

export default function NetWorthCard() {
  const scope = useOverviewScope();
  const { data, isLoading, error } = useFinanceData<NetWorthData>("/overview/net-worth");
  // Label the panel with the renderer that actually drew, not the one we hoped
  // for — the SVG path is what reduced-motion and no-WebGL viewers see.
  const [ridge, setRidge] = useState<RidgeMode | null>(null);
  const onMode = useCallback((mode: RidgeMode) => setRidge(mode), []);

  const trend = data?.trend ?? [];
  const fromDate = trend[0]?.date;
  const toDate = trend[trend.length - 1]?.date;
  // The backend endpoint doesn't exist yet (PLAN item 1) — a 404 here renders
  // exactly like state: "empty" (D28.5), never a crash or a fabricated line.
  const benchmarkPath =
    fromDate && toDate
      ? `/market/benchmark?symbol=${BENCHMARK_SYMBOL}&from=${fromDate}&to=${toDate}`
      : "/market/benchmark";
  const { data: benchmarkData, error: benchmarkError } =
    useFinanceData<BenchmarkData>(benchmarkPath);
  const benchmarkState: BenchmarkData["state"] =
    benchmarkError || !benchmarkData ? "empty" : benchmarkData.state;
  const benchmarkName = benchmarkData?.name ?? "the index";

  const selectedIndex = scope.through ? trend.findIndex((t) => t.date === scope.through) : -1;
  const scoped = scope.isHistorical && selectedIndex >= 0;

  const visibleTrendPoints = scoped ? trend.slice(0, selectedIndex + 1) : trend;
  const visibleTrend = visibleTrendPoints.map((t) => t.net_worth);
  const visibleTrendLabels = visibleTrendPoints.map((t) => t.date);
  // A projection from a past month is a fiction — hide it entirely (§3.2).
  const visibleProjectionPoints = scoped ? [] : (data?.projection ?? []);
  const visibleProjection = visibleProjectionPoints.map((p) => p.net_worth);
  const visibleProjectionLabels = visibleProjectionPoints.map((p) => p.month);

  const heroNetWorth = scoped ? trend[selectedIndex].net_worth : data?.net_worth;
  const monthChangePct = scoped
    ? selectedIndex > 0
      ? pctChange(trend[selectedIndex].net_worth, trend[selectedIndex - 1].net_worth)
      : null
    : (data?.month_change_pct ?? null);
  const allTimePct = scoped
    ? trend.length > 0
      ? pctChange(trend[selectedIndex].net_worth, trend[0].net_worth)
      : null
    : (data?.all_time_pct ?? null);

  const benchmarkPointsAll = benchmarkData?.points ?? [];
  const benchmarkPoints = scoped
    ? benchmarkPointsAll.filter((p) => p.date <= (scope.through as string))
    : benchmarkPointsAll;

  const syntheticFull = useMemo(
    () => rebaseBenchmark(trend, benchmarkPoints),
    [trend, benchmarkPoints]
  );
  const synthetic = scoped ? syntheticFull.slice(0, selectedIndex + 1) : syntheticFull;
  const hasBenchmarkLine = synthetic.filter((v) => v !== null).length >= 2;

  const footnoteBase = "SOLID = ACTUAL · DOTTED = 12-MO PROJECTION";

  return (
    <section className="panel hero flex h-full min-h-[280px] flex-col pb-0">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="flex items-start justify-between gap-4">
            <div className="plabel">
              Net Worth
              <span className={`tag ${ridge === "svg" ? "dim" : ""}`}>
                {ridge === "svg" ? "ridge · still" : "3D ridge · three.js"}
              </span>
              {scoped ? <HistoricalMarker label={scope.label} /> : null}
            </div>
            <div className="flex gap-6">
              {scoped ? (
                <>
                  <Ministat label="Assets" value="—" cls="fainttx" />
                  <Ministat label="Liabilities" value="—" cls="fainttx" />
                </>
              ) : (
                <>
                  <Ministat label="Assets" value={inr(data.assets)} cls="pos" />
                  <Ministat label="Liabilities" value={inr(data.liabilities)} cls="neg" />
                </>
              )}
              <Ministat label="All-time" value={pct(allTimePct)} cls="goldc" />
            </div>
          </div>

          <div className="mt-3.5 flex items-end gap-4">
            <div className="value-hero">
              <span className="cur">₹</span>
              {num(heroNetWorth)}
            </div>
            {monthChangePct !== null && (
              <div className={`delta ${monthChangePct >= 0 ? "up" : "down"}`}>
                {monthChangePct >= 0 ? "▲" : "▼"} {pct(monthChangePct, 1)} this month
              </div>
            )}
          </div>

          <div className="pointer-events-none absolute right-[22px] top-[64px] flex flex-col items-end gap-1.5 text-right">
            <div className="footnote">
              {footnoteBase}
              {benchmarkState === "ok" ? ` · FAINT = ${benchmarkName.toUpperCase()}, REBASED` : ""}
            </div>
            {benchmarkState === "partial" && <span className="tag dim">BENCHMARK · PARTIAL</span>}
            {benchmarkState === "empty" && <span className="tag dim">NO BENCHMARK LOADED</span>}
          </div>

          {/* full-bleed: the ridge runs to the panel edges, under the numbers */}
          <div className="pointer-events-auto absolute inset-x-0 bottom-0 h-[150px]">
            <NetWorthRidge
              trend={visibleTrend}
              trendLabels={visibleTrendLabels}
              projection={visibleProjection}
              projectionLabels={visibleProjectionLabels}
              benchmark={hasBenchmarkLine ? synthetic : undefined}
              onMode={onMode}
            />
          </div>
        </>
      )}
    </section>
  );
}
