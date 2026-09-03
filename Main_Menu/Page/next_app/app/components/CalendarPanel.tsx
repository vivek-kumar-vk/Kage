"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Left column, top module - "CALENDAR" (D23).
 *
 *  The card is the reference card: same panel, same header, same
 *  WHAT'S NEXT list. Two things changed, both on the owner's
 *  instruction (2026-09-03):
 *
 *    - the OPEN CAL pill became a two-way switch, so WakaTime opens in
 *      this same card rather than another tab;
 *    - the world-clock row and the Q1-Q4 grid both came out, replaced
 *      by a real month grid. The month grid does what the quarter grid
 *      was gesturing at - a year's rhythm at a glance - and it gives
 *      every day a real cell to hover.
 *
 *  Hovering a day opens a popover to the RIGHT of the card, in the
 *  empty gutter before the centre column: it never covers the grid you
 *  are reading, and there is room for a real list. A cell only carries
 *  a marker when the day actually has something, so hovering is never
 *  a guess.
 *
 *  Every figure here comes from /api/main_menu/calendar/* or
 *  /wakatime/summary. Nothing is invented: a day with no data draws an
 *  empty cell, and a disconnected source says so in words (Rule 8).
 */

const WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"];

const AMBER = "#ff7a00";
const DIM = "#6b6b6b";

type DayCell = {
  events: number;
  notes: number;
  proposals: number;
  coding_seconds: number | null;
};

type MonthPayload = {
  state: string;
  detail: string;
  year: number;
  month: number;
  label: string;
  today: string | null;
  first_weekday: number;
  days_in_month: number;
  days: Record<string, DayCell>;
  synced_at: string | null;
  event_count: number;
  connecting: boolean;
  syncing: boolean;
  credentials_path: string;
  auto_write: boolean;
  pending_proposals: number;
  agent: { state: string; detail: string; backend: string; last_run: string | null };
};

type DayPayload = {
  day: string;
  label: string;
  events: { summary: string; time: string | null; all_day: boolean; by_agent: boolean }[];
  notes: { kind: string; text: string }[];
  proposals: { id: number; summary: string; time: string | null; reason: string; status: string }[];
  coding: { display: string | null; top_project: string | null; top_language: string | null } | null;
};

type NextPayload = {
  state: string;
  detail: string;
  events: { summary: string; time: string | null; day: string; today: boolean; by_agent: boolean }[];
};

type WakaPayload = {
  state: string;
  detail?: string;
  today?: string | null;
  snapshot_days?: number;
  week?: { day: string; letter: string; seconds: number | null; display: string | null }[];
  languages?: { name: string; percent: number; display: string }[];
  projects?: { name: string; display: string }[];
  daily_average?: string;
  range_total?: string;
  stats_detail?: string;
};

const API = "/api/main_menu";

async function getJSON<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(path, { headers: { accept: "application/json" } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Wall-clock time of an ISO stamp, for the footer. */
function clockOf(iso?: string | null): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed
    .toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true })
    .toUpperCase();
}

/** "25 NOV" - the short date the WHAT'S NEXT rows carry when the event
    is not today. */
function dayLabel(day: string): string {
  const parsed = new Date(`${day}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return day;
  return parsed
    .toLocaleDateString("en-GB", { day: "2-digit", month: "short" })
    .toUpperCase();
}

function CalendarIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
      <rect x="4" y="5" width="16" height="16" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 9h16M9 3v4M15 3v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/** The switch that replaced OPEN CAL. Two segments, one lit. */
function ModeSwitch({ mode, onChange }: { mode: "cal" | "waka"; onChange: (m: "cal" | "waka") => void }) {
  return (
    <div className="flex overflow-hidden rounded-[3px] border border-[#333333]" role="tablist" aria-label="Card source">
      {(["cal", "waka"] as const).map((key) => (
        <button
          key={key}
          type="button"
          role="tab"
          aria-selected={mode === key}
          onClick={() => onChange(key)}
          className="px-2 py-[3px] text-[9px] uppercase tracking-[0.12em] transition-colors"
          style={{
            background: mode === key ? "rgba(255,122,0,0.14)" : "transparent",
            color: mode === key ? AMBER : "#8b9099",
          }}
        >
          {key === "cal" ? "Cal" : "Waka"}
        </button>
      ))}
    </div>
  );
}

/** Coding time tints the cell. This is the one thing the old Q1-Q4 grid
    did well - a glance tells you which days were heavy - kept, but on
    real WakaTime seconds instead of a decorative pattern. */
function codingTint(seconds: number | null): string {
  if (!seconds) return "transparent";
  const hours = seconds / 3600;
  const alpha = Math.min(0.06 + hours * 0.045, 0.3);
  return `rgba(255,122,0,${alpha.toFixed(3)})`;
}

export function CalendarPanel() {
  const [mode, setMode] = useState<"cal" | "waka">("cal");
  const [cursor, setCursor] = useState<{ year: number; month: number } | null>(null);
  const [month, setMonth] = useState<MonthPayload | null>(null);
  const [next, setNext] = useState<NextPayload | null>(null);
  const [waka, setWaka] = useState<WakaPayload | null>(null);

  const [hover, setHover] = useState<{ day: string; top: number } | null>(null);
  const [detail, setDetail] = useState<DayPayload | null>(null);
  const cardRef = useRef<HTMLElement | null>(null);
  const closeTimer = useRef<number | null>(null);
  const dayCache = useRef<Map<string, DayPayload>>(new Map());

  const loadMonth = useCallback(async (year?: number, monthNumber?: number) => {
    const query = year && monthNumber ? `?year=${year}&month=${monthNumber}` : "";
    const data = await getJSON<MonthPayload>(`${API}/calendar/month${query}`);
    if (data) {
      setMonth(data);
      setCursor({ year: data.year, month: data.month });
    }
  }, []);

  const loadNext = useCallback(async () => {
    const data = await getJSON<NextPayload>(`${API}/calendar/next?limit=3`);
    if (data) setNext(data);
  }, []);

  useEffect(() => {
    loadMonth();
    loadNext();
  }, [loadMonth, loadNext]);

  // Poll: once a minute normally, every 3s while a consent tab is open or a
  // sync is running, so the card flips over the moment either lands rather
  // than waiting for the user to reload the page.
  useEffect(() => {
    const busy = month?.connecting || month?.syncing;
    const timer = setInterval(() => {
      loadMonth(cursor?.year, cursor?.month);
      loadNext();
    }, busy ? 3000 : 60000);
    return () => clearInterval(timer);
  }, [month?.connecting, month?.syncing, cursor?.year, cursor?.month, loadMonth, loadNext]);

  const post = async (path: string) => {
    try {
      await fetch(`${API}${path}`, { method: "POST" });
    } catch {
      /* the next poll tells the truth if it failed */
    }
    setTimeout(() => loadMonth(cursor?.year, cursor?.month), 800);
  };

  useEffect(() => {
    if (mode === "waka" && !waka) {
      getJSON<WakaPayload>(`${API}/wakatime/summary`).then(setWaka);
    }
  }, [mode, waka]);

  const step = (delta: number) => {
    if (!cursor) return;
    const raw = cursor.month - 1 + delta;
    const year = cursor.year + Math.floor(raw / 12);
    const monthNumber = ((raw % 12) + 12) % 12 + 1;
    setHover(null);
    loadMonth(year, monthNumber);
  };

  const openDay = (day: string, element: HTMLElement) => {
    if (closeTimer.current) window.clearTimeout(closeTimer.current);
    const base = cardRef.current?.getBoundingClientRect();
    const rect = element.getBoundingClientRect();
    setHover({ day, top: base ? rect.top - base.top : 0 });
    const cached = dayCache.current.get(day);
    setDetail(cached ?? null);
    if (!cached) {
      getJSON<DayPayload>(`${API}/calendar/day?day=${day}`).then((data) => {
        if (!data) return;
        dayCache.current.set(day, data);
        setDetail(data);
      });
    }
  };

  const scheduleClose = () => {
    if (closeTimer.current) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setHover(null), 160);
  };

  const decide = async (id: number, action: "approve" | "reject") => {
    await fetch(`${API}/calendar/proposals/${id}/${action}`, { method: "POST" });
    if (hover) {
      dayCache.current.delete(hover.day);
      const fresh = await getJSON<DayPayload>(`${API}/calendar/day?day=${hover.day}`);
      if (fresh) {
        dayCache.current.set(hover.day, fresh);
        setDetail(fresh);
      }
    }
    loadMonth(cursor?.year, cursor?.month);
  };

  const cells: (string | null)[] = [];
  if (month) {
    for (let i = 0; i < month.first_weekday; i += 1) cells.push(null);
    for (let d = 1; d <= month.days_in_month; d += 1) {
      cells.push(`${month.year}-${String(month.month).padStart(2, "0")}-${String(d).padStart(2, "0")}`);
    }
  }

  const notConnected = month && month.state !== "ok";

  return (
    <section aria-label="Calendar" className="rubric-panel relative p-4" ref={cardRef}>
      <header className="mb-3 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <CalendarIcon />
          Calendar
        </p>
        <div className="flex items-center gap-2">
          <span className="rubric-sub text-[8px] normal-case tracking-normal text-dim">today</span>
          <ModeSwitch mode={mode} onChange={setMode} />
        </div>
      </header>

      {mode === "cal" ? (
        <>
          {/* Month strip - the row the world clocks used to occupy. */}
          <div className="mb-2 flex items-center justify-between border-y border-[#232323] py-1.5">
            <button type="button" className="pill px-1.5 py-0.5" onClick={() => step(-1)} aria-label="Previous month">
              &lsaquo;
            </button>
            <span className="num text-[11px] tracking-[0.14em] text-white">{month?.label ?? "—"}</span>
            <button type="button" className="pill px-1.5 py-0.5" onClick={() => step(1)} aria-label="Next month">
              &rsaquo;
            </button>
          </div>

          <div className="mb-1 grid grid-cols-7 gap-[3px]">
            {WEEKDAYS.map((letter, i) => (
              <span key={`${letter}-${i}`} className="rubric-sub text-center text-[8px]">
                {letter}
              </span>
            ))}
          </div>

          <div className="mb-3 grid grid-cols-7 gap-[3px]">
            {cells.map((day, index) => {
              if (!day) return <span key={`pad-${index}`} className="h-[26px]" />;
              const cell = month?.days[day];
              const isToday = month?.today === day;
              const hasSomething = Boolean(
                cell && (cell.events || cell.notes || cell.proposals || cell.coding_seconds),
              );
              return (
                <button
                  key={day}
                  type="button"
                  onMouseEnter={(e) => hasSomething && openDay(day, e.currentTarget)}
                  onMouseLeave={scheduleClose}
                  onFocus={(e) => hasSomething && openDay(day, e.currentTarget)}
                  onBlur={scheduleClose}
                  aria-label={hasSomething ? `${day} - has activity` : day}
                  className="flex h-[26px] flex-col items-center justify-center rounded-[2px] border transition-colors"
                  style={{
                    background: isToday ? AMBER : codingTint(cell?.coding_seconds ?? null),
                    borderColor: hover?.day === day ? AMBER : "transparent",
                    cursor: hasSomething ? "pointer" : "default",
                  }}
                >
                  <span
                    className="num text-[10px] leading-none"
                    style={{ color: isToday ? "#141212" : hasSomething ? "#ffffff" : "#5a5a5a" }}
                  >
                    {Number(day.slice(8))}
                  </span>
                  <span className="mt-[2px] flex h-[3px] items-center gap-[2px]">
                    {cell?.events ? (
                      <span
                        className="h-[3px] w-[3px] rounded-full"
                        style={{ background: isToday ? "#141212" : AMBER }}
                      />
                    ) : null}
                    {cell?.proposals ? (
                      <span
                        className="h-[3px] w-[3px] rounded-full border"
                        style={{ borderColor: isToday ? "#141212" : AMBER }}
                      />
                    ) : null}
                    {cell?.notes ? (
                      <span
                        className="h-[3px] w-[3px] rounded-full"
                        style={{ background: isToday ? "rgba(20,18,18,0.55)" : DIM }}
                      />
                    ) : null}
                  </span>
                </button>
              );
            })}
          </div>

          {notConnected ? (
            <div className="mb-3 border-t border-[#232323] pt-2.5">
              <p className="text-[11px] leading-snug text-white">
                {month?.connecting
                  ? "Finish the consent in the Google tab that just opened."
                  : month?.state === "needs_credentials"
                    ? "One file away from live:"
                    : month?.state === "not_connected"
                      ? "Google Calendar not authorised yet."
                      : month?.state === "libs_missing"
                        ? "The Google client libraries are not installed."
                        : "The last calendar sync failed."}
              </p>

              {month?.state === "needs_credentials" && month.credentials_path ? (
                <p className="num mt-1 break-all text-[8px] leading-snug text-[#c98a3d]">
                  {month.credentials_path}
                </p>
              ) : null}

              {/* The headline already says it for the two ordinary states;
                  only a real error earns a second line. */}
              {month && month.detail
                && !["needs_credentials", "not_connected"].includes(month.state) ? (
                <p className="mt-1 text-[9px] leading-snug text-dim">{month.detail}</p>
              ) : null}

              <p className="mt-1 text-[9px] text-dim">
                Dates are real; event data is not connected.
              </p>

              {/* The card could say it was unauthorised but gave you nothing
                  to press. Same control the Email card has, same states. */}
              {(month?.state === "not_connected" || month?.state === "needs_credentials") ? (
                <button
                  type="button"
                  onClick={() => post("/calendar/connect")}
                  disabled={month?.state === "needs_credentials" || month?.connecting}
                  className="num mt-2 cursor-pointer rounded-full border border-[#ff7a00] px-3 py-1 text-[8px] text-[#ff7a00] hover:bg-[#ff7a00]/10 disabled:cursor-not-allowed disabled:border-[#333] disabled:text-dim"
                >
                  {month?.connecting ? "WAITING FOR GOOGLE…" : "CONNECT GOOGLE CALENDAR"}
                </button>
              ) : null}
            </div>
          ) : null}

          <p className="rubric-sub mb-1.5 text-[8px]">What&rsquo;s Next</p>
          {next && next.events.length > 0 ? (
            <ul className="flex flex-col gap-1.5">
              {next.events.map((ev) => (
                <li key={`${ev.day}-${ev.summary}`} className="flex items-baseline justify-between gap-2 text-[11px]">
                  <span className="truncate text-white">{ev.summary}</span>
                  <span className="num shrink-0 text-dim">
                    {/* A date only when it is not today - "all day" on its
                        own reads as today, which for a November birthday
                        would be plainly wrong. */}
                    {ev.today ? (ev.time ?? "—") : `${dayLabel(ev.day)}${ev.time && ev.time !== "all day" ? ` ${ev.time}` : ""}`}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[10px] text-dim">
              {next && next.state !== "ok" ? "Not connected." : "Nothing scheduled."}
            </p>
          )}

          {month && month.pending_proposals > 0 ? (
            <p className="mt-2 text-[9px]" style={{ color: AMBER }}>
              {month.pending_proposals} agent proposal{month.pending_proposals > 1 ? "s" : ""} awaiting you
            </p>
          ) : null}

          {/* Footer, same shape as the Email card's: when it is connected it
              says which account and when it last synced; when it is not, it
              says so rather than showing a blank. */}
          <p className="num mt-3 border-t border-[#232323] pt-2 text-[8px] text-dim">
            {month?.state === "ok"
              ? `SYNCED ${clockOf(month.synced_at)} · ${month.event_count} EVENTS`
              : month?.connecting
                ? "AWAITING GOOGLE CONSENT"
                : "UNCONNECTED"}
          </p>
        </>
      ) : (
        <WakaBody waka={waka} />
      )}

      {/* The popover: to the RIGHT of the card, in the gutter before the
          centre column, so it never covers the grid being read. */}
      {hover && detail ? (
        <div
          className="rubric-panel day-popover absolute z-30 w-[236px] p-3"
          style={{ top: Math.max(hover.top - 10, 0) }}
          onMouseEnter={() => closeTimer.current && window.clearTimeout(closeTimer.current)}
          onMouseLeave={scheduleClose}
          role="tooltip"
        >
          <p className="rubric-sub mb-2 text-[8px]">{detail.label}</p>

          {detail.coding ? (
            <p className="mb-2 text-[10px] text-white">
              <span className="num" style={{ color: AMBER }}>
                {detail.coding.display}
              </span>{" "}
              coding
              {detail.coding.top_project ? (
                <span className="text-dim"> &middot; {detail.coding.top_project}</span>
              ) : null}
            </p>
          ) : null}

          {detail.events.length > 0 ? (
            <ul className="mb-2 flex flex-col gap-1">
              {detail.events.map((ev, i) => (
                <li key={i} className="flex items-baseline justify-between gap-2 text-[10px]">
                  <span className="min-w-0 truncate text-white">{ev.summary}</span>
                  <span className="num shrink-0 text-dim">{ev.time ?? ""}</span>
                </li>
              ))}
            </ul>
          ) : null}

          {detail.notes.length > 0 ? (
            <ul className="mb-2 flex flex-col gap-[3px] border-t border-[#232323] pt-2">
              {detail.notes.map((note, i) => (
                <li key={i} className="text-[10px] leading-snug text-dim">
                  &middot; {note.text}
                </li>
              ))}
            </ul>
          ) : null}

          {detail.proposals.length > 0 ? (
            <div className="border-t border-[#232323] pt-2">
              <p className="rubric-sub mb-1.5 text-[8px]">Agent proposes</p>
              {detail.proposals.map((p) => (
                <div key={p.id} className="mb-2">
                  <p className="text-[10px] text-white">
                    {p.summary} <span className="num text-dim">{p.time ?? ""}</span>
                  </p>
                  {p.reason ? <p className="text-[9px] leading-snug text-dim">{p.reason}</p> : null}
                  {p.status === "pending" ? (
                    <div className="mt-1 flex gap-1.5">
                      <button type="button" className="pill" onClick={() => decide(p.id, "approve")}>
                        Add to calendar
                      </button>
                      <button type="button" className="pill" onClick={() => decide(p.id, "reject")}>
                        Dismiss
                      </button>
                    </div>
                  ) : (
                    <p className="text-[9px]" style={{ color: AMBER }}>
                      on your calendar
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : null}

          {!detail.coding && detail.events.length === 0 && detail.notes.length === 0 &&
          detail.proposals.length === 0 ? (
            <p className="text-[10px] text-dim">Nothing recorded.</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

/** The WAKA half of the switch. Same card, same type scale. */
function WakaBody({ waka }: { waka: WakaPayload | null }) {
  if (!waka) {
    return <p className="py-6 text-center text-[10px] text-dim">Reading WakaTime&hellip;</p>;
  }

  if (waka.state !== "ok") {
    return (
      <div className="py-4">
        <p className="rubric-sub mb-1.5 text-[8px]">WakaTime</p>
        <p className="text-[10px] leading-snug text-dim">
          {waka.state === "not_connected" ? "Not connected." : "Cannot read WakaTime."}
          <br />
          <span className="text-[9px]">{waka.detail}</span>
        </p>
        {waka.snapshot_days ? (
          <p className="mt-2 text-[9px] text-dim">{waka.snapshot_days} days already snapshotted locally.</p>
        ) : null}
      </div>
    );
  }

  const peak = Math.max(1, ...(waka.week ?? []).map((d) => d.seconds ?? 0));

  return (
    <>
      <div className="mb-3 flex items-baseline gap-2 border-y border-[#232323] py-2">
        <span className="num rubric-accent text-[22px] font-semibold leading-none">
          {waka.today ?? "—"}
        </span>
        <span className="rubric-sub text-[8px]">
          Coded
          <br />
          Today
        </span>
      </div>

      <p className="rubric-sub mb-1.5 text-[8px]">Last 7 days</p>
      <div className="mb-3 flex items-end justify-between gap-1">
        {(waka.week ?? []).map((d) => (
          <div key={d.day} className="flex flex-1 flex-col items-center gap-1" title={d.display ?? "no data"}>
            <span
              className="w-full rounded-[1px]"
              style={{
                height: `${Math.max(2, ((d.seconds ?? 0) / peak) * 34)}px`,
                background: d.seconds ? AMBER : "#242424",
              }}
            />
            <span className="rubric-sub text-[7px]">{d.letter}</span>
          </div>
        ))}
      </div>

      {waka.languages && waka.languages.length > 0 ? (
        <>
          <p className="rubric-sub mb-1.5 text-[8px]">Languages &middot; 7d</p>
          <ul className="mb-3 flex flex-col gap-1">
            {waka.languages.map((lang) => (
              <li key={lang.name} className="flex items-center gap-2 text-[10px]">
                <span className="w-16 shrink-0 truncate text-white">{lang.name}</span>
                <span className="h-[3px] flex-1 rounded-[1px] bg-[#242424]">
                  <span
                    className="block h-full rounded-[1px]"
                    style={{ width: `${lang.percent}%`, background: AMBER }}
                  />
                </span>
                <span className="num w-9 shrink-0 text-right text-dim">{lang.percent}%</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {waka.stats_detail ? (
        <p className="mb-2 text-[9px] leading-snug text-dim">{waka.stats_detail}</p>
      ) : null}

      <p className="rubric-sub text-[8px]">
        {waka.daily_average ? `${waka.daily_average} daily avg` : ""}
        {waka.snapshot_days ? ` · ${waka.snapshot_days}d stored` : ""}
      </p>
    </>
  );
}
