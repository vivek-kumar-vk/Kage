"use client";

import { useCallback, useEffect, useState } from "react";

// Data for the home-page agent ring: one node per real agent, read from
// the menu's own backend proxy (which reads the Agent Deck over HTTP).
// The menu frontend never talks to another screen directly.

export interface AgentNode {
  name: string;
  role: string;
  department: string;
  tier: "head" | "main" | "sub";
  parent?: string | null;
  model?: string | null;
  unread: number;
}

export interface AgentRosterResponse {
  state: string;
  agents: AgentNode[];
  deck_url?: string;
  unread_total?: number;
  note?: string;
}

export function useAgentRoster(pollMs = 30000) {
  const [data, setData] = useState<AgentRosterResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    fetch("/api/main_menu/agents")
      .then(async (res) => {
        if (!res.ok) throw new Error(`agents HTTP ${res.status}`);
        return (await res.json()) as AgentRosterResponse;
      })
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch(() => {
        // keep last known data; the ring degrades to its offline note
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    refresh();
    if (pollMs > 0) {
      const timer = setInterval(refresh, pollMs);
      return () => clearInterval(timer);
    }
  }, [refresh, pollMs]);

  return { data, loading, refresh };
}
