"use client";

import { useState } from "react";
import { useModulesBoard } from "./useModulesBoard";
import { useTopics } from "./useTopics";
import { ModuleRoom } from "./ModuleRoom";
import { ProgressRing } from "./ProgressRing";

const STATE_LOOK: Record<string, string> = {
  ready: "text-jade",
  missing: "text-dim",
  malformed: "text-amber",
};

export function PlanBoard() {
  const { data: topics, state: topicsState } = useTopics();
  const { board, state: boardState } = useModulesBoard();
  const [openNote, setOpenNote] = useState<string | null>(null);

  const freshness =
    boardState === "fresh" && topicsState === "fresh"
      ? "fresh"
      : boardState === "error" || topicsState === "error"
        ? "unavailable"
        : "empty";

  return (
    <section aria-label="Plan board" data-fresh={freshness} className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-3 flex items-center justify-between gap-4">
        <h2 className="num text-sm tracking-[0.2em] text-dim">PLAN</h2>
        {board && (
          <span className="num text-[10px] text-dim">
            {board.topics_with_modules}/{board.topics_total} topics have a module - the gap is the to-do list
          </span>
        )}
      </header>

      {topics && (
        <div className="mb-4 flex flex-wrap gap-6">
          <ProgressRing pct={topics.trackA.progress?.pct ?? 0} label={`Track A · ${topics.trackA.progress?.done ?? 0}/${topics.trackA.progress?.total ?? 0}`} />
          <ProgressRing pct={topics.trackB.progress?.pct ?? 0} label={`Track B · ${topics.trackB.progress?.done ?? 0}/${topics.trackB.progress?.total ?? 0}`} />
        </div>
      )}

      {boardState === "loading" && !board && <p className="text-sm text-dim">loading the board...</p>}
      {boardState === "error" && !board && <p className="text-sm text-p5red">could not reach /api/learning/modules</p>}

      <div className="panel-scroll flex max-h-[32rem] flex-col gap-3 overflow-y-auto">
        {board?.groups.map((group) => (
          <div key={`${group.track}-${group.group}`} className="rounded-md border border-line bg-void p-3">
            <h3 className="num mb-1 text-xs tracking-widest text-dim">
              {group.track === "trackA" ? "A" : "B"} · {group.group}
            </h3>
            <ul className="flex flex-col gap-1">
              {group.topics.map((row) => (
                <li key={row.id}>
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="truncate text-bone">{row.topic}</span>
                    <span className="flex shrink-0 items-center gap-2">
                      {row.module_state === "ready" && (
                        <span className="num text-dim">
                          {row.tasks_done}/{row.tasks_total}
                        </span>
                      )}
                      <span className={`num ${STATE_LOOK[row.module_state]}`}>
                        {row.module_state.toUpperCase()}
                      </span>
                      {row.module_state === "ready" && row.note_file && (
                        <button
                          type="button"
                          onClick={() =>
                            setOpenNote((cur) => (cur === row.note_file ? null : row.note_file!))
                          }
                          className="num rounded border border-line px-1.5 py-0.5 text-[10px] text-dim hover:border-cyan hover:text-cyan"
                        >
                          {openNote === row.note_file ? "CLOSE" : "OPEN"}
                        </button>
                      )}
                    </span>
                  </div>
                  {openNote === row.note_file && row.note_file && (
                    <div className="mt-2">
                      <ModuleRoom noteFile={row.note_file} onClose={() => setOpenNote(null)} />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
