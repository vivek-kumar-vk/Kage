"use client";

import { useEffect, useRef, useState } from "react";
import { useLiveEvents } from "./useLiveEvents";

export interface AgentEntry {
  name: string;
  what_i_am_for: string;
  state: string;
}

/** "Portfolio_Analyst_Agent" in a card and "portfolio_analyst" in the
    ledger are the same actor - match on the stem, never guess harder. */
function actor_stem(name: string): string {
  return name.toLowerCase().replace(/_agent$/, "");
}

/** The real fleet roster + the live SSE trace stream + which agent, if
    any, just did something real. Lifted out of the old
    AgentActivityPanel.tsx so the ring (AgentRing.tsx) has one fetch and
    one EventSource instead of opening its own. `rows`/`state` are kept
    on the return value for whatever next reads the raw trace stream -
    nothing in the current panel set displays them directly since the
    Agentic-OS second pass (2026-08-27) moved the log display to
    EmailPanel's slot; only `pulsing` drives the ring today. */
export function useAgentFleetActivity() {
  const { rows, state } = useLiveEvents("/api/main_menu/live");
  const [agents, setAgents] = useState<AgentEntry[] | null>(null);
  const [fleetFailed, setFleetFailed] = useState(false);
  const [pulsing, setPulsing] = useState<Record<string, boolean>>({});
  const lastSeq = useRef<number | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/main_menu/agents/fleet")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((body) => {
        if (cancelled) return;
        const list: AgentEntry[] = [];
        for (const section of body.sections ?? []) {
          for (const agent of section.agents ?? []) list.push(agent);
        }
        setAgents(list);
      })
      .catch(() => {
        if (!cancelled) setFleetFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const newest = rows[rows.length - 1];
    if (!newest || newest.seq === undefined) return;
    if (lastSeq.current !== undefined && newest.seq <= lastSeq.current) return;
    lastSeq.current = newest.seq;
    if (!agents) return;
    const hits: Record<string, boolean> = {};
    for (const agent of agents) {
      if ((newest.actor ?? "").toLowerCase() === actor_stem(agent.name)) {
        hits[agent.name] = true;
      }
    }
    if (Object.keys(hits).length === 0) return;
    setPulsing((p) => ({ ...p, ...hits }));
    const t = setTimeout(
      () =>
        setPulsing((p) => {
          const next = { ...p };
          for (const k of Object.keys(hits)) delete next[k];
          return next;
        }),
      950,
    );
    return () => clearTimeout(t);
  }, [rows, agents]);

  return { agents, fleetFailed, rows, state, pulsing };
}
