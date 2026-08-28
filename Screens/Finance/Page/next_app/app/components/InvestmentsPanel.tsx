"use client";

import { useInvestments } from "./useInvestments";
import { AskStrip } from "./AskStrip";

/** Tab 2 - what is actually held. The snapshot ledger (portfolio_holdings.csv,
    editable elsewhere, read-only here), the NAV ledger with a per-row
    fresh/stale badge, and true per-holding XIRR. An empty snapshot says
    so plainly - never padded with an invented row (C12). */
export function InvestmentsPanel() {
  const { investments, navLedger, xirr, state } = useInvestments();

  const freshness = state === "fresh" ? "fresh" : state === "error" ? "unavailable" : "empty";

  return (
    <section aria-label="Investments" data-fresh={freshness} className="flex flex-col gap-4">
      {state === "loading" && !investments && <p className="text-sm text-dim">loading investments...</p>}
      {state === "error" && !investments && (
        <p className="text-sm text-p5red">could not reach /api/finance/investments</p>
      )}

      {investments && (
        <div className="rounded-lg border border-line bg-panel p-4">
          <header className="mb-3 flex items-center justify-between gap-3">
            <h2 className="num text-sm tracking-[0.2em] text-dim">HOLDINGS SNAPSHOT</h2>
            {investments.has_snapshot && (
              <span className="num text-sm text-bone">
                {investments.snapshot_total_current.text}
                <span className="text-dim"> / invested {investments.snapshot_total_invested.text}</span>
              </span>
            )}
          </header>

          {!investments.has_snapshot && (
            <p className="text-xs text-dim">{investments.snapshot_note || "no snapshot on file yet"}</p>
          )}

          {investments.has_snapshot && (
            <div className="scroll-x">
              <table className="num w-full min-w-[480px] text-xs">
                <thead>
                  <tr className="text-left text-dim">
                    <th className="pb-1 font-normal">fund</th>
                    <th className="pb-1 text-right font-normal">invested</th>
                    <th className="pb-1 text-right font-normal">current</th>
                    <th className="pb-1 text-right font-normal">P/L</th>
                  </tr>
                </thead>
                <tbody>
                  {investments.snapshot_holdings.map((h) => (
                    <tr key={h.scheme_name} className="border-t border-line/40">
                      <td className="py-1 text-bone">{h.scheme_name}</td>
                      <td className="py-1 text-right text-dim">{h.invested.text}</td>
                      <td className="py-1 text-right text-bone">{h.current.text}</td>
                      <td className={`py-1 text-right ${(h.pl_abs.raw ?? 0) < 0 ? "text-p5red" : "text-jade"}`}>
                        {h.pl_abs.text}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {navLedger && (
        <div className="rounded-lg border border-line bg-panel p-4">
          <h2 className="num mb-2 text-sm tracking-[0.2em] text-dim">NAV LEDGER</h2>
          {!navLedger.has_data && <p className="text-xs text-dim">no NAV recorded yet</p>}
          {navLedger.has_data && (
            <div className="flex flex-col gap-1">
              {navLedger.rows.map((r) => (
                <div key={r.scheme_name} className="flex items-center justify-between gap-3 text-xs">
                  <span className="truncate text-bone">{r.scheme_name}</span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className="num text-dim">{r.nav ?? "—"}</span>
                    <span
                      className={`num rounded border px-1.5 py-0.5 text-[9px] tracking-widest ${
                        r.state === "fresh" ? "border-jade text-jade" : "border-amber text-amber"
                      }`}
                    >
                      {r.state.toUpperCase()}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {xirr && xirr.has_data && (
        <div className="rounded-lg border border-line bg-panel p-4">
          <h2 className="num mb-2 text-sm tracking-[0.2em] text-dim">XIRR PER HOLDING</h2>
          <div className="flex flex-col gap-1">
            {xirr.holdings.map((h) => (
              <div key={h.name} className="flex items-center justify-between gap-3 text-xs">
                <span className="truncate text-bone">{h.name}</span>
                <span className="num text-dim">{h.xirr_pct != null ? `${h.xirr_pct}%/yr` : "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <AskStrip endpoint="/api/finance/investments/ask" placeholder="Ask about your own holdings..." />
    </section>
  );
}
