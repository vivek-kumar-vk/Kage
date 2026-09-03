"use client";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useFinanceData } from "@/lib/api";
import { inr, inrCompact, num, pct } from "@/lib/format";
import Explainer from "@/components/finance/analyse/Explainer";

// The Analyse drawer — an independent window inside the tab. One holding's
// whole reference sheet: facts, the published portfolio with weights,
// returns, risk ratios vs NIFTY 50, peers, pros/cons, and the explainer.
// Data comes from /investments/analyse/{hid} (funds) or /investments/
// analyse/stock/{symbol} (stocks) — every section carries its own honest
// state, so a pending fact shows "—" plus the reason, never a fake row.

type State = "ok" | "partial" | "pending";

interface SheetHolding {
  id: number; symbol: string; name: string | null; type: string | null;
  units: number; invested: number | null; value: number | null;
  gain_loss: number | null; priced: boolean; weight: number;
  lots_count: number; direct_regular?: string | null;
}
interface FundFacts {
  scheme_name?: string | null; amc?: string | null; category?: string | null;
  sub_category?: string | null; plan_type?: string | null;
  aum_cr?: number | null; expense_ratio_pct?: number | null;
  portfolio_turnover_pct?: number | null; launch_date?: string | null;
  fund_managers?: string[]; exit_load?: string | null;
  min_sip_investment?: number | null; benchmark_name?: string | null;
  risk?: string | null; groww_rating?: number | null; lock_in?: string | null;
  description?: string | null; portfolio_date?: string | null;
  published_returns?: Record<string, number> | null;
  sip_return?: Record<string, number> | null;
  peers?: Record<string, unknown>[];
  pros?: string[]; cons?: string[];
}
interface Perf {
  has_data?: boolean; return_1y_pct?: number | null;
  volatility_pct?: number | null; beta?: number | null;
  alpha_pct?: number | null; sharpe?: number | null;
  sortino?: number | null; max_drawdown_pct?: number | null;
  r_squared?: number | null; shared_days?: number; note?: string;
}
interface Sheet {
  state: State; reason?: string | null;
  holding?: SheetHolding; plan?: string | null; folio?: string | null;
  facts?: FundFacts | null; reference_slug?: string | null;
  portfolio?: { state: string; as_of?: string; holdings?: PortfolioRow[]; reason?: string };
  nav_chart?: { date: string; nav: number }[];
  returns?: Record<string, number>;
  performance?: Perf; xirr?: number | null; lots?: number;
  benchmark?: { name?: string };
  // stock sheet
  symbol?: string; quote?: { price?: number; source?: string } | null;
  range_52w?: { low?: number; high?: number } | null;
  fundamentals?: Record<string, unknown> | null; sector?: string | null;
}
interface PortfolioRow {
  company: string; sector?: string | null; weight: number;
  instrument?: string | null;
}

const RET_LABELS: [string, string][] = [
  ["1m", "1M"], ["3m", "3M"], ["6m", "6M"], ["1y", "1Y"],
  ["3y", "3Y"], ["5y", "5Y"], ["10y", "10Y"],
];

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">{label}</div>
      <div className="mt-0.5 font-mono text-[13px] text-aurum-text">{value ?? "—"}</div>
    </div>
  );
}

function ReturnChips({ returns }: { returns?: Record<string, number> }) {
  if (!returns || Object.keys(returns).length === 0)
    return <p className="text-xs text-aurum-muted">No published returns.</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {RET_LABELS.map(([k, label]) => {
        const v = returns[k];
        if (v === undefined || v === null) return null;
        return (
          <div key={k} className="rounded-lg border border-white/[.07] bg-white/[.02] px-3 py-1.5 text-center">
            <div className="text-[9px] tracking-[.14em] text-aurum-faint">{label}</div>
            <div className={`font-mono text-[13px] ${v >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}`}>
              {v >= 0 ? "+" : ""}{num(v, 1)}%
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RiskGrid({ perf, benchName }: { perf: Perf; benchName?: string | null }) {
  if (!perf?.has_data)
    return <p className="text-xs text-aurum-muted">{perf?.note ?? "Not enough overlapping history for ratios yet."}</p>;
  const cells: [string, React.ReactNode][] = [
    ["Ann. return", pct(perf.return_1y_pct)],
    ["Volatility", pct(perf.volatility_pct)],
    ["Beta", perf.beta === null ? "—" : num(perf.beta, 2)],
    ["Alpha", pct(perf.alpha_pct)],
    ["Sharpe", perf.sharpe === null ? "—" : num(perf.sharpe, 2)],
    ["Sortino", perf.sortino === null ? "—" : num(perf.sortino, 2)],
    ["Max drawdown", pct(perf.max_drawdown_pct)],
    ["R²", perf.r_squared === null ? "—" : num(perf.r_squared, 2)],
  ];
  return (
    <div>
      <div className="grid grid-cols-4 gap-2.5">
        {cells.map(([k, v]) => (
          <div key={k} className="rounded-lg border border-white/[.06] bg-white/[.02] p-2.5">
            <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">{k}</div>
            <div className="mt-0.5 font-mono text-[14px] text-aurum-text">{v}</div>
          </div>
        ))}
      </div>
      <p className="footnote mt-2">
        vs {benchName ?? "NIFTY 50"} · {perf.shared_days ?? "—"} shared days · computed from the NAV ledger
      </p>
    </div>
  );
}

function PortfolioTable({ portfolio }: { portfolio: Sheet["portfolio"] }) {
  if (!portfolio || portfolio.state !== "ok")
    return (
      <p className="text-xs text-aurum-muted">
        {portfolio?.reason ?? "Published portfolio not available for this scheme."}
      </p>
    );
  const rows = portfolio.holdings ?? [];
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="footnote">
          What the fund owns · {rows.length} published positions
          {portfolio.as_of ? ` · as of ${portfolio.as_of}` : ""}
        </p>
        <p className="footnote">WEIGHT = SHARE OF THE FUND&apos;S ASSETS</p>
      </div>
      <div className="max-h-[340px] overflow-y-auto pr-1">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 bg-[#101218]">
            <tr className="text-left text-aurum-faint">
              <th className="py-1.5 pr-3 font-medium">Company</th>
              <th className="py-1.5 pr-3 font-medium">Sector</th>
              <th className="py-1.5 font-medium text-right">Weight</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((h) => (
              <tr key={`${h.company}-${h.instrument}-${h.weight}`} className="border-t border-white/[.05]">
                <td className="py-1.5 pr-3 text-aurum-text">{h.company}</td>
                <td className="py-1.5 pr-3 text-aurum-muted">{h.sector || "—"}</td>
                <td className="py-1.5 text-right">
                  <div className="ml-auto flex w-28 items-center justify-end gap-2">
                    <div className="h-1 w-16 overflow-hidden rounded-full bg-white/[.06]">
                      <div className="h-full rounded-full bg-aurum-gold/70"
                           style={{ width: `${Math.min(100, (h.weight / 10) * 100)}%` }} />
                    </div>
                    <span className="w-12 font-mono text-aurum-text">{num(h.weight, 2)}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FundSheetBody({ sheet }: { sheet: Sheet }) {
  const f = sheet.facts;
  const h = sheet.holding;
  const gainPct = h?.value != null && h.invested ? (h.value / h.invested - 1) * 100 : null;
  return (
    <>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-4">
        <Fact label="Your value" value={inr(h?.value)} />
        <Fact label="Your invested" value={inr(h?.invested)} />
        <Fact label="Your gain"
              value={gainPct === null ? "—" : (
                <span className={gainPct >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}>
                  {inr(h?.gain_loss)} ({gainPct >= 0 ? "+" : ""}{num(gainPct, 1)}%)
                </span>)} />
        <Fact label="Your XIRR" value={sheet.xirr === null || sheet.xirr === undefined ? "needs lots" : `${num(sheet.xirr, 1)}%`} />
        <Fact label="Category" value={[f?.category, f?.sub_category].filter(Boolean).join(" · ") || "—"} />
        <Fact label="Plan" value={f?.plan_type ?? sheet.plan ?? "—"} />
        <Fact label="Expense ratio" value={f?.expense_ratio_pct != null ? `${num(f.expense_ratio_pct, 2)}%` : "—"} />
        <Fact label="AUM" value={f?.aum_cr != null ? `₹${num(f.aum_cr, 0)} Cr` : "—"} />
        <Fact label="Benchmark" value={f?.benchmark_name ?? "—"} />
        <Fact label="Risk" value={f?.risk ?? (f?.groww_rating ? `${f.groww_rating}/5 on Groww` : "—")} />
        <Fact label="Min SIP" value={f?.min_sip_investment != null ? inr(f.min_sip_investment) : "—"} />
        <Fact label="Launched" value={f?.launch_date ?? "—"} />
      </div>

      {f?.description && (
        <p className="mt-3 text-[12px] leading-relaxed text-aurum-muted">{f.description}</p>
      )}
      {f?.exit_load && (
        <p className="mt-2 text-[12px] text-aurum-muted">
          <span className="text-aurum-gold">Exit load:</span> {f.exit_load}
        </p>
      )}

      <div className="mt-5">
        <div className="plabel mb-2">Returns</div>
        <ReturnChips returns={sheet.returns} />
        {f?.sip_return && Object.keys(f.sip_return).length > 0 && (
          <div className="mt-3">
            <div className="plabel mb-2">SIP returns (monthly invest, annualised)</div>
            <ReturnChips returns={f.sip_return} />
          </div>
        )}
      </div>

      <div className="mt-5">
        <div className="plabel mb-2">Risk — one year vs {sheet.benchmark?.name ?? "NIFTY 50"}</div>
        <RiskGrid perf={sheet.performance ?? {}} benchName={sheet.benchmark?.name} />
      </div>

      <div className="mt-5">
        <div className="plabel mb-2">The fund&apos;s portfolio</div>
        <PortfolioTable portfolio={sheet.portfolio} />
      </div>

      {f?.peers && f.peers.length > 0 && (
        <div className="mt-5">
          <div className="plabel mb-2">Peers (same category)</div>
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-aurum-faint">
                <th className="py-1.5 pr-3 font-medium">Fund</th>
                <th className="py-1.5 pr-3 text-right font-medium">1Y</th>
                <th className="py-1.5 pr-3 text-right font-medium">3Y</th>
                <th className="py-1.5 text-right font-medium">Rating</th>
              </tr>
            </thead>
            <tbody>
              {f.peers.map((p, i) => {
                const r1y = p["return1y"] as number | null;
                const r3y = p["return3y"] as number | null;
                const rating = p["groww_rating"] as number | null;
                return (
                  <tr key={i} className="border-t border-white/[.05]">
                    <td className="py-1.5 pr-3 text-aurum-text">{String(p["scheme_name"] ?? p["search_id"] ?? "—")}</td>
                    <td className={`py-1.5 pr-3 text-right font-mono ${(r1y ?? 0) >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}`}>{r1y == null ? "—" : `${num(r1y, 1)}%`}</td>
                    <td className={`py-1.5 pr-3 text-right font-mono ${(r3y ?? 0) >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}`}>{r3y == null ? "—" : `${num(r3y, 1)}%`}</td>
                    <td className="py-1.5 text-right font-mono text-aurum-gold">{rating ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {(f?.pros?.length || f?.cons?.length) ? (
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
          {f?.pros?.length ? (
            <div className="rounded-xl border border-aurum-emerald/20 bg-aurum-emerald/[.04] p-3">
              <div className="plabel mb-1.5 !text-aurum-emerald">Pros · from the reference</div>
              <ul className="list-disc space-y-1 pl-4 text-[12px] leading-relaxed text-aurum-muted">
                {f.pros.slice(0, 5).map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </div>
          ) : null}
          {f?.cons?.length ? (
            <div className="rounded-xl border border-white/[.08] bg-white/[.02] p-3">
              <div className="plabel mb-1.5">Cons · from the reference</div>
              <ul className="list-disc space-y-1 pl-4 text-[12px] leading-relaxed text-aurum-muted">
                {f.cons.slice(0, 5).map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <Explainer />
    </>
  );
}

function StockSheetBody({ sheet }: { sheet: Sheet }) {
  const q = sheet.quote?.price;
  const r52 = sheet.range_52w;
  const fun = sheet.fundamentals ?? {};
  const cap = fun["marketCap"] as number | undefined;
  const rows: [string, React.ReactNode][] = [
    ["Price", q != null ? inr(q) : "—"],
    ["52-week range", r52 ? `${inrCompact(r52.low ?? 0)} – ${inrCompact(r52.high ?? 0)}` : "—"],
    ["Market cap", cap != null ? inrCompact(cap) : "—"],
    ["Sector", sheet.sector ?? (fun["sector"] as string) ?? "—"],
    ["P/E", fun["trailingPE"] != null ? num(fun["trailingPE"] as number, 1) : "—"],
    ["P/B", fun["priceToBook"] != null ? num(fun["priceToBook"] as number, 1) : "—"],
    ["ROE", fun["returnOnEquity"] != null ? pct((fun["returnOnEquity"] as number) * 100, 1) : "—"],
    ["Dividend yield", fun["dividendYield"] != null ? pct(fun["dividendYield"] as number, 2) : "—"],
  ];
  return (
    <>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-4">
        {rows.map(([k, v]) => <Fact key={k} label={k} value={v} />)}
      </div>
      {typeof fun["longBusinessSummary"] === "string" && (
        <p className="mt-3 line-clamp-4 text-[12px] leading-relaxed text-aurum-muted">
          {fun["longBusinessSummary"]}
        </p>
      )}
      <div className="mt-5">
        <div className="plabel mb-2">Returns</div>
        <ReturnChips returns={sheet.returns} />
      </div>
      <div className="mt-5">
        <div className="plabel mb-2">Risk — one year vs {sheet.benchmark?.name ?? "NIFTY 50"}</div>
        <RiskGrid perf={sheet.performance ?? {}} />
      </div>
      <Explainer />
    </>
  );
}

export default function AnalyseDrawer({
  hid, symbol, onClose,
}: { hid?: number; symbol?: string; onClose: () => void }) {
  const path = useMemo(
    () => (symbol ? `/investments/analyse/stock/${symbol}` : `/investments/analyse/${hid}`),
    [hid, symbol]);
  const { data: sheet, isLoading, error } = useFinanceData<Sheet>(path);
  const [visible, setVisible] = useState(false);
  useEffect(() => setVisible(true), []);          // slide-in on mount
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const title = sheet?.facts?.scheme_name ?? sheet?.holding?.name ?? sheet?.symbol ?? "Analysis";
  const kind = sheet?.facts ? "MUTUAL FUND" : sheet?.symbol ? "STOCK" : "HOLDING";

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
           style={{ opacity: visible ? 1 : 0, transition: "opacity .18s" }}
           onClick={onClose} />
      <aside
        className="absolute inset-y-0 right-0 flex w-[min(880px,94vw)] flex-col border-l border-aurum-gold-border bg-[#0C0E16] shadow-2xl"
        style={{ transform: visible ? "translateX(0)" : "translateX(24px)",
                 opacity: visible ? 1 : 0, transition: "transform .22s ease, opacity .22s ease" }}>
        <header className="flex items-start justify-between gap-4 border-b border-white/[.07] px-7 py-4">
          <div>
            <div className="plabel">
              {kind}
              {sheet?.folio ? <span className="tag">FOLIO {sheet.folio}</span> : null}
              {sheet?.state === "partial" ? <span className="tag dim">partial</span> : null}
            </div>
            <h2 className="mt-1 font-serif text-[22px] text-aurum-text">{title}</h2>
            <p className="footnote mt-0.5">
              {sheet?.holding?.symbol ?? sheet?.symbol}
              {sheet?.reference_slug ? ` · groww.in/mutual-funds/${sheet.reference_slug}` : ""}
            </p>
          </div>
          <button onClick={onClose}
                  className="chip hover:border-aurum-gold/40 hover:text-aurum-gold">
            CLOSE · ESC
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-7 py-5">
          {isLoading ? (
            <p className="footnote">LOADING…</p>
          ) : error ? (
            <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
          ) : !sheet ? null : sheet.state === "pending" ? (
            <p className="text-sm text-aurum-muted">{sheet.reason ?? "Nothing to analyse yet."}</p>
          ) : (
            <>
              {sheet.reason && sheet.state === "partial" && (
                <p className="mb-4 rounded-lg border border-white/[.08] bg-white/[.02] px-3 py-2 text-[12px] text-aurum-muted">
                  {sheet.reason}
                </p>
              )}
              {sheet.facts ? <FundSheetBody sheet={sheet} /> : <StockSheetBody sheet={sheet} />}
            </>
          )}
        </div>
      </aside>
    </div>,
    document.body,
  );
}
