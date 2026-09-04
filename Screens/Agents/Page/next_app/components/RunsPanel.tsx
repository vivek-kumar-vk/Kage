"use client";

import { useEffect, useState } from "react";
import type { OfficeEvent } from "../lib/office";

interface Run {
  id: number;
  agent_name: string;
  department: string | null;
  prompt: string;
  reply: string | null;
  model: string | null;
  status: "running" | "ok" | "error";
  problem: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  started_at: string | null;
  duration_ms: number | null;
}

interface RunsResponse {
  state: string;
  runs: Run[];
  note?: string;
}

function clockOf(iso: string | null) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

interface Stats {
  total: number;
  errors: number;
  errorRate: number | null;
  avgDurationMs: number | null;
}

/** Computed from whatever page the RUNS list is currently showing (up to 50
 * most recent) — an honest snapshot of that window, not a lifetime metric
 * the backend doesn't track (PLAN item 7). */
function statsOf(runs: Run[]): Stats {
  const closed = runs.filter((r) => r.status !== "running");
  const errors = closed.filter((r) => r.status === "error").length;
  const durations = closed
    .map((r) => r.duration_ms)
    .filter((d): d is number => d !== null);
  return {
    total: closed.length,
    errors,
    errorRate: closed.length ? (errors / closed.length) * 100 : null,
    avgDurationMs: durations.length
      ? Math.round(durations.reduce((s, d) => s + d, 0) / durations.length)
      : null,
  };
}

/** Live RUNS panel (V2) — refreshes off the SSE done/error events already
 * flowing through the page, since a run only ever closes on one of those two
 * event types; a 4s poll would just re-read the same row most of the time. */
export default function RunsPanel({ events }: { events: OfficeEvent[] }) {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const closedCount = events.filter((e) => e.type === "done" || e.type === "error").length;

  useEffect(() => {
    let cancelled = false;

    fetch("/api/agents/runs?limit=50")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<RunsResponse>;
      })
      .then((data) => {
        if (!cancelled) setRuns(data.runs ?? []);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "runs failed");
          setRuns([]);
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closedCount]);

  const stats = runs ? statsOf(runs) : null;

  return (
    <section className="deck-panel flex h-full min-h-0 flex-col gap-3 p-4">
      <p className="section-label">System room</p>
      <h2 className="text-lg font-semibold text-deck-text">Runs</h2>

      {stats && stats.total > 0 ? (
        <div className="px-panel flex items-center gap-5 p-3 text-xs">
          <div>
            <div className="text-deck-dim">Runs (window)</div>
            <div className="font-mono text-deck-text">{stats.total}</div>
          </div>
          <div>
            <div className="text-deck-dim">Error rate</div>
            <div
              className="font-mono"
              style={
                stats.errorRate && stats.errorRate > 0
                  ? { color: "var(--deck-alert)" }
                  : undefined
              }
            >
              {stats.errorRate === null ? "—" : `${stats.errorRate.toFixed(0)}%`}
            </div>
          </div>
          <div>
            <div className="text-deck-dim">Avg latency</div>
            <div className="font-mono text-deck-text">
              {stats.avgDurationMs === null ? "—" : `${stats.avgDurationMs}ms`}
            </div>
          </div>
        </div>
      ) : null}

      {runs === null ? (
        <p className="text-sm text-deck-dim">Loading…</p>
      ) : error ? (
        <p className="text-sm" style={{ color: "var(--deck-alert)" }}>
          {error}
        </p>
      ) : runs.length === 0 ? (
        <p className="text-sm text-deck-dim">No runs yet.</p>
      ) : (
        <div className="deck-scroll flex min-h-0 flex-1 flex-col gap-2">
          {runs.map((run) => (
            <div key={run.id} className="px-panel flex flex-col gap-1 p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-display text-deck-text">
                  {run.agent_name.replace(/_Agent$/, "")}
                </span>
                <span
                  className={
                    run.status === "ok"
                      ? "text-xs"
                      : run.status === "error"
                        ? "text-xs"
                        : "text-xs text-deck-dim"
                  }
                  style={run.status === "error" ? { color: "var(--deck-alert)" } : undefined}
                >
                  {run.status}
                </span>
              </div>
              <p className="truncate text-deck-dim">{run.prompt}</p>
              {run.status === "error" ? (
                <p style={{ color: "var(--deck-alert)" }}>{run.problem}</p>
              ) : null}
              <div className="flex items-center gap-2 text-xs text-deck-dim">
                <span>{clockOf(run.started_at)}</span>
                {run.model ? <span>· {run.model}</span> : null}
                {run.duration_ms != null ? <span>· {run.duration_ms}ms</span> : null}
                {run.tokens_in != null && run.tokens_out != null ? (
                  <span>
                    · {run.tokens_in}+{run.tokens_out} tok
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
