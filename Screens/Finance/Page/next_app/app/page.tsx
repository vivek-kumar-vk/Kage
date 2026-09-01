"use client";

import { useState } from "react";
import { OverviewPanel } from "./components/OverviewPanel";
import { InvestmentsPanel } from "./components/InvestmentsPanel";
import { DebtPanel } from "./components/DebtPanel";
import { PortfolioPanel } from "./components/PortfolioPanel";
import { PaddockNav } from "./components/PaddockNav";
import { TelemetryPanel } from "./components/TelemetryPanel";
import { SakuraLayer } from "./components/SakuraLayer";
import { motion } from "framer-motion";

type Tab = "overview" | "investments" | "debt" | "portfolio" | "telemetry";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "OVERVIEW" },
  { id: "investments", label: "INVESTMENTS" },
  { id: "debt", label: "DEBT" },
  { id: "portfolio", label: "PORTFOLIO" },
  { id: "telemetry", label: "TELEMETRY" },
];

/** The Finance rebuild — real money, legibility over flourish. A paddock
    shell (nav + header) carries a per-tab team accent: Ferrari livery on
    Overview, Red Bull livery on Investments; the others inherit. Seed data
    for now — PLANNED_WORK.md P8. */
export default function Home() {
  const [tab, setTab] = useState<Tab>("overview");
  const livery = tab === "investments" ? "liv-rb" : "liv-ferrari";

  return (
    <div className="relative flex min-h-screen flex-col">
      <SakuraLayer livery={livery} />

      <header className="page-header border-b border-line/40 bg-transparent">
        <div className="header-pad mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
          <h1 className="page-title font-mono text-2xl font-black tracking-tight text-bone">
            FINANCE
          </h1>
        </div>
      </header>

      <main className="page-main mx-auto w-full max-w-6xl flex-1 px-6 py-6">
        <div className={`grid-main ${livery} grid grid-cols-[168px_1fr] gap-6`}>
          <PaddockNav items={TABS} tab={tab} onSelect={(id) => setTab(id as Tab)} />
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-6"
          >
            {tab === "overview" && <OverviewPanel />}
            {tab === "investments" && <InvestmentsPanel />}
            {tab === "debt" && <DebtPanel />}
            {tab === "portfolio" && <PortfolioPanel />}
            {tab === "telemetry" && <TelemetryPanel />}
          </motion.div>
        </div>
      </main>
    </div>
  );
}
