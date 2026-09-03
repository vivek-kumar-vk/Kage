"use client";
import { useMemo, useState } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData, useSubmit } from "@/lib/api";
import { inr, inrCompact, num, dateOrDash } from "@/lib/format";
import AnalyseDrawer from "@/components/finance/analyse/AnalyseDrawer";

// The Trade Desk — four segments:
//   WATCHLIST  tracked names with live quotes (ANALYSE opens the stock sheet)
//   JOURNAL    delivery swing trades with per-trade capital-gains buckets
//   IPO        the live calendar + your own UPI-ASBA checklist
//   GLOBAL     the LRS/TCS math for a planned overseas investment
// Delivery-only by design: no intraday, no F&O (house rule). The journal
// never rewrites a closed trade.

type Segment = "watchlist" | "journal" | "ipo" | "global";

interface WatchItem {
  id: number; symbol: string; name: string | null; asset_type: string;
  notes: string | null; price: number | null; priced: boolean;
  price_source?: string | null; added_at: string;
}
interface Trade {
  id: number; symbol: string; name: string | null; qty: number;
  entry_price: number; entry_date: string; exit_price: number | null;
  exit_date: string | null; charges: number; thesis: string | null;
  status: string; pnl: number | null; cg_bucket: string | null;
  holding_days?: number; est_tax_rs: number | null; cg_rate_pct?: number;
}
interface TradeData {
  state: string; trades: Trade[];
  summary: { open: number; closed: number; realized_stcg: number;
    realized_ltcg: number; ltcg_exemption_rs: number; est_tax_rs: number };
}
interface IpoRow {
  name: string; symbol?: string | null; open_date?: string | null;
  close_date?: string | null; price_min?: number | null;
  price_max?: number | null; status: string; applied: boolean;
  upi_mandate?: string | null; notes?: string | null; is_sme?: boolean;
}
interface IpoData { state: string; open: IpoRow[]; upcoming: IpoRow[]; closed: IpoRow[]; reason?: string }
interface GlobalData {
  state: string; usd_inr: number | null; lrs_limit_usd: number;
  lrs_limit_inr: number | null;
  tcs: { rate_pct: number; threshold_rs: number; creditable_note: string };
  nasdaq_100_note: string;
  planned?: { usd: number; within_lrs: boolean; tcs_payable_rs: number;
    tcs_applies: boolean; total_cash_needed_rs: number; note: string };
}

const SEGMENTS: [Segment, string][] = [
  ["watchlist", "WATCHLIST"], ["journal", "JOURNAL"],
  ["ipo", "IPO"], ["global", "GLOBAL"],
];

function Segments({ seg, setSeg }: { seg: Segment; setSeg: (s: Segment) => void }) {
  return (
    <div className="flex gap-1">
      {SEGMENTS.map(([s, label]) => (
        <button key={s} onClick={() => setSeg(s)}
                className={`border-b-2 px-4 pb-2 pt-1 text-[12px] font-medium tracking-wide transition ${
                  seg === s
                    ? "border-aurum-gold text-aurum-gold-bright"
                    : "border-transparent text-aurum-muted hover:text-aurum-text"}`}>
          {label}
        </button>
      ))}
    </div>
  );
}

/* ---------------- WATCHLIST ---------------- */
function Watchlist({ onAnalyse }: { onAnalyse: (symbol: string) => void }) {
  const { data, isLoading, error, refetch } = useFinanceData<{ state: string; items: WatchItem[]; reason?: string }>(
    "/tradedesk/watchlist");
  const { submit } = useSubmit("/tradedesk/watchlist", "POST");
  const [sym, setName] = useState({ symbol: "", name: "" });

  return (
    <Card title="Watchlist" isLoading={isLoading} error={error}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input value={sym.symbol} onChange={(e) => setName({ ...sym, symbol: e.target.value.toUpperCase() })}
               placeholder="SYMBOL (NSE)" className="w-40 rounded-lg border border-white/[.09] bg-white/[.03] px-3 py-1.5 font-mono text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50" />
        <input value={sym.name} onChange={(e) => setName({ ...sym, name: e.target.value })}
               placeholder="Name" className="w-48 rounded-lg border border-white/[.09] bg-white/[.03] px-3 py-1.5 text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50" />
        <button className="chip g" disabled={!sym.symbol}
                onClick={() => submit({ symbol: sym.symbol, name: sym.name })
                  .then(() => { setName({ symbol: "", name: "" }); refetch(); })
                  .catch((e) => alert(e.message))}>
          TRACK
        </button>
      </div>
      {!data || data.items.length === 0 ? (
        <p className="text-sm text-aurum-muted">{data?.reason ?? "Loading…"}</p>
      ) : (
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-aurum-faint">
              <th className="py-1.5 pr-3 font-medium">Name</th>
              <th className="py-1.5 pr-3 text-right font-medium">Price</th>
              <th className="py-1.5 pr-3 font-medium">Notes</th>
              <th className="py-1.5 text-right font-medium" />
            </tr>
          </thead>
          <tbody>
            {data.items.map((w) => (
              <tr key={w.id} className="border-t border-white/[.05]">
                <td className="py-2 pr-3">
                  <div className="text-aurum-text">{w.name ?? w.symbol}</div>
                  <div className="footnote">{w.symbol}</div>
                </td>
                <td className="py-2 pr-3 text-right font-mono text-aurum-text">
                  {w.priced ? inr(w.price) : <span className="text-aurum-faint">—</span>}
                </td>
                <td className="py-2 pr-3 text-[12px] text-aurum-muted">{w.notes ?? ""}</td>
                <td className="py-2 text-right">
                  <button className="chip g mr-1.5" onClick={() => onAnalyse(w.symbol)}>ANALYSE</button>
                  <button className="chip hover:border-aurum-coral/40 hover:text-aurum-coral"
                          onClick={() => fetch(`/api/finance/tradedesk/watchlist/${w.id}`, { method: "DELETE" })
                            .then(refetch)}>
                    REMOVE
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

/* ---------------- JOURNAL ---------------- */
function Journal() {
  const { data, isLoading, error, refetch } = useFinanceData<TradeData>("/tradedesk/trades");
  const { submit } = useSubmit("/tradedesk/trades", "POST");
  const [form, setForm] = useState({ symbol: "", name: "", qty: "", entry_price: "", entry_date: "", thesis: "" });
  const [closing, setClosing] = useState<Trade | null>(null);
  const [exit, setExit] = useState({ exit_price: "", exit_date: new Date().toISOString().slice(0, 10) });
  const valid = form.symbol && form.qty && form.entry_price && form.entry_date;
  const s = data?.summary;

  return (
    <Card title="Swing-trade journal" isLoading={isLoading} error={error}>
      {s && (
        <div className="mb-4 grid grid-cols-2 gap-2.5 md:grid-cols-5">
          {[
            ["Open", String(s.open)],
            ["Closed", String(s.closed)],
            ["Realised STCG", inr(s.realized_stcg)],
            ["Realised LTCG", inr(s.realized_ltcg)],
            ["Est. tax", inr(s.est_tax_rs)],
          ].map(([k, v]) => (
            <div key={k} className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
              <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">{k}</div>
              <div className="mt-0.5 font-mono text-[14px] text-aurum-text">{v}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input value={form.symbol} placeholder="SYMBOL"
               onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
               className="w-28 rounded-lg border border-white/[.09] bg-white/[.03] px-2.5 py-1.5 font-mono text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50" />
        <input value={form.qty} placeholder="QTY" type="number"
               onChange={(e) => setForm({ ...form, qty: e.target.value })}
               className="w-20 rounded-lg border border-white/[.09] bg-white/[.03] px-2.5 py-1.5 font-mono text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50" />
        <input value={form.entry_price} placeholder="BUY ₹" type="number"
               onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
               className="w-24 rounded-lg border border-white/[.09] bg-white/[.03] px-2.5 py-1.5 font-mono text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50" />
        <input value={form.entry_date} type="date"
               onChange={(e) => setForm({ ...form, entry_date: e.target.value })}
               className="rounded-lg border border-white/[.09] bg-white/[.03] px-2.5 py-1.5 text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50" />
        <input value={form.thesis} placeholder="Why (one line)" className="flex-1 rounded-lg border border-white/[.09] bg-white/[.03] px-2.5 py-1.5 text-[12px] text-aurum-text outline-none focus:border-aurum-gold/50"
               onChange={(e) => setForm({ ...form, thesis: e.target.value })} />
        <button className="chip g" disabled={!valid}
                onClick={() => submit({ ...form, qty: Number(form.qty), entry_price: Number(form.entry_price) })
                  .then(() => { setForm({ symbol: "", name: "", qty: "", entry_price: "", entry_date: "", thesis: "" }); refetch(); })
                  .catch((e) => alert(e.message))}>
          LOG ENTRY
        </button>
      </div>

      {!data || data.trades.length === 0 ? (
        <p className="text-sm text-aurum-muted">{data?.state === "pending" ? "No trades journalled yet." : "Loading…"}</p>
      ) : (
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-aurum-faint">
              <th className="py-1.5 pr-3 font-medium">Trade</th>
              <th className="py-1.5 pr-3 text-right font-medium">Entry → Exit</th>
              <th className="py-1.5 pr-3 text-right font-medium">P&L</th>
              <th className="py-1.5 pr-3 font-medium">CG bucket</th>
              <th className="py-1.5 pr-3 font-medium">Thesis</th>
              <th className="py-1.5 text-right font-medium" />
            </tr>
          </thead>
          <tbody>
            {data.trades.map((t) => (
              <tr key={t.id} className="border-t border-white/[.05]">
                <td className="py-2 pr-3">
                  <div className="text-aurum-text">{t.name ?? t.symbol} · {num(t.qty, 0)}</div>
                  <div className="footnote">DELIVERY · {t.symbol}</div>
                </td>
                <td className="py-2 pr-3 text-right font-mono text-aurum-muted">
                  {inrCompact(t.entry_price)} → {t.exit_price != null ? inrCompact(t.exit_price) : "OPEN"}
                  <div className="footnote">{dateOrDash(t.entry_date)} → {t.exit_date ? dateOrDash(t.exit_date) : "—"}</div>
                </td>
                <td className={`py-2 pr-3 text-right font-mono ${(t.pnl ?? 0) >= 0 ? "text-aurum-emerald" : "text-aurum-coral"}`}>
                  {t.pnl == null ? "—" : `${t.pnl >= 0 ? "+" : ""}${inr(t.pnl)}`}
                </td>
                <td className="py-2 pr-3">
                  {t.cg_bucket ? (
                    <span className="chip g">{t.cg_bucket.toUpperCase()} · {t.cg_rate_pct}%</span>
                  ) : (
                    <span className="footnote">ON CLOSE</span>
                  )}
                </td>
                <td className="max-w-[180px] truncate py-2 pr-3 text-[12px] text-aurum-muted">{t.thesis ?? ""}</td>
                <td className="py-2 text-right">
                  {t.status === "open" ? (
                    <button className="chip g" onClick={() => setClosing(t)}>CLOSE</button>
                  ) : (
                    <button className="chip hover:border-aurum-coral/40 hover:text-aurum-coral"
                            onClick={() => fetch(`/api/finance/tradedesk/trades/${t.id}`, { method: "DELETE" }).then(refetch)}>
                      DELETE
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="footnote mt-3">
        DELIVERY SWINGS ARE CAPITAL GAINS, NOT BUSINESS INCOME — HOLDING &gt; 12 MONTHS = LTCG 12.5%
        (ABOVE ₹1.25L/YR), ELSE STCG 20%. EST. TAX USES THE RULEBOOK FILE, STILL [UNVERIFIED].
      </p>

      {closing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
             onClick={() => setClosing(null)}>
          <div className="panel w-[380px]" onClick={(e) => e.stopPropagation()}>
            <div className="plabel mb-2">Close {closing.symbol}</div>
            <div className="space-y-2">
              <input value={exit.exit_price} type="number" placeholder="SELL ₹"
                     onChange={(e) => setExit({ ...exit, exit_price: e.target.value })}
                     className="w-full rounded-lg border border-white/[.09] bg-white/[.03] px-3 py-2 font-mono text-[13px] text-aurum-text outline-none focus:border-aurum-gold/50" />
              <input value={exit.exit_date} type="date"
                     onChange={(e) => setExit({ ...exit, exit_date: e.target.value })}
                     className="w-full rounded-lg border border-white/[.09] bg-white/[.03] px-3 py-2 text-[13px] text-aurum-text outline-none focus:border-aurum-gold/50" />
              <button className="chip g w-full justify-center py-2 text-center"
                      onClick={() =>
                        fetch(`/api/finance/tradedesk/trades/${closing.id}/close`, {
                          method: "PUT",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ exit_price: Number(exit.exit_price), exit_date: exit.exit_date }),
                        }).then(async (r) => {
                          if (!r.ok) alert(await r.text());
                          setClosing(null); refetch();
                        })}>
                RECORD EXIT
              </button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

/* ---------------- IPO ---------------- */
function Ipo() {
  const { data, isLoading, error, refetch } = useFinanceData<IpoData>("/tradedesk/ipo");
  const [toggle, setToggle] = useState<{ name: string; applied: boolean } | null>(null);

  function setApplied(row: IpoRow, applied: boolean) {
    setToggle({ name: row.name, applied });
    fetch("/api/finance/tradedesk/ipo/checklist", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: row.name, applied }),
    }).then(refetch).finally(() => setToggle(null));
  }

  const Group = ({ label, rows }: { label: string; rows?: IpoRow[] }) => (
    <div>
      <div className="plabel mb-1.5">{label}</div>
      {!rows || rows.length === 0 ? (
        <p className="text-[12px] text-aurum-faint">—</p>
      ) : (
        <div className="space-y-1.5">
          {rows.map((r) => (
            <div key={r.name} className="rounded-xl border border-white/[.06] bg-white/[.02] p-2.5">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-[12.5px] text-aurum-text">
                    {r.name} {r.is_sme ? <span className="chip">SME</span> : null}
                  </div>
                  <div className="footnote mt-0.5">
                    {r.status === "open" ? `OPEN ${dateOrDash(r.open_date)} → ${dateOrDash(r.close_date)}`
                      : r.status === "upcoming" ? `EXPECTED ${dateOrDash(r.open_date)}`
                      : `CLOSED ${dateOrDash(r.close_date) ?? ""}`}
                    {r.price_min != null ? ` · ₹${num(r.price_min, 0)}${r.price_max ? `–₹${num(r.price_max, 0)}` : ""}` : ""}
                  </div>
                </div>
                {r.status !== "closed" && (
                  <button className={`chip ${r.applied ? "e" : ""}`}
                          disabled={toggle?.name === r.name}
                          onClick={() => setApplied(r, !r.applied)}>
                    {r.applied ? "APPLIED ✓" : "MARK APPLIED"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <Card title="IPO calendar" isLoading={isLoading} error={error}>
      {!data || data.state !== "ok" ? (
        <p className="text-sm text-aurum-muted">{data?.reason ?? "Loading…"}</p>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <Group label="Open now" rows={data.open} />
          <Group label="Upcoming" rows={data.upcoming} />
          <Group label="Recently closed" rows={data.closed.slice(0, 6)} />
        </div>
      )}
      <p className="footnote mt-3">
        CALENDAR AS PUBLISHED BY GROWW, CACHED 24H · APPLYING IS YOUR CALL — THIS IS A CHECKLIST,
        NOT ADVICE · UPI-ASBA: FUNDS SIT BLOCKED UNTIL ALLOTMENT.
      </p>
    </Card>
  );
}

/* ---------------- GLOBAL ---------------- */
function Global() {
  const [planned, setPlanned] = useState("");
  const q = planned ? `?planned_inr=${Number(planned)}` : "";
  const { data, isLoading, error } = useFinanceData<GlobalData>(`/tradedesk/global${q}`);

  return (
    <Card title="Global planner" isLoading={isLoading} error={error}>
      {!data || data.state !== "ok" ? (
        <p className="text-sm text-aurum-muted">The FX rate could not be fetched right now.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ["USD / INR", data.usd_inr ? num(data.usd_inr, 2) : "—"],
              ["LRS limit", `$${num(data.lrs_limit_usd, 0)}`],
              ["LRS in ₹", data.lrs_limit_inr ? inrCompact(data.lrs_limit_inr) : "—"],
              ["TCS above", inr(data.tcs.threshold_rs)],
            ].map(([k, v]) => (
              <div key={k} className="rounded-xl border border-white/[.06] bg-white/[.02] p-3">
                <div className="text-[9px] uppercase tracking-[.12em] text-aurum-faint">{k}</div>
                <div className="mt-0.5 font-mono text-[16px] text-aurum-text">{v}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-xl border border-white/[.06] bg-white/[.02] p-4">
            <div className="plabel mb-2">Plan an overseas investment</div>
            <div className="flex items-center gap-3">
              <input value={planned} type="number" placeholder="Amount in ₹"
                     onChange={(e) => setPlanned(e.target.value)}
                     className="w-48 rounded-lg border border-white/[.09] bg-white/[.03] px-3 py-1.5 font-mono text-[13px] text-aurum-text outline-none focus:border-aurum-gold/50" />
              {data.planned && (
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-[12.5px]">
                  <span className="text-aurum-muted">= <span className="font-mono text-aurum-text">${num(data.planned.usd, 0)}</span></span>
                  <span className="text-aurum-muted">TCS: <span className={`font-mono ${data.planned.tcs_applies ? "text-aurum-amber" : "text-aurum-text"}`}>{inr(data.planned.tcs_payable_rs)}</span></span>
                  <span className="text-aurum-muted">Cash needed: <span className="font-mono text-aurum-text">{inr(data.planned.total_cash_needed_rs)}</span></span>
                  <span className={`chip ${data.planned.within_lrs ? "e" : "r"}`}>
                    {data.planned.within_lrs ? "WITHIN LRS" : "NEEDS RBI PATH"}
                  </span>
                </div>
              )}
            </div>
            {data.planned && <p className="footnote mt-2">{data.planned.note}</p>}
          </div>

          <p className="mt-3 text-[12px] leading-relaxed text-aurum-muted">{data.tcs.creditable_note}</p>
          <p className="mt-1 text-[12px] leading-relaxed text-aurum-muted">{data.nasdaq_100_note}</p>
          <p className="footnote mt-2">
            LRS $250K/YEAR (RBI) · TCS 20% ABOVE ₹10L/YEAR FOR INVESTMENTS (FINANCE ACT 2024) ·
            NUMBERS UNVERIFIED AGAINST THE CURRENT FINANCE ACT.
          </p>
        </>
      )}
    </Card>
  );
}

export default function TradeDeskPage() {
  const [seg, setSeg] = useState<Segment>("watchlist");
  const [analyseSym, setAnalyseSym] = useState<string | null>(null);
  const body = useMemo(() => {
    switch (seg) {
      case "watchlist": return <Watchlist onAnalyse={setAnalyseSym} />;
      case "journal": return <Journal />;
      case "ipo": return <Ipo />;
      case "global": return <Global />;
    }
  }, [seg]);

  return (
    <div className="space-y-4">
      <Segments seg={seg} setSeg={setSeg} />
      {body}
      {analyseSym && (
        <AnalyseDrawer symbol={analyseSym} onClose={() => setAnalyseSym(null)} />
      )}
    </div>
  );
}
