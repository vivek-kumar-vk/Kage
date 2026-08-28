"use client";

import { useEffect, useState } from "react";

interface CalendarEvent {
  date?: string;
  title?: string;
}

/** Left column, middle module - "TODAY", matching the reference's
    Calendar module: a big clock, then what's on file for today. */
export function TodayPanel() {
  const [now, setNow] = useState<Date | null>(null);
  const [events, setEvents] = useState<CalendarEvent[] | null>(null);
  const [calFailed, setCalFailed] = useState(false);

  useEffect(() => {
    setNow(new Date());
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/main_menu/calendar/events")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((body) => {
        if (cancelled) return;
        if (body.state === "error") {
          setCalFailed(true);
          return;
        }
        setEvents(Array.isArray(body.events) ? body.events : []);
      })
      .catch(() => {
        if (!cancelled) setCalFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const today_iso = now ? now.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }) : "";
  const todays = (events ?? []).filter((ev) => !ev.date || ev.date === today_iso);

  return (
    <div data-figure="today" data-fresh={now ? "fresh" : "empty"} className="agentic-panel p-4">
      <p className="agentic-label mb-1">Today</p>
      {now ? (
        <>
          <p className="num agentic-accent text-3xl font-semibold">
            {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </p>
          <p className="num text-[10px] text-dim">
            {now.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" })}
          </p>
        </>
      ) : (
        <p className="text-xs text-dim">&hellip;</p>
      )}

      <div className="mt-3 border-t border-[#262626] pt-2">
        {calFailed ? (
          <p className="text-xs text-amber">the calendar agent did not answer</p>
        ) : events === null ? (
          <p className="text-xs text-dim">reading the calendar&hellip;</p>
        ) : todays.length === 0 ? (
          <p className="text-xs text-dim">nothing on file today - that is the truth, not an error.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {todays.slice(0, 3).map((ev, i) => (
              <li key={`${ev.title}-${i}`} className="flex items-baseline justify-between gap-2 text-xs">
                <span className="truncate text-white">{ev.title ?? "untitled"}</span>
                {ev.date && <span className="num agentic-accent text-[10px]">{ev.date}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
