"use client";

import { useCallback, useEffect, useState } from "react";

export interface Comment {
  id: string;
  text: string;
  author: "user" | "ai";
  created_at: string;
}
export interface Idea {
  id: string;
  key: string;
  title: string;
  note: string;
  area: string;
  source: "user" | "ai";
  status: "ideas" | "todo" | "in_progress" | "done";
  priority: "low" | "medium" | "high" | "critical";
  order_index: number;
  added_at: string;
  updated_at: string;
  comments: Comment[];
}

export type IdeasState = "loading" | "fresh" | "error";

/** The board's own read route, GET /api/enhancement/ideas, which
    answers {built, ideas}. No second endpoint exists and none is
    invented here - every count on this page is counted client-side
    off this one real list. */
export function useIdeas() {
  const [ideas, setIdeas] = useState<Idea[] | null>(null);
  const [state, setState] = useState<IdeasState>("loading");
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/enhancement/ideas")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setIdeas(Array.isArray(body.ideas) ? body.ideas : []);
        setFetchedAt(new Date());
        setState("fresh");
      })
      .catch(() => {
        setState("error");
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { ideas, state, fetchedAt, reload: load };
}
