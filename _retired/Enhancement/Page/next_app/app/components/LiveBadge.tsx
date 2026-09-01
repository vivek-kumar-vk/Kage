"use client";

import type { StreamState } from "./useLiveEvents";

/** The connection chip. Red means the stream is actually down - never
    decoration (the one rule this design lives or dies by). */
export function LiveBadge({ state }: { state: StreamState }) {
  const look: Record<StreamState, string> = {
    connecting: "text-dim border-line",
    live: "text-jade border-jade",
    reconnecting: "text-amber border-amber",
    offline: "text-p5red border-p5red",
  };
  const word: Record<StreamState, string> = {
    connecting: "CONNECTING",
    live: "LIVE",
    reconnecting: "RECONNECTING",
    offline: "OFFLINE",
  };
  return (
    <span
      data-stream-state={state}
      className={`num inline-flex items-center gap-2 rounded-sm border px-2 py-0.5 text-xs tracking-widest ${look[state]}`}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
      {word[state]}
    </span>
  );
}
