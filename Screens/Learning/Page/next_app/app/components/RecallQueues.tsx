"use client";

import { useRecallCards, useRecallNotes } from "./useRecall";

const QUALITIES: Array<{ value: number; label: string }> = [
  { value: 0, label: "Again" },
  { value: 3, label: "Hard" },
  { value: 4, label: "Good" },
  { value: 5, label: "Easy" },
];

export function RecallQueues() {
  const cards = useRecallCards();
  const notes = useRecallNotes();

  const freshness =
    cards.state === "fresh" && notes.state === "fresh"
      ? "fresh"
      : cards.state === "error" || notes.state === "error"
        ? "unavailable"
        : "empty";

  return (
    <section aria-label="Recall queues" data-fresh={freshness} className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-3 flex items-center justify-between">
        <h2 className="num text-sm tracking-[0.2em] text-dim">RECALL</h2>
        <span className="num text-[10px] text-dim">two queues, side by side</span>
      </header>

      <div className="stats-strip grid grid-cols-2 gap-4">
        <div className="rounded-md border border-line bg-void p-3">
          <h3 className="num mb-2 text-xs tracking-widest text-dim">
            SM-2 CARDS <span className="text-jade">{cards.data?.due.length ?? 0} due</span>
          </h3>
          {cards.state === "loading" && !cards.data && <p className="text-xs text-dim">loading...</p>}
          {cards.state === "error" && !cards.data && (
            <p className="text-xs text-p5red">could not reach /api/learning/recall-cards</p>
          )}
          {cards.data && cards.data.due.length === 0 && (
            <p className="text-xs text-dim">nothing due - empty beats fake</p>
          )}
          <ul className="panel-scroll flex max-h-64 flex-col gap-2 overflow-y-auto">
            {cards.data?.due.map((c) => (
              <li key={c.id} className="rounded border border-line/60 bg-panel p-2">
                <p className="truncate text-xs text-bone">{c.topic}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {QUALITIES.map((q) => (
                    <button
                      key={q.value}
                      type="button"
                      onClick={() => cards.review(c.id, q.value)}
                      className="num rounded border border-line px-1.5 py-0.5 text-[10px] text-dim hover:border-jade hover:text-jade"
                    >
                      {q.label}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-md border border-line bg-void p-3">
          <h3 className="num mb-2 text-xs tracking-widest text-dim">
            LEITNER NOTES <span className="text-jade">{notes.data?.due_count ?? 0} due</span>
          </h3>
          {notes.state === "loading" && !notes.data && <p className="text-xs text-dim">loading...</p>}
          {notes.state === "error" && !notes.data && (
            <p className="text-xs text-p5red">could not reach /api/learning/recall</p>
          )}
          {notes.data && notes.data.due.length === 0 && (
            <p className="text-xs text-dim">nothing due - empty beats fake</p>
          )}
          <ul className="panel-scroll flex max-h-64 flex-col gap-2 overflow-y-auto">
            {notes.data?.due.map((n) => (
              <li key={n.note_file} className="rounded border border-line/60 bg-panel p-2">
                <p className="truncate text-xs text-bone">{n.title}</p>
                <p className="num text-[10px] text-dim">box {n.box}</p>
                <div className="mt-1 flex gap-1">
                  <button
                    type="button"
                    onClick={() => notes.review(n.note_file, true)}
                    className="num rounded border border-line px-1.5 py-0.5 text-[10px] text-dim hover:border-jade hover:text-jade"
                  >
                    REMEMBERED
                  </button>
                  <button
                    type="button"
                    onClick={() => notes.review(n.note_file, false)}
                    className="num rounded border border-line px-1.5 py-0.5 text-[10px] text-dim hover:border-p5red hover:text-p5red"
                  >
                    FORGOT
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
