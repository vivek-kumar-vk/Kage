"use client";

import { motion } from "framer-motion";
import type { Idea } from "./useIdeas";

const STATUSES: Idea["status"][] = ["ideas", "todo", "in_progress", "done"];
const STATUS_LABEL: Record<Idea["status"], string> = {
  ideas: "CAPTURE",
  todo: "TODO",
  in_progress: "IN PROGRESS",
  done: "DONE",
};
const PRIORITY_COLOUR: Record<Idea["priority"], string> = {
  low: "border-line text-dim",
  medium: "border-cyan text-cyan",
  high: "border-amber text-amber",
  critical: "border-p5red text-p5red",
};

function IdeaCard({ idea }: { idea: Idea }) {
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      data-idea-key={idea.key}
      className={`rounded border border-line bg-void p-2.5 text-xs ${
        idea.source === "ai" ? "ai-generated" : ""
      }`}
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="num text-dim">{idea.key}</span>
        <span
          className={`num rounded-sm border px-1.5 text-[9px] tracking-wider ${PRIORITY_COLOUR[idea.priority]}`}
        >
          {idea.priority.toUpperCase()}
        </span>
      </div>
      <p className="leading-snug text-bone">{idea.title}</p>
      {idea.area ? (
        <p className="num mt-1 text-[10px] text-dim">{idea.area}</p>
      ) : null}
      {idea.comments.length > 0 ? (
        <p className="num mt-1 text-[10px] text-dim">
          {idea.comments.length} comment{idea.comments.length === 1 ? "" : "s"}
        </p>
      ) : null}
    </motion.li>
  );
}

/** The board itself - four columns, one per status, each holding the
    real ideas already fetched by the page. Read-only in this rebuild:
    the drag/drop/comment editing the hand-drawn page already has stays
    the way to change the board; this view is the pitch-grade window
    onto the same data, not a second way to write it. A column with no
    cards still gets its header, empty and honest. */
export function IdeaBoard({
  ideas,
  state,
}: {
  ideas: Idea[] | null;
  state: "loading" | "fresh" | "error";
}) {
  const freshness = state === "fresh" ? "fresh" : state === "error" ? "unavailable" : "empty";

  return (
    <section
      aria-label="Idea board"
      data-fresh={freshness}
      className="board-scroll overflow-x-auto rounded-lg border border-line bg-panel p-3"
    >
      {state === "error" && (
        <p className="text-sm text-amber">
          the board did not answer - no cards guessed in its place
        </p>
      )}
      {state === "loading" && (
        <p className="text-sm text-dim">reading the board&hellip;</p>
      )}
      {state === "fresh" && (
        <div className="board-columns flex gap-3">
          {STATUSES.map((status) => {
            const items = (ideas ?? []).filter((i) => i.status === status);
            return (
              <div
                key={status}
                className="board-column flex w-64 shrink-0 flex-col gap-2"
                data-column={status}
              >
                <header className="flex items-center justify-between">
                  <h3 className="num text-xs tracking-[0.2em] text-dim">
                    {STATUS_LABEL[status]}
                  </h3>
                  <span className="num text-xs text-dim">{items.length}</span>
                </header>
                <ol className="flex flex-col gap-2">
                  {items.length === 0 && (
                    <li className="rounded border border-dashed border-line px-2 py-3 text-center text-[10px] text-dim">
                      empty
                    </li>
                  )}
                  {items.map((idea) => (
                    <IdeaCard key={idea.id} idea={idea} />
                  ))}
                </ol>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
