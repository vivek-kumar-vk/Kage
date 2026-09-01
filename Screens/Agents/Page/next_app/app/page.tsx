"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import RoomTabs from "../components/office/RoomTabs";
import DeskChat from "../components/office/DeskChat";
import {
  deriveAgentStates,
  useLiveEvents,
  useWorkspace,
  type OfficeAgent,
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

  const [tab, setTab] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [reloadSignal, setReloadSignal] = useState(0);

  const seenRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // New run events for the selected agent refresh its chat.
  useEffect(() => {
    for (const event of events) {
      if (event.id == null || seenRef.current.has(event.id)) continue;
      seenRef.current.add(event.id);
      if (
        event.agent_name === selected &&
        (event.type === "started" || event.type === "done" || event.type === "error")
      ) {
        setReloadSignal((value) => value + 1);
      }
    }
  }, [events, selected]);

  const selectedAgent: OfficeAgent | null =
    (selected && workspace.data?.agents.find((a) => a.name === selected)) || null;

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
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between gap-3 border-b border-deck-line bg-deck-panel px-4 py-2">
        <span className="deck-wordmark text-sm">[AGENT DECK] · PIXEL OFFICE</span>

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
          <a href="/workspace" className="office-pill office-pill-inline">
            Workspace →
          </a>
        </div>
      </header>

      <RoomTabs
        departments={workspace.data?.departments ?? []}
        selected={tab}
        onSelect={setTab}
      />

      <main className="relative min-h-0 flex-1 overflow-hidden">
        <PixelOffice
          agents={workspace.data?.agents ?? []}
          departments={workspace.data?.departments ?? []}
          states={states}
          tab={tab}
          selected={selected}
          onSelect={(name) => setSelected(name || null)}
          now={now}
        />

        {!workspace.loading && !workspace.error && (workspace.data?.agents.length ?? 0) === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="deck-panel p-6 text-sm text-deck-dim">
              No agents yet — add a profile folder under
              <code className="mx-1 text-deck-text">Screens/Agents/AI_Agents/</code>
              and it gets a desk automatically.
            </div>
          </div>
        ) : null}
      </main>

      {selectedAgent ? (
        <DeskChat
          agent={selectedAgent}
          onClose={() => setSelected(null)}
          reloadSignal={reloadSignal}
        />
      ) : null}
    </div>
  );
}
