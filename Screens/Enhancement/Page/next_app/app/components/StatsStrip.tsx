"use client";

import type { Idea, IdeasState } from "./useIdeas";

const STATUSES: Idea["status"][] = ["ideas", "todo", "in_progress", "done"];
const STATUS_LABEL: Record<Idea["status"], string> = {
  ideas: "CAPTURE",
  todo: "TODO",
  in_progress: "IN PROGRESS",
  done: "DONE",
};

/** Counts, all counted client-side off the one real list the board
    already fetched - no second endpoint exists and none is invented
    here (same rule the Svelte pilot's StatsCard already followed). */
export function StatsStrip({
  ideas,
  state,
}: {
  ideas: Idea[] | null;
  state: IdeasState;
}) {
  const freshness: "fresh" | "empty" | "unavailable" =
    state === "fresh" ? "fresh" : state === "error" ? "unavailable" : "empty";

  const total = ideas?.length ?? 0;
  const byStatus = STATUSES.map((s) => ({
    key: s,
    label: STATUS_LABEL[s],
    count: ideas?.filter((i) => i.status === s).length ?? 0,
  }));
  const aiCount = ideas?.filter((i) => i.source === "ai").length ?? 0;

  return (
    <section
      aria-label="Board stats"
      data-fresh={freshness}
      className="stats-strip grid grid-cols-3 gap-2 sm:grid-cols-6"
    >
      <div className="rounded-lg border border-line bg-panel p-3" data-figure="total-ideas">
        <p className="num mb-1 text-[10px] tracking-[0.2em] text-dim">TOTAL</p>
        {state === "fresh" ? (
          <p className="num text-xl">{total}</p>
        ) : state === "error" ? (
          <p className="text-xs leading-snug text-amber">board did not answer</p>
        ) : (
          <p className="text-xs leading-snug text-dim">reading&hellip;</p>
        )}
      </div>
      {byStatus.map((s) => (
        <div
          key={s.key}
          className="rounded-lg border border-line bg-panel p-3"
          data-figure={`count-${s.key}`}
        >
          <p className="num mb-1 text-[10px] tracking-[0.2em] text-dim">
            {s.label}
          </p>
          <p className="num text-xl">{state === "fresh" ? s.count : "—"}</p>
        </div>
      ))}
      <div className="rounded-lg border border-line bg-panel p-3" data-figure="ai-share">
        <p className="num mb-1 text-[10px] tracking-[0.2em] text-dim">
          YOU / AI
        </p>
        <p className="num text-xl">
          {state === "fresh" ? `${total - aiCount} / ${aiCount}` : "—"}
        </p>
      </div>
    </section>
  );
}
