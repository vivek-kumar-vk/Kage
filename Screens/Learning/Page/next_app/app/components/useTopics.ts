"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

export interface TopicGroup {
  group: string;
  topics: Array<{ id: string; topic: string; status?: string }>;
}

export interface TrackBook {
  groups: TopicGroup[];
  progress: { done: number; total: number; pct: number };
}

export interface TopicsPayload {
  trackA: TrackBook;
  trackB: TrackBook;
}

/** GET /api/learning/topics - the two-track topic board, seeded
    verbatim from the owner's own contract file. */
export function useTopics() {
  const [data, setData] = useState<TopicsPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/learning/topics")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setData(body as TopicsPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { data, state, reload: load };
}
