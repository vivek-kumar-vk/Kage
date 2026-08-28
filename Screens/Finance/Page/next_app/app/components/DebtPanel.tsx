"use client";

import { useState } from "react";
import { useDebt } from "./useDebt";

type SubTab = "loans" | "networth";

/** Tab 3 - Loans and Net Worth as sub-tabs, matching the vanilla Debt
    tab's own split. The personal-debt clear date and the education-loan
    payoff are the two countdowns that matter most in this project; the
    net-worth ledger is a separate, read-only file. Neither figure is
    softened - a negative net worth or a distant payoff date renders
    exactly as computed. */
export function DebtPanel() {
  const { debt, liabilities, state } = useDebt();
  const [sub, setSub] = useState<SubTab>("loans");

  const freshness = state === "fresh" ? "fresh" : state === "error" ? "unavailable" : "empty";

  return (
    <section aria-label="Debt" data-fresh={freshness} className="flex flex-col gap-4">
      <nav className="sub-tab-strip flex gap-2">
        {(["loans", "networth"] as SubTab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setSub(t)}
            className={`num rounded border px-3 py-1 text-[11px] tracking-widest ${
              sub === t ? "border-jade text-jade" : "border-line text-dim hover:border-cyan hover:text-cyan"
            }`}
          >
            {t === "loans" ? "LOANS" : "NET WORTH"}
          </button>
        ))}
      </nav>

      {state === "loading" && !debt && <p className="text-sm text-dim">loading debt...</p>}
      {state === "error" && !debt && <p className="text-sm text-p5red">could not reach /api/finance/debt</p>}

      {sub === "loans" && debt && (
        <div className="flex flex-col gap-4">
          <div className="rounded-lg border border-line bg-panel p-4">
            <h2 className="num mb-2 text-sm tracking-[0.2em] text-dim">PERSONAL DEBT</h2>
            <p className="num text-xl text-bone">{debt.personal_debt.remaining.text}</p>
            <p className="text-xs text-dim">
              {debt.personal_debt.monthly.text}/month · clears {debt.personal_debt.clears}
              {debt.personal_debt.months_left != null && ` · ${debt.personal_debt.months_left} months left`}
            </p>
          </div>
          <div className="rounded-lg border border-line bg-panel p-4">
            <h2 className="num mb-2 text-sm tracking-[0.2em] text-dim">EDUCATION LOAN</h2>
            <p className="num text-xl text-bone">{debt.education_loan.outstanding.text}</p>
            <p className="text-xs text-dim">
              EMI {debt.education_loan.emi.text} · {debt.education_loan.rate_pct}% · payoff {debt.education_loan.payoff_now}
            </p>
          </div>
        </div>
      )}

      {sub === "networth" && liabilities && (
        <div className="rounded-lg border border-line bg-panel p-4">
          {!liabilities.has_data && <p className="text-xs text-dim">no assets/liabilities on file yet</p>}
          {liabilities.has_data && (
            <>
              <header className="mb-3 flex items-baseline justify-between gap-3">
                <h2 className="num text-sm tracking-[0.2em] text-dim">NET WORTH</h2>
                <span className={`num text-xl font-bold ${(liabilities.net_worth.value.raw ?? 0) < 0 ? "text-p5red" : "text-bone"}`}>
                  {liabilities.net_worth.value.text}
                </span>
              </header>
              <p className="num text-xs text-dim">
                assets {liabilities.total_assets.text} · liabilities {liabilities.total_liabilities.text} ·
                {" "}monthly recurring {liabilities.monthly_recurring_liabilities.text}
              </p>
              <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <p className="num mb-1 text-[10px] tracking-widest text-dim">ASSETS</p>
                  {liabilities.assets.map((a) => (
                    <div key={a.name} className="flex justify-between text-xs">
                      <span className="text-bone">{a.name}</span>
                      <span className="num text-dim">{a.value.text}</span>
                    </div>
                  ))}
                </div>
                <div>
                  <p className="num mb-1 text-[10px] tracking-widest text-dim">LIABILITIES</p>
                  {liabilities.liabilities.map((l) => (
                    <div key={l.name} className="flex justify-between text-xs">
                      <span className="text-bone">{l.name}</span>
                      <span className="num text-p5red">{l.value.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
