"use client";

import { useEffect, useState } from "react";

/** Left column, middle module - "CALENDAR" from the reference. The big
    clock is the one live bit kept (it ticks); everything else - the
    week label, the timezone row, the quarter grid, WHAT'S NEXT - is
    static, an exact copy of the reference image. */

const ZONES = [
  { label: "USA PT", time: "09:32 pm", day: "WED" },
  { label: "USA ET", time: "12:32 am", day: "THU" },
  { label: "LONDON", time: "05:32 am", day: "THU" },
];

const WHATS_NEXT = [
  { title: "Team standup", at: "3:30pm" },
  { title: "Partnership intro – Nordic SaaS", at: "5:00pm" },
  { title: "Team meet – sprint review", at: "6:30pm" },
];

// A 4-row quarter grid; one cell in Q3 is the "today" marker (amber).
const QUARTERS = ["Q1", "Q2", "Q3", "Q4"];
const CELLS_PER_ROW = 13;
const TODAY_CELL = { row: 2, col: 6 };

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    // First paint happens client-side only (avoids an SSR/CSR clock
    // mismatch); the async first tick keeps it out of the effect body.
    const tick = () => setNow(new Date());
    const first = setTimeout(tick, 0);
    const timer = setInterval(tick, 1000);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, []);
  return now;
}

export function CalendarPanel() {
  const now = useClock();
  const clock = now
    ? now
        .toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        })
        .toLowerCase()
    : "--:--:-- --";

  return (
    <section aria-label="Calendar" className="rubric-panel p-4">
      <header className="mb-3 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
            <rect x="4" y="5" width="16" height="16" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M4 9h16M9 3v4M15 3v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          Calendar
        </p>
        <div className="flex items-center gap-2">
          <span className="rubric-sub text-[8px] normal-case tracking-normal text-dim">today</span>
          <button type="button" className="pill">Open Cal</button>
        </div>
      </header>

      <p className="mb-1 text-[11px]">
        <span className="rubric-accent num font-semibold">Wk34</span>
        <span className="text-dim"> | Aug 20 2026 (Thu)</span>
      </p>
      <p className="num rubric-accent text-[28px] font-semibold leading-tight">{clock}</p>
      <p className="rubric-sub mb-3 text-[9px]">AEST &middot; SYDNEY</p>

      <div className="mb-3 grid grid-cols-3 gap-2 border-y border-[#232323] py-2">
        {ZONES.map((z) => (
          <div key={z.label}>
            <p className="rubric-sub text-[8px]">{z.label}</p>
            <p className="num text-[11px] text-white">{z.time}</p>
            <p className="num text-[8px] text-dim">({z.day})</p>
          </div>
        ))}
      </div>

      <div className="mb-3 flex flex-col gap-[3px]">
        {QUARTERS.map((q, row) => (
          <div key={q} className="flex items-center gap-1.5">
            <span className="rubric-sub w-4 text-[8px]">{q}</span>
            <span className="flex gap-[3px]">
              {Array.from({ length: CELLS_PER_ROW }).map((_, col) => {
                const isToday = row === TODAY_CELL.row && col === TODAY_CELL.col;
                const filled = row < 2 || (row === 2 && col <= TODAY_CELL.col);
                return (
                  <span
                    key={col}
                    className="h-[9px] w-[9px] rounded-[1px]"
                    style={{
                      background: isToday
                        ? "#ff7a00"
                        : filled
                          ? "#3a3a3a"
                          : "#1d1d1d",
                    }}
                  />
                );
              })}
            </span>
          </div>
        ))}
      </div>

      <p className="rubric-sub mb-1.5 text-[8px]">What&rsquo;s Next</p>
      <ul className="flex flex-col gap-1.5">
        {WHATS_NEXT.map((ev) => (
          <li key={ev.title} className="flex items-baseline justify-between gap-2 text-[11px]">
            <span className="truncate text-white">{ev.title}</span>
            <span className="num shrink-0 text-dim">{ev.at}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
