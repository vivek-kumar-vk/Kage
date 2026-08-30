"use client";

import type { Agent, Room, Selection, Workspace } from "../lib/api";

function isSelected(selected: Selection, kind: Selection["kind"], id: string): boolean {
  return selected.kind === kind && selected.id === id;
}

export default function Navigator({
  workspace,
  selected,
  onSelect,
}: {
  workspace: Workspace;
  selected: Selection;
  onSelect: (selection: Selection) => void;
}) {
  const rooms = workspace.rooms;

  const agents = [...workspace.agents].sort((a, b) => {
    if (a.name === "Agent_Head") return -1;
    if (b.name === "Agent_Head") return 1;
    return a.name.localeCompare(b.name, undefined, { numeric: true });
  });

  const boardCount =
    workspace.counts.ideas.ideas +
    workspace.counts.ideas.todo +
    workspace.counts.ideas.in_progress +
    workspace.counts.ideas.done;

  return (
    <nav className="deck-panel flex h-full min-h-0 flex-col gap-5 p-4">
      <header>
        <p className="section-label">Workspace</p>
        <h1 className="deck-wordmark mt-1 text-lg">[AGENT DECK]</h1>
      </header>

      <section>
        <p className="section-label">Rooms</p>
        <div className="mt-2 flex flex-col gap-1">
          {rooms.length === 0 ? (
            <p className="text-sm text-deck-dim">No rooms yet.</p>
          ) : (
            rooms.map((room: Room) => {
              const active = isSelected(selected, "room", room.id);

              return (
                <button
                  key={room.id}
                  type="button"
                  onClick={() => onSelect({ kind: "room", id: room.id })}
                  className={`nav-row ${active ? "nav-row-active" : ""}`}
                  aria-current={active ? "page" : undefined}
                >
                  <span>{room.name}</span>

                  {room.id === "board" ? (
                    <span className="num text-xs text-deck-dim">{boardCount}</span>
                  ) : null}
                </button>
              );
            })
          )}
        </div>
      </section>

      <section>
        <p className="section-label">Agents</p>
        <div className="mt-2 flex flex-col gap-1">
          {agents.length === 0 ? (
            <p className="text-sm text-deck-dim">No agents yet.</p>
          ) : (
            agents.map((agent: Agent) => {
              const active = isSelected(selected, "agent", agent.name);

              return (
                <button
                  key={agent.name}
                  type="button"
                  onClick={() => onSelect({ kind: "agent", id: agent.name })}
                  className={`nav-row ${active ? "nav-row-active" : ""}`}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="flex items-center gap-2">
                    <span className="status-dot status-dot-idle" aria-hidden="true" />
                    <span>{agent.name}</span>
                  </span>

                  <span className="text-xs text-deck-dim">idle</span>
                </button>
              );
            })
          )}
        </div>
      </section>
    </nav>
  );
}
