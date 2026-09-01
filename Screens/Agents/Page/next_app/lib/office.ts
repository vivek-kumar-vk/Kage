"use client";

import { useCallback, useEffect, useState } from "react";

// Self-contained data layer for the Pixel Office (D12) — deliberately independent
// from lib/api.ts so the office and the workspace blocks stay modular (Rule 4).

export type AgentStatus = "idle" | "working" | "stuck";

export interface OfficeDepartment {
  id: string;
  label: string;
  color: string;
}

export interface OfficeAgent {
  name: string;
  role: string;
  department: string;
  tier: "head" | "main" | "sub";
  parent?: string | null;
  room_id: string;
}

export interface OfficeWorkspace {
  state: string;
  departments: OfficeDepartment[];
  agents: OfficeAgent[];
  rooms: { id: string; kind: string; name: string; agent_name: string | null }[];
  counts: { ideas: Record<string, number> };
}

export type OfficeEventType =
  | "started"
  | "thinking"
  | "output"
  | "done"
  | "error"
  | "note";

export interface OfficeEvent {
  id: number | null;
  ts: string;
  source: "run" | "demo" | "board" | "ui";
  sim: 0 | 1;
  agent_name: string | null;
  department: string | null;
  type: OfficeEventType;
  text: string;
  artifact: string | null;
  _at?: number;
}

export interface AgentView {
  status: AgentStatus;
  text: string | null;
  sim: boolean;
  at: number;
}

export function useWorkspace() {
  const [data, setData] = useState<OfficeWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    fetch("/api/agents/workspace")
      .then(async (res) => {
        if (!res.ok) throw new Error(`workspace HTTP ${res.status}`);
        return (await res.json()) as OfficeWorkspace;
      })
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "workspace failed");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  const reload = useCallback(() => setTick((v) => v + 1), []);

  return { data, loading, error, reload };
}

export function useLiveEvents() {
  const [events, setEvents] = useState<OfficeEvent[]>([]);
  const [status, setStatus] = useState<"connecting" | "live" | "offline">("connecting");

  useEffect(() => {
    let closed = false;
    let source: EventSource | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      source = new EventSource("/api/agents/events");

      source.onopen = () => setStatus("live");

      source.onmessage = (msg) => {
        try {
          const parsed = JSON.parse(msg.data) as OfficeEvent;
          parsed._at = Date.now();
          setEvents((prev) => [...prev.slice(-199), parsed]);
        } catch {
          // ignore malformed frames
        }
      };

      source.onerror = () => {
        setStatus("offline");
        source?.close();
        if (!closed) {
          retry = setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      source?.close();
    };
  }, []);

  return { events, status };
}

export function deriveAgentStates(events: OfficeEvent[]): Map<string, AgentView> {
  const map = new Map<string, AgentView>();

  const ensure = (name: string): AgentView => {
    let view = map.get(name);
    if (!view) {
      view = { status: "idle", text: null, sim: false, at: 0 };
      map.set(name, view);
    }
    return view;
  };

  for (const event of events) {
    if (!event.agent_name) continue;

    const view = ensure(event.agent_name);
    const at = event._at ?? 0;

    switch (event.type) {
      case "started":
        view.status = "working";
        view.sim = event.sim === 1;
        view.at = at;
        break;
      case "thinking":
        view.status = "working";
        view.at = Math.max(view.at, at);
        break;
      case "output":
        view.status = "working";
        if (event.text) view.text = event.text;
        view.sim = event.sim === 1;
        view.at = Math.max(view.at, at);
        break;
      case "done":
        view.status = "idle";
        if (event.text) view.text = event.text;
        view.sim = event.sim === 1;
        view.at = Math.max(view.at, at);
        break;
      case "error":
        view.status = "stuck";
        view.text = event.text || "needs attention";
        view.sim = event.sim === 1;
        view.at = Math.max(view.at, at);
        break;
      case "note":
        if (event.text) {
          view.text = event.text;
          view.sim = event.sim === 1;
          view.at = Math.max(view.at, at);
        }
        break;
    }
  }

  return map;
}
