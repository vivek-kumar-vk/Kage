"use client";

import { useEffect, useRef, useState } from "react";

/** One trace-ledger row, exactly as the ledger writes it.
    Absent keys stay absent - a reader tolerates absence, never guesses. */
export interface TraceRow {
  ts?: string;
  actor?: string;
  kind?: string;
  action?: string;
  target?: string;
  outcome?: string;
  seq?: number;
  correlation_id?: string;
}

export type StreamState =
  | "connecting"
  | "live"
  | "reconnecting"
  | "offline";

const MAX_ROWS = 40;

/** The screen's own SSE stream at /api/enhancement/live - real trace
    rows, replayed from the top of today's ledger on connect, then
    live. The connection state is reported honestly; EventSource
    reconnects on its own and we only report what we know. Same shape
    as Main_Menu's hook (Phase 12.3) because the wire contract is the
    same one every screen's SSE endpoint speaks. */
export function useLiveEvents(url: string) {
  const [rows, setRows] = useState<TraceRow[]>([]);
  const [state, setState] = useState<StreamState>("connecting");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    const es = new EventSource(url);
    sourceRef.current = es;

    es.onopen = () => {
      if (!cancelled) setState("live");
    };
    es.onerror = () => {
      if (!cancelled) setState("reconnecting");
    };
    es.onmessage = (e) => {
      try {
        const row = JSON.parse(e.data) as TraceRow;
        setRows((prev) => {
          const next = [...prev, row];
          return next.length > MAX_ROWS ? next.slice(-MAX_ROWS) : next;
        });
      } catch {
        // A frame we cannot parse is dropped, not invented around.
      }
    };

    return () => {
      cancelled = true;
      es.close();
    };
  }, [url]);

  return { rows, state };
}
