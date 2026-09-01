"use client";
import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import { useFinanceData } from "@/lib/api";
import { inr, num, pct } from "@/lib/format";
import type { RidgeMode } from "@/components/finance/three/NetWorthRidge";
import type { NetWorthData } from "@/lib/types";

const NetWorthRidge = dynamic(() => import("@/components/finance/three/NetWorthRidge"), {
  ssr: false,
  loading: () => null,
});

function Ministat({ label, value, cls }: { label: string; value: string; cls: string }) {
  return (
    <div className="text-right">
      <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">{label}</div>
      <div className={`mt-[3px] font-mono text-[15px] ${cls}`}>{value}</div>
    </div>
  );
}

export default function NetWorthCard() {
  const { data, isLoading, error } = useFinanceData<NetWorthData>("/overview/net-worth");
  // Label the panel with the renderer that actually drew, not the one we hoped
  // for — the SVG path is what reduced-motion and no-WebGL viewers see.
  const [ridge, setRidge] = useState<RidgeMode | null>(null);
  const onMode = useCallback((mode: RidgeMode) => setRidge(mode), []);

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
            </div>
            <div className="flex gap-6">
              <Ministat label="Assets" value={inr(data.assets)} cls="pos" />
              <Ministat label="Liabilities" value={inr(data.liabilities)} cls="neg" />
              <Ministat label="All-time" value={pct(data.all_time_pct)} cls="goldc" />
            </div>
          </div>

          <div className="mt-3.5 flex items-end gap-4">
            <div className="value-hero">
              <span className="cur">₹</span>
              {num(data.net_worth)}
            </div>
            {data.month_change_pct !== null && (
              <div className={`delta ${data.month_change_pct >= 0 ? "up" : "down"}`}>
                {data.month_change_pct >= 0 ? "▲" : "▼"} {pct(data.month_change_pct, 1)} this
                month
              </div>
            )}
          </div>

          <div className="pointer-events-none absolute right-[22px] top-[64px] text-right">
            <div className="footnote">SOLID = ACTUAL · DOTTED = 12-MO PROJECTION</div>
          </div>

          {/* full-bleed: the ridge runs to the panel edges, under the numbers */}
          <div className="pointer-events-auto absolute inset-x-0 bottom-0 h-[150px]">
            <NetWorthRidge
              trend={(data.trend ?? []).map((t) => t.net_worth)}
              projection={(data.projection ?? []).map((p) => p.net_worth)}
              onMode={onMode}
            />
          </div>
        </>
      )}
    </section>
  );
}
