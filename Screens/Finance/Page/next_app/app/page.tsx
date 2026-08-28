"use client";

import { useState } from "react";
import { ActivityRail } from "./components/ActivityRail";
import { OverviewPanel } from "./components/OverviewPanel";
import { InvestmentsPanel } from "./components/InvestmentsPanel";
import { DebtPanel } from "./components/DebtPanel";
import { PortfolioPanel } from "./components/PortfolioPanel";

type Tab = "overview" | "investments" | "debt" | "portfolio";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "OVERVIEW" },
  { id: "investments", label: "INVESTMENTS" },
  { id: "debt", label: "DEBT" },
  { id: "portfolio", label: "PORTFOLIO" },
];

/** The Finance rebuild - real money, legibility over flourish. Where
    Models' design pass is a control room and Learning's is a workflow,
    this screen prioritizes honesty of state above everything: a failed
    gate stays red, the health score stays whatever it actually is, an
    [UNVERIFIED] badge stays visible. C4 (every number traces to a
    source) and C5 (never recommend a buy/sell) apply to every pixel
    here - nothing on this page invents a figure or softens a result. */
export default function Home() {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div className="flex min-h-screen flex-col">
      <header className="page-header border-b border-line bg-panel">
        <div className="header-pad mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
          <h1 className="page-title font-mono text-2xl font-black tracking-tight text-jade">
            FINANCE <span className="font-light text-bone">// OVERVIEW · INVESTMENTS · DEBT · PORTFOLIO</span>
          </h1>
          <nav className="tab-strip flex gap-2">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`num rounded border px-3 py-1.5 text-xs tracking-widest transition-colors ${
                  tab === t.id
                    ? "border-jade text-jade"
                    : "border-line text-dim hover:border-cyan hover:text-cyan"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="page-main mx-auto w-full max-w-6xl flex-1 px-6 py-6">
        <div className="grid-main grid grid-cols-[1fr_300px] gap-6">
          <div className="flex flex-col gap-6">
            {tab === "overview" && <OverviewPanel />}
            {tab === "investments" && <InvestmentsPanel />}
            {tab === "debt" && <DebtPanel />}
            {tab === "portfolio" && <PortfolioPanel />}
          </div>
          <div className="rail flex flex-col gap-6">
            <ActivityRail />
          </div>
        </div>
      </main>

      <footer className="mx-auto w-full max-w-6xl px-6 pb-6 pt-2">
        <p className="num text-[10px] leading-relaxed text-dim">
          every figure traces to server_for_finance.py&apos;s own endpoints (C4) · never a buy/sell
          recommendation (C5) · empty means not recorded yet, stated plainly
          {" · events stream from Shared_By_All_Screens/Trace_Ledger via /api/finance/live"}
        </p>
      </footer>
    </div>
  );
}
