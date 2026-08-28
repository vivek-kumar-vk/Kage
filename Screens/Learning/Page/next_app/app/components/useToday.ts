"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

export interface TodaySchedule {
  date: string;
  day_name: string;
  track_a: string;
  track_b: string;
  kind: string;
  chunks: Array<{ label?: string; minutes?: number }>;
  evening: unknown;
  note: string;
  day_done: boolean;
  week_found: boolean;
  week_num: number | null;
  focus_a: string;
  focus_b: string;
  target_minutes: number | null;
}

export interface RecentActivityRow {
  date: string;
  minutes: number;
  topic: string;
  notes: string;
  capture: string;
}

export interface TodayPayload {
  streak: { days: number; last_studied: string | null };
  schedule: TodaySchedule;
  recent_activity: RecentActivityRow[];
  checklist: Record<string, boolean>;
  running_session: unknown;
  due_cards: number;
  due_notes: number;
}

/** GET /api/learning/today - streak, today's planned schedule, the
    three-box checklist, both recall queues' due counts. One real
    endpoint, read verbatim - no field renamed, nothing invented. */
export function useToday() {
  const [data, setData] = useState<TodayPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/learning/today")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setData(body as TodayPayload);
        setFetchedAt(new Date());
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const setChecklistKey = useCallback((key: string, value: boolean) => {
    setData((prev) =>
      prev ? { ...prev, checklist: { ...prev.checklist, [key]: value } } : prev
    );
    fetch("/api/learning/checklist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    })
      .then((r) => r.json())
      .then(() => load())
      .catch(() => load());
  }, [load]);

  return { data, state, fetchedAt, reload: load, setChecklistKey };
}
