"use client";

import { useState } from "react";
import { ActivityRail } from "./components/ActivityRail";
import { TodayPanel } from "./components/TodayPanel";
import { PlanBoard } from "./components/PlanBoard";
import { RecallQueues } from "./components/RecallQueues";

type Tab = "today" | "plan" | "recall";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "today", label: "TODAY" },
  { id: "plan", label: "PLAN" },
  { id: "recall", label: "RECALL" },
];

/** The Learning rebuild - a workflow, not a brochure. Where Models'
    design pass is a control room and Enhancement's is a quiet
    corkboard, this screen is where a session actually happens: the
    Today/Plan/Recall structure (ADR-100 merged Study into Plan)
    stays the spine, so a click gets you into a module's task list or
    a due card fast, not through a dashboard first. Every figure comes
    from this screen's own existing endpoints - no second source of
    truth, nothing invented. */
export default function Home() {
  const [tab, setTab] = useState<Tab>("today");

  return (
    <div className="flex min-h-screen flex-col">
      <header className="page-header border-b border-line bg-panel">
        <div className="header-pad mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
          <h1 className="page-title font-mono text-2xl font-black tracking-tight text-jade">
            LEARNING <span className="font-light text-bone">// TODAY · PLAN · RECALL</span>
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
            {tab === "today" && <TodayPanel />}
            {tab === "plan" && <PlanBoard />}
            {tab === "recall" && <RecallQueues />}
          </div>
          <div className="rail flex flex-col gap-6">
            <ActivityRail />
          </div>
        </div>
      </main>

      <footer className="mx-auto w-full max-w-6xl px-6 pb-6 pt-2">
        <p className="num text-[10px] leading-relaxed text-dim">
          every figure traces to server_for_learning.py's own endpoints · empty means not
          studied/planned yet, stated plainly
          {" · events stream from Shared_By_All_Screens/Trace_Ledger via /api/learning/live"}
        </p>
      </footer>
    </div>
  );
}
