"use client";

import { useMemo, useState } from "react";
import type { AgentView, OfficeAgent, OfficeDepartment } from "../../lib/office";

export type DeckSelection =
  | { kind: "agent"; id: string }
  | { kind: "room"; id: string };

const TIER_RANK: Record<string, number> = { head: 0, main: 1, sub: 2 };
const COLLAPSE_KEY = "deck.collapsed-parents";

function readCollapsed(): Set<string> {
  try {
    const raw = localStorage.getItem(COLLAPSE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? new Set(parsed as string[]) : new Set();
  } catch {
    return new Set();
  }
}

function writeCollapsed(set: Set<string>) {
  try {
    localStorage.setItem(COLLAPSE_KEY, JSON.stringify([...set]));
  } catch {
    // private mode / storage full: collapse state just won't persist
  }
}

function presenceClass(states: Map<string, AgentView>, name: string) {
  const status = states.get(name)?.status;
  if (status === "working") return "presence presence-working";
  if (status === "stuck") return "presence presence-stuck";
  if (status === "idle") return "presence presence-idle";
  return "presence presence-off";
}

function UnreadBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="unread-badge ml-auto" aria-label={`${count} unread`}>
      {count > 99 ? "99+" : count}
    </span>
  );
}

interface CrewRow {
  main: OfficeAgent;
  subs: OfficeAgent[];
}

interface Props {
  departments: OfficeDepartment[];
  agents: OfficeAgent[];
  states: Map<string, AgentView>;
  unread: Map<string, number>;
  selection: DeckSelection;
  onSelectAgent: (name: string) => void;
  onSelectRoom: (id: string) => void;
}

/** Left rail: rooms + the roster grouped by department, collapsible by parent —
 * each main agent heads its own crew of subs. Unread counts are Slack-style
 * numeric badges (no blinking). */
export default function DeckRail({
  departments,
  agents,
  states,
  unread,
  selection,
  onSelectAgent,
  onSelectRoom,
}: Props) {
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(readCollapsed);
  const searching = query.trim().length > 0;

  const toggleCollapse = (parent: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(parent)) next.delete(parent);
      else next.add(parent);
      writeCollapsed(next);
      return next;
    });
  };

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    return departments
      .map((dept) => {
        const members = agents
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
          );

        // Crews: every main is a collapsible header over its own subs.
        const heads = members.filter((agent) => agent.tier === "head");
        const mains = members.filter((agent) => agent.tier === "main");
        const subsByParent = new Map<string, OfficeAgent[]>();
        const orphanSubs: OfficeAgent[] = [];
        for (const agent of members) {
          if (agent.tier !== "sub") continue;
          if (agent.parent && mains.some((main) => main.name === agent.parent)) {
            const list = subsByParent.get(agent.parent) ?? [];
            list.push(agent);
            subsByParent.set(agent.parent, list);
          } else {
            orphanSubs.push(agent);
          }
        }

        const crews: CrewRow[] = mains.map((main) => ({
          main,
          subs: subsByParent.get(main.name) ?? [],
        }));

        return { dept, heads, crews, orphanSubs };
      })
      .filter(
        (group) =>
          group.heads.length > 0 || group.crews.length > 0 || group.orphanSubs.length > 0
      );
  }, [agents, departments, query]);

  const agentRow = (agent: OfficeAgent, indent = false) => {
    const active = selection.kind === "agent" && selection.id === agent.name;
    const view = states.get(agent.name);
    const count = unread.get(agent.name) ?? 0;
    return (
      <button
        key={agent.name}
        type="button"
        className={`rail-row${active ? " rail-row-active" : ""}${indent ? " rail-row-sub" : ""}`}
        onClick={() => onSelectAgent(agent.name)}
        title={agent.role}
      >
        <span className={presenceClass(states, agent.name)} aria-hidden="true" />
        <span className="truncate">{agent.name.replace(/_Agent$/, "")}</span>
        {view?.sim ? <span className="sim-tag ml-1">SIM</span> : null}
        <UnreadBadge count={count} />
      </button>
    );
  };

  const crewBlock = (crew: CrewRow) => {
    const isCollapsed = !searching && collapsed.has(crew.main.name);
    const crewUnread =
      crew.subs.reduce((sum, sub) => sum + (unread.get(sub.name) ?? 0), 0) +
      (unread.get(crew.main.name) ?? 0);
    const active = selection.kind === "agent" && selection.id === crew.main.name;
    const view = states.get(crew.main.name);
    const count = isCollapsed ? crewUnread : unread.get(crew.main.name) ?? 0;

    return (
      <div key={crew.main.name}>
        <div className={`rail-row rail-row-main${active ? " rail-row-active" : ""}`}>
          <button
            type="button"
            className="rail-row-label"
            onClick={() => onSelectAgent(crew.main.name)}
            title={crew.main.role}
          >
            <span className={presenceClass(states, crew.main.name)} aria-hidden="true" />
            <span className="truncate">{crew.main.name.replace(/_Agent$/, "")}</span>
            {view?.sim ? <span className="sim-tag ml-1">SIM</span> : null}
            <UnreadBadge count={count} />
          </button>
          {crew.subs.length > 0 ? (
            <button
              type="button"
              className={`rail-chevron${isCollapsed ? " rail-chevron-closed" : ""}`}
              onClick={() => toggleCollapse(crew.main.name)}
              aria-label={isCollapsed ? `Expand ${crew.main.name}` : `Collapse ${crew.main.name}`}
              aria-expanded={!isCollapsed}
            >
              ▾
            </button>
          ) : null}
        </div>
        {!isCollapsed ? crew.subs.map((sub) => agentRow(sub, true)) : null}
      </div>
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
        {roomRow("board", "board-room", selection, onSelectRoom)}
        {roomRow("runs", "runs", selection, onSelectRoom)}

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
            {group.heads.map((agent) => agentRow(agent))}
            {group.crews.map((crew) => crewBlock(crew))}
            {group.orphanSubs.map((agent) => agentRow(agent, true))}
          </div>
        ))}

        {grouped.length === 0 ? (
          <p className="px-3 py-4 text-xs text-deck-dim">No agents match “{query}”.</p>
        ) : null}
      </div>
    </div>
  );
}

function roomRow(
  id: string,
  label: string,
  selection: DeckSelection,
  onSelectRoom: (id: string) => void
) {
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
}
