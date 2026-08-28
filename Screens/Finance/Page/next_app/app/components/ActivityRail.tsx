"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useLiveEvents } from "./useLiveEvents";
import { LiveBadge } from "./LiveBadge";

/** This screen's own live trace feed, off /api/finance/live - the
    Phase 12.2 SSE endpoint every FastAPI screen carries. An empty feed
    is the truth that nothing has been traced yet today, never faked
    with a fabricated row. */
export function ActivityRail() {
  const { rows, state } = useLiveEvents("/api/finance/live");

  const freshness =
    state === "live"
      ? "fresh"
      : state === "reconnecting"
        ? "stale"
        : state === "offline"
          ? "unavailable"
          : "empty";

  return (
    <section
      aria-label="Finance activity"
      data-fresh={freshness}
      className="rounded-lg border border-line bg-panel p-4"
    >
      <header className="mb-3 flex items-center justify-between gap-2">
        <h2 className="num text-sm tracking-[0.2em] text-dim">ACTIVITY</h2>
        <LiveBadge state={state} />
      </header>
      <ol
        data-feed-count={rows.length}
        className="panel-scroll flex max-h-72 flex-col-reverse gap-1 overflow-y-auto"
      >
        <AnimatePresence initial={false}>
          {rows.map((row, i) => (
            <motion.li
              key={`${row.seq ?? "x"}-${i}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={`flex items-baseline justify-between gap-3 rounded border-l-2 bg-void px-2 py-1 text-xs ${
                row.outcome === "fail"
                  ? "border-p5red"
                  : row.outcome === "escalated"
                    ? "border-amber"
                    : "border-line"
              }`}
            >
              <span className="truncate">
                <span className="text-cyan">{row.actor ?? "?"}</span>
                <span className="text-dim"> · </span>
                <span>{row.action ?? "?"}</span>
                {row.target ? <span className="text-dim"> {row.target}</span> : null}
              </span>
              <span className="num shrink-0 text-dim">
                {row.ts ? row.ts.slice(11, 19) : ""}
              </span>
            </motion.li>
          ))}
        </AnimatePresence>
      </ol>
      {rows.length === 0 && state === "live" && (
        <p className="mt-2 text-xs text-dim">connected - nothing traced yet today</p>
      )}
    </section>
  );
}
