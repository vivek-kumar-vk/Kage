"use client";

import { useMemo, useRef, useState, useSyncExternalStore } from "react";

/** Left column, bottom module - "DAY PLAN". Replaces the old YouTube
    Studio card (owner, 2026-09-04).

    A morning-to-night timeline of what today asks of me across the four
    areas - Finance, Learning, Anime, Agents. Each row is a time, an area
    tag and a line of text; tap the dot to mark it done.

    FOR NOW this is a hand-kept checklist that lives in the browser
    (localStorage). LATER, once the AI agents are running, they own this
    card end to end - each agent fetches its own area's real state,
    plans the day and writes the rows here (PLAN.md item 15: "Day Plan
    card -> agent-owned"). The Task shape below is what those agents fill. */

type Area = "FIN" | "LEARN" | "ANIME" | "AGENT";

type Task = {
  id: string;
  time: string; // "HH:MM", 24h - sorts the timeline
  area: Area;
  text: string;
  done: boolean;
};

const AREA_COLOUR: Record<Area, string> = {
  FIN: "#ff7a00",
  LEARN: "#8b9099",
  ANIME: "#8b9099",
  AGENT: "#8b9099",
};

const AREAS: Area[] = ["FIN", "LEARN", "ANIME", "AGENT"];

const STORAGE_KEY = "kage.dayplan.v1";

/** The seed day - a plausible morning-to-night pass. Used until the user
    (or later, an agent) edits the card; from then on localStorage wins. */
const SEED: Task[] = [
  { id: "s1", time: "08:00", area: "FIN", text: "Check overnight P&L + open positions", done: false },
  { id: "s2", time: "09:30", area: "LEARN", text: "One lesson on the current track", done: false },
  { id: "s3", time: "11:00", area: "AGENT", text: "Review agent deck - approve / redirect", done: false },
  { id: "s4", time: "13:30", area: "FIN", text: "Log trades, reconcile ledger", done: false },
  { id: "s5", time: "16:00", area: "LEARN", text: "Spaced-recall review", done: false },
  { id: "s6", time: "19:00", area: "ANIME", text: "One episode of the current show", done: false },
  { id: "s7", time: "21:30", area: "AGENT", text: "Queue tomorrow's agent runs", done: false },
];

function byTime(a: Task, b: Task) {
  return a.time.localeCompare(b.time);
}

/* ---------------------------------------------------------------------
   A tiny localStorage-backed store read through useSyncExternalStore.
   The server snapshot is always SEED, so the static export prerenders
   with SEED and the hook swaps in the stored list on the client without
   a hydration warning. The parsed array is cached against its raw
   string so getSnapshot returns a stable reference between changes.
   --------------------------------------------------------------------- */
let cachedRaw: string | null = null;
let cachedItems: Task[] = SEED;
const listeners = new Set<() => void>();

function readSnapshot(): Task[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === cachedRaw) return cachedItems;
    cachedRaw = raw;
    if (raw) {
      const parsed = JSON.parse(raw) as { items?: Task[] };
      cachedItems =
        Array.isArray(parsed.items) && parsed.items.length ? parsed.items : SEED;
    } else {
      cachedItems = SEED;
    }
  } catch {
    cachedItems = SEED;
  }
  return cachedItems;
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

function writeItems(items: Task[]) {
  const sorted = [...items].sort(byTime);
  const raw = JSON.stringify({ items: sorted });
  try {
    window.localStorage.setItem(STORAGE_KEY, raw);
  } catch {
    /* private mode / quota - still update the in-memory cache below */
  }
  cachedRaw = raw;
  cachedItems = sorted;
  listeners.forEach((cb) => cb());
}

function useDayPlan(): Task[] {
  return useSyncExternalStore(subscribe, readSnapshot, () => SEED);
}

function DayPlanIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
      <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="19" cy="18" r="2.4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function DayPlanPanel() {
  const tasks = useDayPlan();
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<{ time: string; area: Area; text: string }>({
    time: "09:00",
    area: "FIN",
    text: "",
  });
  const textRef = useRef<HTMLInputElement | null>(null);

  const toggle = (id: string) =>
    writeItems(tasks.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));

  const remove = (id: string) => writeItems(tasks.filter((t) => t.id !== id));

  const addDraft = () => {
    const text = draft.text.trim();
    if (!text) return;
    writeItems([
      ...tasks,
      { id: `t${Date.now()}`, time: draft.time || "09:00", area: draft.area, text, done: false },
    ]);
    setDraft((d) => ({ ...d, text: "" }));
    textRef.current?.focus();
  };

  const done = useMemo(() => tasks.filter((t) => t.done).length, [tasks]);

  return (
    <section aria-label="Day Plan" className="rubric-panel p-3">
      <header className="mb-2 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <DayPlanIcon />
          Day Plan
        </p>
        <div className="flex items-center gap-2">
          <span className="rubric-sub text-[8px] normal-case tracking-normal text-dim">
            {done}/{tasks.length} done
          </span>
          <button
            type="button"
            className="pill"
            aria-expanded={adding}
            onClick={() => {
              setAdding((v) => !v);
              setTimeout(() => textRef.current?.focus(), 0);
            }}
          >
            {adding ? "Close" : "+ Add"}
          </button>
        </div>
      </header>

      {adding ? (
        <div className="mb-3 flex flex-wrap items-center gap-1.5 border-y border-[#232323] py-2">
          <input
            type="time"
            value={draft.time}
            onChange={(e) => setDraft((d) => ({ ...d, time: e.target.value }))}
            aria-label="Time"
            className="num rounded-[3px] border border-[#333] bg-[#1a1818] px-1.5 py-1 text-[10px] text-white"
          />
          <select
            value={draft.area}
            onChange={(e) => setDraft((d) => ({ ...d, area: e.target.value as Area }))}
            aria-label="Area"
            className="num rounded-[3px] border border-[#333] bg-[#1a1818] px-1.5 py-1 text-[10px] text-white"
          >
            {AREAS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <input
            ref={textRef}
            value={draft.text}
            onChange={(e) => setDraft((d) => ({ ...d, text: e.target.value }))}
            onKeyDown={(e) => {
              if (e.key === "Enter") addDraft();
            }}
            placeholder="what needs doing"
            aria-label="Task"
            className="min-w-0 flex-1 rounded-[3px] border border-[#333] bg-[#1a1818] px-2 py-1 text-[11px] text-white placeholder:text-dim"
          />
          <button
            type="button"
            onClick={addDraft}
            className="num rounded-[3px] border border-[#ff7a00] px-2 py-1 text-[9px] text-[#ff7a00] hover:bg-[#ff7a00]/10"
          >
            ADD
          </button>
        </div>
      ) : null}

      {tasks.length === 0 ? (
        <p className="py-4 text-[10px] text-dim">Nothing planned. Press + Add.</p>
      ) : (
        <ul>
          {tasks.map((t) => (
            <li
              key={t.id}
              className="group grid grid-cols-[42px_1fr_auto_16px] items-center gap-x-2 border-b border-[#1f1f1f] py-1.5 last:border-b-0"
            >
              <button
                type="button"
                onClick={() => toggle(t.id)}
                aria-pressed={t.done}
                aria-label={t.done ? `mark ${t.text} not done` : `mark ${t.text} done`}
                className="num flex items-center gap-1.5 text-[10px]"
                style={{ color: t.done ? "#5a5a5a" : "#8b9099" }}
              >
                <span
                  className="inline-block h-[7px] w-[7px] shrink-0 rounded-full border"
                  style={{
                    background: t.done ? "#ff7a00" : "transparent",
                    borderColor: t.done ? "#ff7a00" : "#4a4a4a",
                  }}
                />
                {t.time}
              </button>

              <span
                className="min-w-0 truncate text-[11px] leading-snug"
                style={{
                  color: t.done ? "#5a5a5a" : "#ffffff",
                  textDecoration: t.done ? "line-through" : "none",
                }}
                title={t.text}
              >
                {t.text}
              </span>

              <span
                className="rubric-sub shrink-0 text-[7px]"
                style={{ color: AREA_COLOUR[t.area] }}
              >
                &#9670; {t.area}
              </span>

              <button
                type="button"
                onClick={() => remove(t.id)}
                aria-label={`remove ${t.text}`}
                className="text-[12px] leading-none text-[#3a3a3a] opacity-0 transition-opacity hover:text-[#ff7a00] group-hover:opacity-100"
              >
                &times;
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="num mt-2 border-t border-[#232323] pt-1.5 text-[8px] text-dim">
        HAND-KEPT FOR NOW &middot; AGENT-OWNED LATER
      </p>
    </section>
  );
}
