"use client";
import dynamic from "next/dynamic";
import { useMemo, useRef, useState } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData } from "@/lib/api";
import { inr, inrCompact, num, pct } from "@/lib/format";
import AnalyseDrawer from "@/components/finance/analyse/AnalyseDrawer";
import type { RidgeMode } from "@/components/finance/three/NetWorthRidge";

// The Investments tab. One hero with the portfolio's value ridge, one
// holdings table with a single ANALYSE action (archive/delete are gone —
// history is soft-archived via Settings if ever needed), the SIP rhythm
// strip derived from recorded lots, and the day movers. Every number is
// ledger-real; sections with no data say so.

const PortfolioRidge = dynamic(
  () => import("@/components/finance/three/NetWorthRidge"),
  { ssr: false, loading: () => null },
);

interface Holding {
  id: number; symbol: string; name: string | null; type: string | null;
  units: number; avg_cost: number; invested: number | null;
  value: number | null; gain_loss: number | null; priced: boolean;
  lots_count: number; weight: number; direct_regular?: string | null;
  folio?: string | null;
}
interface Overview {
  state: string; total_value: number; invested: number; gain_loss: number;
  xirr_pct: number | null; funds_with_portfolio: number;
  portfolio_coverage_pct: number; unpriced: string[];
  settings_verified_by_a_person: boolean;
  value_series: { date: string; value: number }[];
}
interface SipMonth { month: string; amount: number; buys: number }

const KIND_LABEL: Record<string, string> = {
  mutual_fund: "Mutual funds", etf: "ETFs & gold", stock: "Stocks",
  other: "Other", bond: "Bonds",
};

function PlanChip({ h }: { h: Holding }) {
  const name = (h.name ?? "").toLowerCase();
  const plan = name.includes("regular") ? "regular"
    : name.includes("direct") ? "direct" : (h.direct_regular ?? "");
  if (plan === "direct") return <span className="chip e">DIRECT</span>;
  if (plan === "regular") return <span className="chip">REGULAR</span>;
  return null;
}

function HeroPanel() {
  const { data, isLoading, error } = useFinanceData<Overview>("/analysis/overview");
  const [ridge, setRidge] = useState<RidgeMode | null>(null);
  const trend = useMemo(() => (data?.value_series ?? []).map((p) => p.value), [data]);
  const gainPct = data && data.invested ? (data.gain_loss / data.invested) * 100 : null;

  return (
    <section className="panel hero flex min-h-[280px] flex-col pb-0">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="flex items-start justify-between gap-4">
            <div className="plabel">
              Portfolio
              <span className={`tag ${ridge === "svg" ? "dim" : ""}`}>
                {ridge === "svg" ? "ridge · still" : "3D ridge · three.js"}
              </span>
            </div>
            <div className="flex gap-6">
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">Invested</div>
                <div className="mt-[3px] font-mono text-[15px] text-aurum-text">{inr(data.invested)}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">XIRR</div>
                <div className="mt-[3px] font-mono text-[15px] goldc">
                  {data.xirr_pct == null ? "needs lots" : `${num(data.xirr_pct, 1)}%`}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[.14em] text-aurum-faint">X-ray coverage</div>
                <div className="mt-[3px] font-mono text-[15px] text-aurum-text">
                  {num(data.portfolio_coverage_pct, 0)}%
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3.5 flex items-end gap-4">
            <div className="value-hero">
              <span className="cur">₹</span>{num(data.total_value)}
            </div>
            {gainPct !== null && (
              <div className={`delta ${data.gain_loss >= 0 ? "up" : "down"}`}>
                {data.gain_loss >= 0 ? "▲" : "▼"} {inr(data.gain_loss)} ({num(gainPct, 1)}%)
              </div>
            )}
          </div>
          {data.unpriced.length > 0 && (
            <p className="footnote mt-2">
              UNPRICED, EXCLUDED FROM TOTALS: {data.unpriced.join(", ")}
            </p>
          )}

          <div className="pointer-events-auto absolute inset-x-0 bottom-0 h-[150px]">
            <PortfolioRidge trend={trend} projection={[]} onMode={setRidge} />
          </div>
        </>
      )}
    </section>
  );
}

function HoldingsTable({ onAnalyse }: { onAnalyse: (id: number) => void }) {
  const { data, isLoading, error } = useFinanceData<Holding[]>("/investments/holdings");

  const groups = useMemo(() => {
    const g: Record<string, Holding[]> = {};
    for (const h of data ?? []) {
      const k = h.type && KIND_LABEL[h.type] ? h.type : "other";
      (g[k] ??= []).push(h);
    }
    for (const k of Object.keys(g))
      g[k].sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
    return g;
  }, [data]);

  if (isLoading) return <Card title="Holdings"><p className="footnote">LOADING…</p></Card>;
  if (error) return <Card title="Holdings"><p className="text-xs text-aurum-coral">{error.message}</p></Card>;

  return (
    <Card title="Holdings">
      {!data || data.length === 0 ? (
        <p className="text-sm text-aurum-muted">No holdings yet — import the CAS PDF below.</p>
      ) : (
        <div className="space-y-5">
          {Object.entries(groups).map(([kind, rows]) => (
            <div key={kind}>
              <div className="plabel mb-1.5">{KIND_LABEL[kind] ?? kind}</div>
              <div className="overflow-x-auto">
                <table className="w-full text-[12.5px]">
                  <thead>
                    <tr className="text-left text-aurum-faint">
                      <th className="py-1.5 pr-3 font-medium">Scheme</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Units</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Avg cost</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Invested</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Value</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Gain</th>
                      <th className="py-1.5 pr-3 font-medium">Weight</th>
                      <th className="py-1.5 text-right font-medium" />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((h) => {
                      const gainPct = h.value != null && h.invested
                        ? (h.value / h.invested - 1) * 100 : null;
                      return (
                        <tr key={h.id} className="border-t border-white/[.05] hover:bg-white/[.015]">
                          <td className="py-2 pr-3">
                            <div className="text-aurum-text">{h.name ?? h.symbol}</div>
                            <div className="mt-0.5 flex items-center gap-1.5">
                              <span className="footnote">{h.symbol}</span>
                              {h.folio ? <span className="footnote">· FOLIO {h.folio}</span> : null}
                              <PlanChip h={h} />
                            </div>
                          </td>
                          <td className="py-2 pr-3 text-right font-mono text-aurum-muted">{num(h.units, 3)}</td>
                          <td className="py-2 pr-3 text-right font-mono text-aurum-muted">{inrCompact(h.avg_cost)}</td>
                          <td className="py-2 pr-3 text-right font-mono text-aurum-muted">{inrCompact(h.invested)}</td>
                          <td className="py-2 pr-3 text-right font-mono text-aurum-text">
                            {h.priced ? inr(h.value) : <span className="text-aurum-faint">unpriced</span>}
                          </td>
                          <td className={`py-2 pr-3 text-right font-mono ${h.gain_loss == null ? "" : h.gain_loss >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}`}>
                            {h.gain_loss == null ? "—"
                              : `${h.gain_loss >= 0 ? "+" : ""}${inrCompact(h.gain_loss)}${gainPct != null ? ` (${num(gainPct, 1)}%)` : ""}`}
                          </td>
                          <td className="py-2 pr-3">
                            <div className="flex items-center gap-2">
                              <div className="h-1 w-14 overflow-hidden rounded-full bg-white/[.06]">
                                <div className="h-full rounded-full bg-aurum-gold/70"
                                     style={{ width: `${Math.min(100, h.weight * 100)}%` }} />
                              </div>
                              <span className="w-10 font-mono text-aurum-muted">{pct(h.weight * 100, 1)}</span>
                            </div>
                          </td>
                          <td className="py-2 text-right">
                            <button
                              onClick={() => onAnalyse(h.id)}
                              className="chip g hover:border-aurum-gold/60">
                              ANALYSE
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function SipStrip() {
  const { data, isLoading } = useFinanceData<{ state: string; months: SipMonth[]; reason?: string }>(
    "/investments/sip-calendar");
  const months = (data?.months ?? []).slice(-12);
  const max = Math.max(1, ...months.map((m) => m.amount));
  const total12 = months.reduce((s, m) => s + (m.amount ?? 0), 0);

  async function importCas(file: File, pan: string) {
    const fd = new FormData();
    fd.append("file", file);
    const q = pan ? `?pan=${encodeURIComponent(pan)}` : "";
    const res = await fetch(`/api/finance/import/cas${q}`, { method: "POST", body: fd });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body?.detail ?? `${res.status}`);
    alert(`CAS imported — as of ${body.as_of ?? "?"}. Holdings updated, ${body.lots_written ?? 0} purchase lots written.`);
    location.reload();
  }

  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <Card title="SIP rhythm" isLoading={isLoading}>
      {!data || data.state !== "ok" || months.length === 0 ? (
        <div>
          <p className="text-sm text-aurum-muted">
            {data?.reason ?? "No dated purchase lots yet."}
          </p>
          <p className="footnote mt-1">
            THE CAS STATEMENT CARRIES EVERY BUY — IMPORT IT AND THIS PANEL FILLS ITSELF.
          </p>
        </div>
      ) : (
        <>
          <div className="flex h-24 items-end gap-1.5">
            {months.map((m) => (
              <div key={m.month} className="group flex flex-1 flex-col items-center justify-end gap-1">
                <span className="font-mono text-[9px] text-aurum-faint opacity-0 transition group-hover:opacity-100">
                  {inrCompact(m.amount)}
                </span>
                <div className="w-full rounded-t bg-aurum-gold/55 transition group-hover:bg-aurum-gold"
                     style={{ height: `${Math.max(4, (m.amount / max) * 100)}%` }} />
                <span className="font-mono text-[9px] text-aurum-faint">{m.month.slice(5)}</span>
              </div>
            ))}
          </div>
          <p className="footnote mt-2">
            RECORDED BUYS BY MONTH · LAST 12 · TOTAL {inrCompact(total12)} ·
            GROWS AS CAS IMPORTS ADD LOTS
          </p>
        </>
      )}
      <input ref={fileRef} type="file" accept="application/pdf" className="hidden"
             onChange={(e) => {
               const f = e.target.files?.[0];
               if (!f) return;
               const pan = prompt("PAN (the CAS opens with it):", "") ?? "";
               importCas(f, pan).catch((err) => alert(`Import failed: ${err.message}`));
               e.target.value = "";
             }} />
      <div className="mt-3 flex items-center gap-2">
        <button className="chip hover:border-aurum-gold/40 hover:text-aurum-gold"
                onClick={() => fileRef.current?.click()}>
          IMPORT CAS PDF
        </button>
        <span className="footnote">BUILDS LOTS · XIRR · TAX BUCKETS</span>
      </div>
    </Card>
  );
}

function MoversPanel() {
  const { data } = useFinanceData<Holding[]>("/investments/holdings");
  const movers = useMemo(() => {
    const priced = (data ?? []).filter((h) => h.value != null && h.invested);
    const withPct = priced.map((h) => ({
      h, pctv: (h.value! / h.invested! - 1) * 100,
    }));
    withPct.sort((a, b) => b.pctv - a.pctv);
    return { up: withPct.slice(0, 3), down: withPct.slice(-3).reverse() };
  }, [data]);

  const Row = ({ h, pctv }: { h: Holding; pctv: number }) => (
    <div className="flex items-center justify-between border-t border-white/[.05] py-1.5">
      <span className="truncate pr-3 text-[12.5px] text-aurum-text">{h.name ?? h.symbol}</span>
      <span className={`font-mono text-[12.5px] ${pctv >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}`}>
        {pctv >= 0 ? "+" : ""}{num(pctv, 1)}%
      </span>
    </div>
  );

  return (
    <Card title="Day's leaders — since you bought">
      {!data || data.length === 0 ? (
        <p className="text-sm text-aurum-muted">No priced holdings yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <div>
            <div className="plabel mb-1">Strongest</div>
            {movers.up.map(({ h, pctv }) => <Row key={h.id} h={h} pctv={pctv} />)}
          </div>
          <div>
            <div className="plabel mb-1">Weakest</div>
            {movers.down.map(({ h, pctv }) => <Row key={h.id} h={h} pctv={pctv} />)}
          </div>
        </div>
      )}
      <p className="footnote mt-2">GAIN SINCE YOUR AVERAGE COST — NOT TODAY&apos;S MOVE. THE LEDGER&apos;S NAV DATES CARRY THE FRESHNESS.</p>
    </Card>
  );
}

export default function InvestmentsPage() {
  const [analyseId, setAnalyseId] = useState<number | null>(null);
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <div className="lg:col-span-8">
        <HeroPanel />
      </div>
      <div className="lg:col-span-4">
        <SipStrip />
      </div>
      <div className="lg:col-span-8">
        <HoldingsTable onAnalyse={setAnalyseId} />
      </div>
      <div className="lg:col-span-4">
        <MoversPanel />
      </div>
      {analyseId !== null && (
        <AnalyseDrawer hid={analyseId} onClose={() => setAnalyseId(null)} />
      )}
    </div>
  );
}
