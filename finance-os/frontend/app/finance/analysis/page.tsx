"use client";
import { useEffect, useState } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData } from "@/lib/api";
import { inr, inrCompact, num, pct } from "@/lib/format";
import { invalidateCache } from "@/lib/api";

// The Analysis tab — how a portfolio manager reads EVERY fund together:
// the look-through X-ray, pair overlap, behaviour vs the index, the blend's
// cost, allocation vs targets, the tax picture, and the fact-based action
// list. Every panel is one honest section of /analysis/* — coverage gaps
// are named, never papered over. Advisory-neutral by construction: facts
// and thresholds, no buy/sell advice (Finance house rule).

interface Overview {
  state: string; total_value: number; invested: number; gain_loss: number;
  xirr_pct: number | null; funds_with_portfolio: number; holdings: number;
  portfolio_coverage_pct: number; unpriced: string[];
  settings_verified_by_a_person: boolean;
}
interface Look {
  state: string; reason?: string; coverage_pct: number;
  companies: { company: string; weight_pct: number; sector?: string | null }[];
  distinct_companies: number; hhi: number;
  effective_number_of_stocks: number | null; top10_weight_pct: number;
  sectors: { sector: string; weight_pct: number }[];
}
interface OverlapPair {
  a: string; b: string; overlap_pct: number; bucket: string;
  shared_companies: number;
}
interface Overlap {
  state: string; reason?: string;
  symbols: { symbol: string; name: string }[];
  matrix: Record<string, Record<string, number | null>>;
  pairs: OverlapPair[];
}
interface Behaviour {
  state: string;
  benchmark: { name: string; return_1y_pct: number | null; volatility_pct: number | null };
  portfolio: { has_data?: boolean; return_1y_pct?: number | null; volatility_pct?: number | null;
    beta?: number | null; alpha_pct?: number | null; sharpe?: number | null;
    sortino?: number | null; max_drawdown_pct?: number | null; note?: string };
  funds: { symbol: string; name: string; weight_pct: number; has_data: boolean;
    return_1y_pct?: number | null; volatility_pct?: number | null; beta?: number | null;
    alpha_pct?: number | null; sharpe?: number | null; max_drawdown_pct?: number | null }[];
}
interface Allocation {
  state: string;
  split: { bucket: string; value: number; weight_pct: number }[];
  targets: Record<string, number>;
  targets_verified_by_a_person: boolean;
  drift: { bucket: string; target_pct: number; actual_pct: number;
    drift_pp: number; flag: boolean }[];
}
interface CostTax {
  blended_expense_ratio_pct: number | null;
  regular_plan_total_pct: number | null;
  funds: { symbol: string; name: string; expense_ratio_pct: number | null;
    plan_type: string; weight_pct: number }[];
  totals: { stcg_unrealised: number; ltcg_unrealised: number };
  rates: Record<string, unknown>; note?: string;
}
interface Actions {
  state: string;
  observations: { flag: string; severity: string; symbol?: string; detail: string }[];
}

function useSection<T>(path: string) {
  return useFinanceData<T>(path);
}

function Section({ n, title, sub, children }: {
  n: string; title: string; sub?: string; children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="mb-3 flex items-baseline gap-3">
        <span className="font-mono text-[11px] text-aurum-gold">{n}</span>
        <h2 className="font-serif text-[19px] text-aurum-text">{title}</h2>
        {sub ? <span className="footnote">{sub}</span> : null}
      </div>
      {children}
    </section>
  );
}

const SEV_CLS: Record<string, string> = {
  flag: "chip r", watch: "chip g", info: "chip",
};

export default function AnalysisPage() {
  const ov = useSection<Overview>("/analysis/overview");
  const look = useSection<Look>("/analysis/lookthrough");
  const ovlp = useSection<Overlap>("/analysis/overlap");
  const beh = useSection<Behaviour>("/analysis/behaviour");
  const alloc = useSection<Allocation>("/analysis/allocation");
  const ct = useSection<CostTax>("/analysis/cost-tax");
  const act = useSection<Actions>("/analysis/actions");
  const [refreshing, setRefreshing] = useState(false);

  async function refresh() {
    setRefreshing(true);
    try {
      await fetch("/api/finance/analysis/refresh", { method: "POST" });
      // the job runs in the background — give it a beat, then reload panels
      await new Promise((r) => setTimeout(r, 2500));
      invalidateCache();
      for (let i = 0; i < 20; i++) {
        const s = await fetch("/api/finance/analysis/refresh/status").then((r) => r.json());
        if (s?.state === "ok" || s?.state === "error") break;
        await new Promise((r) => setTimeout(r, 3000));
      }
      invalidateCache();
    } finally {
      setRefreshing(false);
    }
  }

  const heat = (v: number | null) => {
    if (v == null) return "bg-white/[.03]";
    const intensity = Math.min(1, v / 80);
    return `rgba(228,192,124,${(0.06 + intensity * 0.5).toFixed(2)})`;
  };
  const bucketLabel = (v: number) =>
    v > 80 ? "extreme" : v > 60 ? "significant" : v >= 20 ? "moderate" : "low";

  const data = ov.data;
  return (
    <div className="space-y-4">
      {/* header row */}
      <Section n="§0" title="The whole-portfolio read" sub="EVERY SECTION IS COMPUTED FROM YOUR LEDGER + PUBLISHED FUND DATA">
        <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
          <div>
            <div className="value-hero !text-[44px]">
              <span className="cur">₹</span>{num(data?.total_value ?? 0)}
            </div>
            {data && (
              <div className={`delta ${data.gain_loss >= 0 ? "up" : "down"} mt-2`}>
                {data.gain_loss >= 0 ? "▲" : "▼"} {inr(data.gain_loss)} all-time
              </div>
            )}
          </div>
          <div className="grid flex-1 grid-cols-2 gap-4 md:grid-cols-4">
            {[
              ["Invested", inr(data?.invested ?? 0)],
              ["XIRR", data?.xirr_pct == null ? "needs lots" : `${num(data.xirr_pct, 1)}%`],
              ["Holdings", String(data?.holdings ?? "—")],
              ["X-ray coverage", data ? `${num(data.portfolio_coverage_pct, 0)}%` : "—"],
            ].map(([k, v]) => (
              <div key={k} className="rounded-xl border border-white/[.06] bg-white/[.02] p-3">
                <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">{k}</div>
                <div className="mt-1 font-mono text-[16px] text-aurum-text">{v}</div>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button className="chip g disabled:opacity-50" disabled={refreshing} onClick={refresh}>
              {refreshing ? "REFRESHING…" : "REFRESH FUND DATA"}
            </button>
          </div>
        </div>
        {data && data.portfolio_coverage_pct < 100 && (
          <p className="footnote mt-3">
            X-RAY COVERS {num(data.portfolio_coverage_pct, 0)}% OF VALUE — FUNDS WITHOUT A PUBLISHED
            PORTFOLIO (OR REFERENCE PAGE) ARE REPORTED BUT NOT X-RAYED. HIT &quot;REFRESH FUND DATA&quot;
            AFTER ADDING A FUND.
          </p>
        )}
        {data?.settings_verified_by_a_person === false && (
          <p className="footnote mt-2">
            TARGETS AND THE RISK-FREE RATE ARE SETTINGS-FILE DEFAULTS NOBODY HAS CONFIRMED YET —
            THE [UNVERIFIED] TAG TRAVELS WITH EVERY NUMBER BUILT ON THEM.
          </p>
        )}
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* look-through */}
        <div className="lg:col-span-7">
          <Section n="§1" title="The X-ray — what you really own" sub="LOOK-THROUGH ACROSS EVERY PUBLISHED PORTFOLIO">
            {!look.data || look.data.state !== "ok" ? (
              <p className="text-sm text-aurum-muted">{look.data?.reason ?? "Loading…"}</p>
            ) : (
              <>
                <div className="mb-3 grid grid-cols-3 gap-3">
                  {[
                    ["Companies", String(look.data.distinct_companies)],
                    ["Behaves like", `${num(look.data.effective_number_of_stocks, 0)} stocks`],
                    ["Top 10 hold", `${num(look.data.top10_weight_pct, 1)}%`],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-xl border border-white/[.06] bg-white/[.02] p-3">
                      <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">{k}</div>
                      <div className="mt-1 font-mono text-[16px] text-aurum-text">{v}</div>
                    </div>
                  ))}
                </div>
                <div className="space-y-1.5">
                  {look.data.companies.slice(0, 12).map((c) => (
                    <div key={c.company} className="flex items-center gap-3">
                      <span className="w-56 truncate text-[12.5px] text-aurum-text">{c.company}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[.05]">
                        <div className="h-full rounded-full bg-aurum-gold/70"
                             style={{ width: `${Math.min(100, (c.weight_pct / (look.data!.companies[0].weight_pct || 1)) * 100)}%` }} />
                      </div>
                      <span className="w-14 text-right font-mono text-[12px] text-aurum-muted">
                        {num(c.weight_pct, 2)}%
                      </span>
                    </div>
                  ))}
                </div>
                <p className="footnote mt-2">
                  SECTORS: {look.data.sectors.slice(0, 5)
                    .map((s) => `${s.sector} ${num(s.weight_pct, 1)}%`).join(" · ")}
                </p>
              </>
            )}
          </Section>
        </div>

        {/* allocation + drift */}
        <div className="lg:col-span-5">
          <Section n="§2" title="Allocation vs targets" sub="±5pp = WORTH NAMING">
            {!alloc.data || alloc.data.state !== "ok" ? (
              <p className="text-sm text-aurum-muted">Loading…</p>
            ) : (
              <>
                <div className="space-y-2">
                  {alloc.data.split.map((s) => (
                    <div key={s.bucket} className="flex items-center gap-3">
                      <span className="w-24 text-[12px] capitalize text-aurum-text">{s.bucket.replace("_", " ")}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/[.05]">
                        <div className="h-full rounded-full bg-aurum-gold/70"
                             style={{ width: `${s.weight_pct}%` }} />
                      </div>
                      <span className="w-12 text-right font-mono text-[12px] text-aurum-muted">{num(s.weight_pct, 1)}%</span>
                    </div>
                  ))}
                </div>
                <table className="mt-4 w-full text-[12px]">
                  <thead>
                    <tr className="text-left text-aurum-faint">
                      <th className="py-1 font-medium">Class</th>
                      <th className="py-1 text-right font-medium">Actual</th>
                      <th className="py-1 text-right font-medium">Target</th>
                      <th className="py-1 text-right font-medium">Drift</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alloc.data.drift.map((d) => (
                      <tr key={d.bucket} className="border-t border-white/[.05]">
                        <td className="py-1.5 capitalize text-aurum-text">{d.bucket}</td>
                        <td className="py-1.5 text-right font-mono text-aurum-text">{num(d.actual_pct, 1)}%</td>
                        <td className="py-1.5 text-right font-mono text-aurum-muted">{num(d.target_pct, 0)}%</td>
                        <td className={`py-1.5 text-right font-mono ${d.flag ? "text-aurum-amber" : "text-aurum-muted"}`}>
                          {d.drift_pp >= 0 ? "+" : ""}{num(d.drift_pp, 1)}pp
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="footnote mt-2">
                  TARGETS ARE SETTINGS DEFAULTS [UNVERIFIED] — EDIT reference/fund_analysis_settings.json
                  AND FLIP verified_by_a_person WHEN THEY ARE REALLY YOURS.
                </p>
              </>
            )}
          </Section>
        </div>

        {/* overlap matrix */}
        <div className="lg:col-span-7">
          <Section n="§3" title="Fund overlap" sub="Σ MIN(WEIGHTS) OVER SHARED COMPANIES">
            {!ovlp.data || ovlp.data.state !== "ok" ? (
              <p className="text-sm text-aurum-muted">{ovlp.data?.reason ?? "Loading…"}</p>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="text-[11px]">
                    <thead>
                      <tr>
                        <th className="p-1" />
                        {ovlp.data.symbols.map((s) => (
                          <th key={s.symbol} className="p-1 text-right font-medium text-aurum-faint">
                            {s.name.split(" ").slice(0, 2).join(" ")}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ovlp.data.symbols.map((a) => (
                        <tr key={a.symbol}>
                          <td className="whitespace-nowrap p-1 pr-3 text-aurum-muted">
                            {a.name.split(" ").slice(0, 2).join(" ")}
                          </td>
                          {ovlp.data!.symbols.map((b) => {
                            const v = ovlp.data!.matrix[a.symbol]?.[b.symbol] ?? null;
                            return (
                              <td key={b.symbol}
                                  className="p-1 text-right font-mono"
                                  style={{ background: a.symbol === b.symbol ? "rgba(255,255,255,.03)" : heat(v) }}>
                                <span className={v != null && v > 60 ? "text-aurum-text" : "text-aurum-muted"}>
                                  {v == null ? "—" : num(v, 0)}
                                </span>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 space-y-1">
                  {ovlp.data.pairs.slice(0, 4).map((p, i) => (
                    <p key={i} className="text-[12px] text-aurum-muted">
                      <span className="text-aurum-text">{p.a}</span> ↔ {p.b}:{" "}
                      <span className={`font-mono ${p.overlap_pct > 60 ? "text-aurum-gold" : ""}`}>
                        {num(p.overlap_pct, 1)}%
                      </span>{" "}
                      <span className="text-aurum-faint">({p.bucket} · {p.shared_companies} shared names)</span>
                    </p>
                  ))}
                </div>
                <p className="footnote mt-2">READ: 40%+ OVERLAP = TWO FUNDS RIDING MANY OF THE SAME COMPANIES.</p>
              </>
            )}
          </Section>
        </div>

        {/* behaviour */}
        <div className="lg:col-span-5">
          <Section n="§4" title="Behaviour vs the index" sub={`RISK RATIOS · vs ${beh.data?.benchmark.name ?? "NIFTY 50"}`}>
            {!beh.data || beh.data.state === "pending" ? (
              <p className="text-sm text-aurum-muted">Not enough ledger history yet.</p>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2.5">
                  {[
                    ["Portfolio 1Y", pct(beh.data.portfolio.return_1y_pct)],
                    ["Volatility", pct(beh.data.portfolio.volatility_pct)],
                    ["Beta", beh.data.portfolio.beta == null ? "—" : num(beh.data.portfolio.beta, 2)],
                    ["Alpha", pct(beh.data.portfolio.alpha_pct)],
                    ["Sharpe", beh.data.portfolio.sharpe == null ? "—" : num(beh.data.portfolio.sharpe, 2)],
                    ["Max drawdown", pct(beh.data.portfolio.max_drawdown_pct)],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
                      <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">{k}</div>
                      <div className="mt-0.5 font-mono text-[15px] text-aurum-text">{v}</div>
                    </div>
                  ))}
                </div>
                <p className="footnote mt-2">
                  BENCHMARK 1Y {pct(beh.data.benchmark.return_1y_pct)} · VOL {pct(beh.data.benchmark.volatility_pct)}
                </p>
                <div className="mt-3 max-h-44 space-y-1 overflow-y-auto pr-1">
                  {beh.data.funds.filter((f) => f.has_data).map((f) => (
                    <div key={f.symbol} className="flex items-center justify-between border-t border-white/[.05] py-1 text-[11.5px]">
                      <span className="truncate pr-2 text-aurum-muted">{f.name}</span>
                      <span className="font-mono text-aurum-text">
                        1Y {pct(f.return_1y_pct)} · β {f.beta == null ? "—" : num(f.beta, 2)}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Section>
        </div>

        {/* cost & tax */}
        <div className="lg:col-span-7">
          <Section n="§5" title="Cost & tax" sub="WHAT THE BLEND COSTS · WHERE GAINS SIT">
            {ct.data && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="mb-2 grid grid-cols-2 gap-2.5">
                    <div className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
                      <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">Blended TER</div>
                      <div className="mt-0.5 font-mono text-[16px] text-aurum-text">
                        {ct.data.blended_expense_ratio_pct == null
                          ? "—" : `${num(ct.data.blended_expense_ratio_pct, 2)}%`}
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
                      <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">In regular plans</div>
                      <div className="mt-0.5 font-mono text-[16px] text-aurum-text">
                        {ct.data.regular_plan_total_pct == null
                          ? "—" : `${num(ct.data.regular_plan_total_pct, 0)}%`}
                      </div>
                    </div>
                  </div>
                  <div className="max-h-40 space-y-0.5 overflow-y-auto pr-1">
                    {ct.data.funds.map((f) => (
                      <div key={f.symbol} className="flex items-center justify-between border-t border-white/[.05] py-1 text-[11.5px]">
                        <span className="truncate pr-2 text-aurum-muted">{f.name}</span>
                        <span className="font-mono text-aurum-text">
                          {f.expense_ratio_pct == null ? "—" : `${num(f.expense_ratio_pct, 2)}%`}
                          <span className="ml-1.5 text-[9px] uppercase text-aurum-faint">{f.plan_type}</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  {ct.data.note ? (
                    <p className="text-[12px] leading-relaxed text-aurum-muted">
                      {ct.data.note}
                    </p>
                  ) : (
                    <>
                      <div className="mb-2 grid grid-cols-2 gap-2.5">
                        <div className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
                          <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">Unrealised STCG</div>
                          <div className="mt-0.5 font-mono text-[15px] text-aurum-text">
                            {inr(ct.data.totals.stcg_unrealised)}
                          </div>
                        </div>
                        <div className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
                          <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">Unrealised LTCG</div>
                          <div className="mt-0.5 font-mono text-[15px] text-aurum-emerald">
                            {inr(ct.data.totals.ltcg_unrealised)}
                          </div>
                        </div>
                      </div>
                      <p className="footnote">
                        FROM RECORDED LOTS · STCG 20% / LTCG 12.5% ABOVE ₹1.25L (EQUITY, FY{" "}
                        {String(ct.data.rates.financial_year ?? "?")}).
                      </p>
                    </>
                  )}
                </div>
              </div>
            )}
          </Section>
        </div>

        {/* actions */}
        <div className="lg:col-span-5">
          <Section n="§6" title="What a reviewer would flag" sub="FACTS + THRESHOLDS — NEVER ORDERS">
            {!act.data ? (
              <p className="text-sm text-aurum-muted">Loading…</p>
            ) : (
              <div className="space-y-2">
                {act.data.observations.length === 0 && (
                  <p className="text-sm text-aurum-muted">No threshold crossed. That is a fact, not a guarantee.</p>
                )}
                {act.data.observations.map((o, i) => (
                  <div key={i} className="rounded-xl border border-white/[.06] bg-white/[.02] p-3">
                    <span className={SEV_CLS[o.severity] ?? "chip"}>{o.flag.replace(/_/g, " ")}</span>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-aurum-text">{o.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
