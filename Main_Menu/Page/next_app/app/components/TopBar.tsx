"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

/** The top bar (owner request, 2026-09-02): the name and logo on the left,
    every screen's navigation across the middle, and the live date + clock on
    the right. Replaces the old left-column NAVIGATION box (NavPanel) and
    takes over the calendar panel's clock — the left column now starts with
    the calendar itself, pushed all the way up.

    Self-contained (AGENTS rule 4): its own fetch of this screen's
    /api/main_menu/navigation (MODEL first, one fallback row when discovery
    is offline), its own inline glyph set, its own client-only clock so the
    static export never mismatches on hydration. */

type Screen = { key: string; label: string; address: string | null; tabs?: { label: string }[] };

// A screen's folder key picks one of these interchangeable marks; an
// unknown key falls back to a dot. No screen name decides behaviour.
const GLYPHS: Record<string, React.ReactNode> = {
  model: (
    <path
      d="M9 5a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8V16a3 3 0 0 0 5 2 3 3 0 0 0 5-2v-2.2A3 3 0 0 0 15 8a3 3 0 0 0-3-3 3 3 0 0 0-3 0z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
  ),
  finance: (
    <>
      <path d="M4 4v16h16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <polyline
        points="6,16 10,11 14,14 19,6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),
  learning: (
    <>
      <path d="M7 3h7l4 4v14H7z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M9.5 12h5M9.5 16h5" stroke="currentColor" strokeWidth="1.3" />
    </>
  ),
  agents: (
    <>
      <path d="M4 8h16v11H4z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M8 8V4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M16 8V4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M9 13h.01" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M15 13h.01" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M9 16h6" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </>
  ),
  dot: <circle cx="12" cy="12" r="3.4" fill="none" stroke="currentColor" strokeWidth="1.4" />,
};

const glyphFor = (key: string) => GLYPHS[key] ?? GLYPHS.dot;

type Entry = { key: string; label: string; href: string; external: boolean; blurb: string };

const strip = (p: string) => p.replace(/index\.html$/, "").replace(/\/$/, "") || "/";
const isExternal = (href: string) => /^https?:\/\//.test(href);

// MODEL leads the list; the fallback fills in only when discovery has not
// reported a Screens/Model/ row. There is no "Home" row - the ring is home.
const MODEL_FALLBACK: Entry = {
  key: "model",
  label: "Model",
  href: "/model/",
  external: false,
  blurb: "Model gateway - models, usage, logs",
};

// ISO-8601 week number, for the "Wk36 | Sep 2 2026 (Tue)" stamp.
function isoWeek(d: Date): number {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  return Math.ceil(((t.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
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

export function TopBar() {
  const [screens, setScreens] = useState<Screen[]>([]);
  const [reachable, setReachable] = useState(true);
  const here = strip(usePathname() || "/");
  const now = useClock();

  const load = useCallback(() => {
    return fetch("/api/main_menu/navigation", { headers: { accept: "application/json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data) => {
        const list: Screen[] = Array.isArray(data?.screens) ? data.screens : [];
        setScreens(list.filter((s) => s && s.address));
        setReachable(true);
      })
      .catch(() => setReachable(false));
  }, []);

  useEffect(() => {
    let alive = true;
    load().finally(() => {
      if (!alive) return;
    });
    return () => {
      alive = false;
    };
  }, [load]);

  const discovered: Entry[] = screens.map((s) => ({
    key: s.key,
    label: s.label,
    href: s.address as string,
    external: isExternal(s.address as string),
    blurb: s.tabs?.length ? s.tabs.map((t) => t.label).join(" · ") : `Open ${s.label}`,
  }));

  const isModel = (e: Entry) => e.key === "model" || e.key === "models";
  const modelRow = discovered.find(isModel) ?? MODEL_FALLBACK;
  const entries: Entry[] = [modelRow, ...discovered.filter((e) => !isModel(e))];

  const activeHref = (href: string) => !isExternal(href) && strip(href) === here;

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
  const date = now
    ? `Wk${isoWeek(now)} | ${now.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })} (${now.toLocaleDateString("en-US", { weekday: "short" })})`
    : null;
  const zone = now
    ? now
        .toLocaleTimeString("en-US", { timeZoneName: "short" })
        .match(/, ([^,]+)$/)
        ?.[1] ?? null
    : null;

  const linkCls = (active: boolean) =>
    `flex items-center gap-1.5 whitespace-nowrap text-[12px] no-underline transition-colors ${
      active ? "text-[#ff7a00]" : "text-dim hover:text-white"
    }`;

  return (
    <header className="mx-auto grid w-full max-w-[1512px] grid-cols-[1fr_auto_1fr] items-center gap-6 px-6 py-2.5">
      {/* left - the name and logo, moved up from the centre column */}
      <div className="flex items-center gap-2.5">
        <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 2.5 20.5 7v10L12 21.5 3.5 17V7z"
            fill="none"
            stroke="#ff7a00"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        </svg>
        <div>
          <h1 className="text-lg font-semibold leading-none tracking-[0.14em]">
            Kage<span className="rubric-accent font-normal">.GG</span>
          </h1>
          <p className="rubric-sub mt-1 text-[9px]">Vivek Kumar &nbsp;|&nbsp; KageEnsui</p>
        </div>
      </div>

      {/* middle - the navigation, moved up from the left column */}
      <nav aria-label="Screens" className="flex items-center gap-5">
        {entries.map((e) => {
          const active = activeHref(e.href);
          const cls = linkCls(active);
          return e.external ? (
            <a key={e.key} href={e.href} title={e.blurb} className={cls}>
              <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                {glyphFor(e.key)}
              </svg>
              {e.label}
            </a>
          ) : (
            <Link
              key={e.key}
              href={e.href}
              title={e.blurb}
              aria-current={active ? "page" : undefined}
              className={cls}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                {glyphFor(e.key)}
              </svg>
              {e.label}
            </Link>
          );
        })}
        <button
          type="button"
          aria-label="Refresh screen list"
          className="text-dim transition-colors hover:text-white"
          onClick={() => load()}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M20 12a8 8 0 1 1-2.3-5.6M20 3v4h-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </nav>

      {/* right - the live date and time, moved up from the calendar panel */}
      <div className="flex items-baseline justify-end gap-3 text-right">
        {date && <span className="rubric-sub text-[10px]">{date}</span>}
        <span className="num rubric-accent text-[20px] font-semibold leading-none">{clock}</span>
        {zone && <span className="rubric-sub text-[9px]">{zone}</span>}
      </div>

      {!reachable ? (
        <p className="col-span-3 -mt-2 text-center text-[9px] uppercase tracking-[0.1em] text-[#6b7079]">
          screen list offline &mdash; showing built-in routes
        </p>
      ) : null}
    </header>
  );
}
