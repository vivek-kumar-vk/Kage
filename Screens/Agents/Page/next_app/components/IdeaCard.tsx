"use client";

import type { DragEvent } from "react";
import type { Idea, IdeaPriority } from "../lib/api";

const priorityClasses: Record<IdeaPriority, string> = {
  low: "border border-deck-line text-deck-dim",
  medium: "border border-deck-slate text-deck-slate",
  high: "border border-deck-copper text-deck-copper",
  critical: "border border-deck-alert text-deck-alert",
};

export default function IdeaCard({
  idea,
  selected,
  onSelect,
  onDragStart,
  onDragEnd,
  onDragOver,
}: {
  idea: Idea;
  selected: boolean;
  onSelect: () => void;
  onDragStart: (event: DragEvent<HTMLDivElement>) => void;
  onDragEnd: () => void;
  onDragOver: (event: DragEvent<HTMLDivElement>) => void;
}) {
  return (
    <div
      draggable={true}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      className={`relative cursor-grab border bg-deck-raised p-3 text-left focus:outline-none focus-visible:border-deck-copper ${
        selected ? "border-deck-copper" : "border-deck-line"
      }`}
    >
      {idea.source === "ai" ? (
        <span className="absolute left-0 top-0 h-full w-0.5 bg-deck-slate" aria-hidden="true" />
      ) : null}

      <div className="flex items-center justify-between gap-2">
        <span className="num font-mono text-xs text-deck-dim">{idea.key}</span>
        <span className={`px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${priorityClasses[idea.priority]}`}>
          {idea.priority}
        </span>
      </div>

      <p className="mt-2 text-sm text-deck-text">{idea.title}</p>

      {idea.note ? <p className="mt-1 text-xs text-deck-dim">{idea.note}</p> : null}

      <div className="mt-2 flex items-center justify-between text-xs text-deck-dim">
        <span>{idea.source === "ai" ? "AI" : "User"}</span>
        <span className="num">
          {idea.comments.length} comment{idea.comments.length === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
}
