"use client";

import { useOneModule } from "./useModulesBoard";

/** One module opened: a real `<details>` accordion, one row per task -
    ADR-100's fix for "the flat stack takes a lot of space", carried
    into this rebuild rather than reverted. */
export function ModuleRoom({ noteFile, onClose }: { noteFile: string; onClose: () => void }) {
  const { module, state, toggleTask } = useOneModule(noteFile);

  return (
    <div className="rounded-md border border-jade bg-void p-3">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-bone">
          {module?.title ?? noteFile}
          {module && (
            <span className="num ml-2 text-xs text-dim">
              {module.counts.done}/{module.counts.total}
            </span>
          )}
        </h4>
        <button
          type="button"
          onClick={onClose}
          className="num rounded border border-line px-2 py-0.5 text-[10px] tracking-widest text-dim hover:border-cyan hover:text-cyan"
        >
          CLOSE
        </button>
      </div>

      {state === "loading" && <p className="text-xs text-dim">loading module...</p>}
      {state === "error" && <p className="text-xs text-p5red">could not load this module</p>}

      {module?.malformed && (
        <p className="mb-2 text-xs text-amber">this note is malformed - shown as best-effort</p>
      )}

      {module?.tasks.map((task) => (
        <details key={task.id} className="mb-1 rounded border border-line/60 bg-panel px-2 py-1">
          <summary className="flex cursor-pointer items-center gap-2 text-xs text-bone">
            <input
              type="checkbox"
              checked={task.done}
              onChange={(e) => {
                e.stopPropagation();
                toggleTask(task.id);
              }}
              onClick={(e) => e.stopPropagation()}
              className="h-3.5 w-3.5 accent-jade"
            />
            <span className={task.done ? "text-dim line-through" : ""}>
              {task.number}. {task.title}
            </span>
          </summary>
          {task.questions.length > 0 && (
            <ul className="mt-1 flex flex-col gap-1 pl-6 text-[11px] text-dim">
              {task.questions.map((q) => (
                <li key={q.id} className={q.solved ? "text-jade" : ""}>
                  {q.text}
                  {q.attempts ? ` (${q.attempts} attempt${q.attempts === 1 ? "" : "s"})` : ""}
                </li>
              ))}
            </ul>
          )}
        </details>
      ))}
    </div>
  );
}
