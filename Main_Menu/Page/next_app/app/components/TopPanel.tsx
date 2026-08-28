"use client";

import { useEffect, useState } from "react";

interface ModelStatus {
  listening: boolean;
  started_by_governor: boolean;
  pending_request: boolean;
  launcher: string;
}
interface GovernorPayload {
  has_data: boolean;
  reason?: string;
  checked_at?: string;
  models?: Record<string, ModelStatus>;
}

const POLL_MS = 5_000;
type View = "local" | "provider";

/** Right column, bottom module - "ROUTINES" in the reference image
    becomes "TOP" here, with a switch between two views:

      LOCAL     - real data, unchanged: the Resource Governor's per-model
                  status (was the whole of the old ResourceGovernorPanel).
      PROVIDER  - top provider usage. Not wired yet (owner's call: build
                  the placeholder now, wire it to the Models screen's
                  real usage ledger later over HTTP, never by import) -
                  so it says exactly that instead of a guessed ranking
                  (C12).

    Switching the view never re-fetches or invents anything; it only
    changes which real (or honestly-empty) thing is on screen. */
export function TopPanel() {
  const [data, setData] = useState<GovernorPayload | null>(null);
  const [failedAt, setFailedAt] = useState<number | null>(null);
  const [view, setView] = useState<View>("local");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const ask = async () => {
      try {
        const r = await fetch("/api/main_menu/governor");
        const body = (await r.json()) as GovernorPayload;
        if (!cancelled) {
          setData(body);
          setFailedAt(null);
        }
      } catch {
        if (!cancelled) setFailedAt(Date.now());
      }
      if (!cancelled) timer = setTimeout(ask, POLL_MS);
    };
    ask();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const freshness =
    view === "local"
      ? data !== null && failedAt === null
        ? "fresh"
        : data !== null
          ? "stale"
          : "unavailable"
      : "empty";

  return (
    <section aria-label="Top" data-figure="top" data-fresh={freshness} className="agentic-panel p-3">
      <header className="mb-2 flex items-baseline justify-between">
        <p className="agentic-label">Top</p>
        {view === "local" && data?.checked_at && (
          <time className="num text-[10px] text-dim">{data.checked_at}</time>
        )}
      </header>

      <div className="mb-2 flex gap-1" role="tablist" aria-label="Top panel view">
        {(["local", "provider"] as View[]).map((v) => (
          <button
            key={v}
            type="button"
            role="tab"
            aria-selected={view === v}
            onClick={() => setView(v)}
            className="rounded px-2 py-1 text-[9px] uppercase tracking-wide transition-colors"
            style={{
              background: view === v ? "var(--agentic-amber, #ff7a00)" : "#1a1a1a",
              color: view === v ? "#141212" : "#8B9099",
              border: "1px solid #333",
            }}
          >
            {v === "local" ? "Local Models" : "Provider Usage"}
          </button>
        ))}
      </div>

      {view === "local" && (
        <>
          {data === null && <p className="text-xs text-dim">no answer from the governor yet - it may not be running</p>}
          {data && !data.has_data && <p className="text-xs text-amber">governor unavailable{data.reason ? `: ${data.reason}` : ""}</p>}
          {data?.models && (
            <ul className="flex flex-col divide-y divide-[#262626]">
              {Object.entries(data.models).map(([name, m]) => {
                const label = m.pending_request ? "REQUESTED" : m.listening ? "ACTIVE" : "IDLE";
                const colour = m.pending_request ? "#F2A93B" : m.listening ? "var(--agentic-amber, #ff7a00)" : "#8B9099";
                return (
                  <li key={name} className="flex items-center justify-between gap-2 py-1.5">
                    <span className="num text-xs text-white">{name}</span>
                    <span className="num text-[10px] tracking-widest" style={{ color: colour }}>
                      {label}
                      {m.started_by_governor ? " · ours" : ""}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}

      {view === "provider" && (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-dim">not wired yet</p>
          <p className="text-[10px] leading-relaxed text-dim">
            top provider usage will read from the Models screen&rsquo;s real
            usage ledger over HTTP once that pass is built - no ranking is
            guessed here in the meantime.
          </p>
        </div>
      )}
    </section>
  );
}
