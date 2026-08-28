"use client";

import { CenterCore } from "./components/CenterCore";
import { SystemMetricsPanel } from "./components/SystemMetricsPanel";
import { TodayPanel } from "./components/TodayPanel";
import { TerminalChatPanel } from "./components/TerminalChatPanel";
import { EmailPanel } from "./components/EmailPanel";
import { SkillsDeckPanel } from "./components/SkillsDeckPanel";
import { TopPanel } from "./components/TopPanel";
import { useAgentFleetActivity } from "./components/useAgentFleetActivity";

/** The Main Menu home screen - "Agentic OS" redesign (2026-08-27, second
    pass). An exact-copy layout of the reference image in
    27-08_UI_Plans/Main_Menu_Agentic_OS_Redesign_Plan.md: strict 3
    columns, a rotating agent ring around a decorative particle core in
    the centre. Every panel reuses a fetch this screen already had -
    nothing here invents a new data source. See
    Documentation/Guide_To_Main_Menu_UI_Design.md for the full writeup. */
export default function Home() {
  const { agents, fleetFailed, pulsing, state, rows } = useAgentFleetActivity();

  return (
    <div className="home-grid mx-auto grid w-full max-w-[1400px] gap-4 p-4">
      <div className="flex flex-col gap-4">
        <SystemMetricsPanel />
        <TodayPanel />
        <TerminalChatPanel />
      </div>

      <CenterCore agents={agents} pulsing={pulsing} fleetFailed={fleetFailed} streamState={state} rows={rows} />

      <div className="flex flex-col gap-4">
        <EmailPanel />
        <SkillsDeckPanel />
        <TopPanel />
      </div>

      <footer className="col-span-full pb-2 pt-1">
        <p className="num text-center text-[10px] leading-relaxed text-dim">
          every number traces to its source file &middot; empty means not built
          yet, stated plainly &middot; the centre ring reacts only to real
          trace-ledger events
        </p>
      </footer>
    </div>
  );
}
