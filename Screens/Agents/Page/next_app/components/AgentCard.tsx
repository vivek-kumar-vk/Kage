"use client";

import type { Agent } from "../lib/api";

export default function AgentCard({ agent }: { agent: Agent }) {
  return (
    <section className="deck-panel flex h-full min-h-0 flex-col gap-3 p-4">
      <header>
        <p className="section-label">Agent card</p>

        <div className="mt-1 flex items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-deck-text">{agent.name}</h2>

          {agent.name === "Agent_Head" ? (
            <span className="border border-deck-copper px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-deck-copper">
              Lead
            </span>
          ) : null}
        </div>
      </header>

      <div className="flex items-center gap-2 text-xs text-deck-dim">
        <span className="status-dot status-dot-idle" aria-hidden="true" />
        <span>idle</span>
      </div>

      <p className="text-sm text-deck-text">
        {agent.role || "No role description yet."}
      </p>

      <div className="mt-auto border border-deck-line bg-deck-raised p-3 text-xs text-deck-dim">
        Rooms, messaging, and model wiring land in V2.
      </div>
    </section>
  );
}
