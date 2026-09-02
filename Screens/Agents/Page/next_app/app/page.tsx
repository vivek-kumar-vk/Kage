"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  deriveAgentStates,
  deriveWalkIns,
  useLiveEvents,
  useWorkspace,
} from "../lib/office";

// The stage measures its container and owns a canvas, so it stays client-only.
const PixelOffice = dynamic(() => import("../components/office/PixelOffice"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center">
      <p className="section-label">Lighting the office…</p>
    </div>
  ),
});

export default function OfficePage() {
  const workspace = useWorkspace();
  const { events, status } = useLiveEvents();
  const states = useMemo(() => deriveAgentStates(events), [events]);
  const walkIns = useMemo(() => deriveWalkIns(events), [events]);

  const [selected, setSelected] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const latest = events.length > 0 ? events[events.length - 1] : null;

  const liveDot =
    status === "live"
      ? "status-dot status-dot-running"
      : status === "offline"
        ? "status-dot"
        : "status-dot status-dot-idle";
  const liveDotStyle =
    status === "offline" ? { background: "var(--deck-alert)" } : undefined;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between gap-3 border-b-2 border-deck-line bg-deck-panel px-4 py-2">
        <div className="flex items-center gap-4">
          <span className="deck-wordmark text-sm">RUBRIC / AGENTS</span>
          <nav className="px-tabs" aria-label="Surfaces">
            <span className="px-tab px-tab-active" aria-current="page">
              PIX-AGENTS
            </span>
            <a href="/workspace" className="px-tab">
              AGENT DECK
            </a>
          </nav>
        </div>

        <div className="flex min-w-0 items-center gap-3">
          {latest ? (
            <span className={`event-line${latest.sim ? " event-line-sim" : ""}`}>
              {latest.sim ? "SIM · " : ""}
              {latest.agent_name ? `${latest.agent_name} — ` : ""}
              {latest.text || latest.type}
            </span>
          ) : null}
          <span className="flex items-center gap-2 text-xs text-deck-dim">
            <span className={liveDot} style={liveDotStyle} />
            {status}
          </span>
        </div>
      </header>

      <main className="relative min-h-0 flex-1 overflow-hidden">
        <PixelOffice
          agents={workspace.data?.agents ?? []}
          departments={workspace.data?.departments ?? []}
          states={states}
          walkIns={walkIns}
          selected={selected}
          onSelect={(name) => setSelected(name || null)}
          now={now}
        />

        {!workspace.loading && !workspace.error && (workspace.data?.agents.length ?? 0) === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="px-panel p-6 text-sm text-deck-dim">
              No agents yet — add a profile folder under
              <code className="mx-1 text-deck-text">Screens/Agents/AI_Agents/</code>
              and it gets a desk automatically.
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
