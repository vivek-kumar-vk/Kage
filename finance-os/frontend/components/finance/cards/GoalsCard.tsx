"use client";
import { useFinanceData } from "@/lib/api";
import { inrCompact, monthLabel, num } from "@/lib/format";
import type { GoalsOverviewData } from "@/lib/types";

const BARS = [
  "linear-gradient(90deg,#E4C07C,#F5DCA4)",
  "linear-gradient(90deg,#8B93FF,#A9AFFF)",
  "linear-gradient(90deg,#6BE1FF,#9BEAFF)",
];

export default function GoalsCard() {
  const { data, isLoading, error } = useFinanceData<GoalsOverviewData>("/overview/goals");
  const goals = data?.goals ?? [];
  const monteCarlo = goals.some((g) => g.probability_source === "monte-carlo");

  return (
    <section className="panel flex h-full min-h-[262px] flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">
            Goals <span className="tag dim">{data.count} active</span>
          </div>

          {goals.length === 0 ? (
            <p className="mt-6 text-xs text-aurum-muted">
              No active goals — add one to see funding probability.
            </p>
          ) : (
            goals.slice(0, 3).map((g, i) => (
              <div key={g.id} className="mt-4">
                <div className="mb-[7px] flex items-baseline justify-between gap-3">
                  <span className="truncate text-[13px] font-medium">{g.name}</span>
                  <span className="shrink-0 font-mono text-[11.5px] text-aurum-muted">
                    {inrCompact(g.current_amount)} / {inrCompact(g.target_amount)}
                  </span>
                </div>
                <div className="track">
                  <div
                    className="fill"
                    style={{
                      width: `${Math.min(g.progress, 1) * 100}%`,
                      background: BARS[i % BARS.length],
                    }}
                  />
                </div>
                <div className="mt-1.5 flex justify-between font-mono text-[10px] text-aurum-faint">
                  <span>{g.target_date ? monthLabel(g.target_date) : "NO TARGET DATE"}</span>
                  <span className="goldc">
                    PROBABILITY {num(g.probability, 0)}%
                    {g.probability_source === "heuristic" ? " ·EST" : ""}
                  </span>
                </div>
              </div>
            ))
          )}

          <div className="footnote mt-auto pt-3.5">
            {monteCarlo
              ? `MONTE-CARLO 10K RUNS · ${num(data.assumed_return_pct, 1)}% RETURN · ${num(
                  data.assumed_vol_pct,
                  1
                )}% VOL`
              : "NO DATED GOALS — SHOWING PROGRESS ESTIMATE, NOT A SIMULATION"}
          </div>
        </>
      )}
    </section>
  );
}
