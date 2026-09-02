"use client";

import { useMemo, useState } from "react";
import type { AgentView, OfficeAgent, OfficeDepartment } from "../../lib/office";

export type DeckSelection =
  | { kind: "agent"; id: string }
  | { kind: "room"; id: string };

const TIER_RANK: Record<string, number> = { head: 0, main: 1, sub: 2 };

function presenceClass(states: Map<string, AgentView>, name: string) {
  const status = states.get(name)?.status;
  if (status === "working") return "presence presence-working";
  if (status === "stuck") return "presence presence-stuck";
  if (status === "idle") return "presence presence-idle";
  return "presence presence-off";
}

interface Props {
  departments: OfficeDepartment[];
  agents: OfficeAgent[];
  states: Map<string, AgentView>;
  selection: DeckSelection;
  onSelectAgent: (name: string) => void;
  onSelectRoom: (id: string) => void;
}

/** Left rail: rooms + the roster grouped by department with live presence. */
export default function DeckRail({
  departments,
  agents,
  states,
  selection,
  onSelectAgent,
  onSelectRoom,
}: Props) {
  const [query, setQuery] = useState("");

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    return departments
      .map((dept) => ({
        dept,
        members: agents
          .filter((agent) => agent.department === dept.id)
          .filter(
            (agent) =>
              !q ||
              agent.name.toLowerCase().includes(q) ||
              agent.role.toLowerCase().includes(q)
          )
          .slice()
          .sort(
            (a, b) =>
              (TIER_RANK[a.tier] ?? 3) - (TIER_RANK[b.tier] ?? 3) ||
              a.name.localeCompare(b.name)
          ),
      }))
      .filter((group) => group.members.length > 0);
  }, [agents, departments, query]);

  const roomRow = (id: string, label: string) => {
    const active = selection.kind === "room" && selection.id === id;
    return (
      <button
        key={id}
        type="button"
        className={`rail-row${active ? " rail-row-active" : ""}`}
        onClick={() => onSelectRoom(id)}
      >
        <span className="rail-hash">#</span>
        <span className="truncate">{label}</span>
      </button>
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b-2 border-deck-line p-2">
        <input
          className="px-input w-full"
          type="search"
          placeholder="search agents…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search agents"
        />
      </div>

      <div className="deck-scroll min-h-0 flex-1 pb-4">
        <p className="rail-section-label">Rooms</p>
        {roomRow("board", "board-room")}
        {roomRow("runs", "runs")}

        {grouped.map((group) => (
          <div key={group.dept.id}>
            <p className="rail-section-label flex items-center gap-2">
              <span
                className="inline-block h-2 w-2"
                style={{ background: group.dept.color }}
                aria-hidden="true"
              />
              {group.dept.label}
            </p>
            {group.members.map((agent) => {
              const active = selection.kind === "agent" && selection.id === agent.name;
              const view = states.get(agent.name);
              return (
                <button
                  key={agent.name}
                  type="button"
                  className={`rail-row${active ? " rail-row-active" : ""}`}
                  onClick={() => onSelectAgent(agent.name)}
                  title={agent.role}
                >
                  <span className={presenceClass(states, agent.name)} aria-hidden="true" />
                  <span className="truncate">{agent.name.replace(/_Agent$/, "")}</span>
                  {view?.sim ? <span className="sim-tag ml-auto">SIM</span> : null}
                </button>
              );
            })}
          </div>
        ))}

        {grouped.length === 0 ? (
          <p className="px-3 py-4 text-xs text-deck-dim">No agents match “{query}”.</p>
        ) : null}
      </div>
    </div>
  );
}
