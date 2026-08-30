"use client";

import { ActivityRail } from "./components/ActivityRail";
import { IdeaBoard } from "./components/IdeaBoard";
import { StatsStrip } from "./components/StatsStrip";
import { useIdeas } from "./components/useIdeas";

/** The Enhancement rebuild - the idea board, its own design pass.
    Where Main_Menu wears the loud Persona-5 slab, this screen is a
    quiet corkboard: a flat jade-accented strip up top, four real
    columns of real cards under it, a live activity rail beside it.
    The shared Look_And_Feel tokens are the thread; the layout and the
    kanban metaphor are this screen's own. */
export default function Home() {
  const { ideas, state, fetchedAt, reload } = useIdeas();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="board-header border-b border-line bg-panel">
        <div className="header-pad mx-auto flex max-w-6xl items-baseline justify-between px-6 py-4">
          <h1 className="board-title font-mono text-2xl font-black tracking-tight text-jade">
            ENHANCEMENT <span className="font-light text-bone">// IDEA BOARD</span>
          </h1>
          <button
            type="button"
            onClick={reload}
            className="num rounded border border-line px-2 py-1 text-[10px] tracking-widest text-dim hover:border-cyan hover:text-cyan"
          >
            REFRESH
          </button>
        </div>
      </header>

      <main className="board-main mx-auto w-full max-w-6xl flex-1 px-6 py-6">
        <StatsStrip ideas={ideas} state={state} />

        <div className="board-grid mt-6 grid grid-cols-[1fr_320px] gap-6">
          <IdeaBoard ideas={ideas} state={state} />
          <div className="rail flex flex-col gap-6">
            <ActivityRail />
          </div>
        </div>
      </main>

      <footer className="mx-auto w-full max-w-6xl px-6 pb-6 pt-2">
        <p className="num text-[10px] leading-relaxed text-dim">
          every card traces to enhancement_board.db · empty means not
          captured yet, stated plainly
          {fetchedAt ? ` · read at ${fetchedAt.toLocaleTimeString()}` : ""}
          {" · events stream from Shared_By_All_Screens/Trace_Ledger via /api/enhancement/live"}
        </p>
      </footer>
    </div>
  );
}
