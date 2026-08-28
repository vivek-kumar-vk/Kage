"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

/** Left column, top module - the Main Menu's real navigation, wearing
    the reference's "MICRO APPS" panel design (it replaces that static
    panel). Same shell: a .rubric-panel, an icon + label header with a
    trailing pill, then one row per destination - square outline glyph,
    title, one-line blurb, trailing arrow.

    The RUBRIC rebuild (ed29673) shipped with no way off the home
    screen. This panel is the way: a fixed HOME row, every screen the
    backend discovers, and MODEL. It is a complete independent component
    (AGENTS rule 4) - its own fetch of this screen's own
    /api/main_menu/navigation (the endpoint the old plain-HTML and
    Svelte menus used), its own inline glyph set (no icon font, so the
    static export stays self-contained), nothing shared. */

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
  enhancement: (
    <path d="M13 2 5 14h5l-1 8 8-13h-5l1-7z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
  ),
  dot: <circle cx="12" cy="12" r="3.4" fill="none" stroke="currentColor" strokeWidth="1.4" />,
};

const glyphFor = (key: string) => GLYPHS[key] ?? GLYPHS.dot;

type Entry = { key: string; label: string; blurb: string; href: string; external: boolean };

const strip = (p: string) => p.replace(/index\.html$/, "").replace(/\/$/, "") || "/";
const isExternal = (href: string) => /^https?:\/\//.test(href);

// MODEL leads the list. It comes from discovery once Screens/Model/ is
// built; this is the fallback row for when the nav endpoint is offline.
// There is no "Home" row - the ring itself is home.
const MODEL_FALLBACK: Entry = {
  key: "model",
  label: "Model",
  blurb: "LiteLLM gateway - models, usage, logs",
  href: "/model/",
  external: false,
};

export function NavPanel() {
  const [screens, setScreens] = useState<Screen[]>([]);
  const [reachable, setReachable] = useState(true);
  const here = strip(usePathname() || "/");

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
    blurb: s.tabs?.length ? s.tabs.map((t) => t.label).join(" · ") : `Open ${s.label}`,
    href: s.address as string,
    external: isExternal(s.address as string),
  }));

  // MODEL first, then the other screens in discovery order. The fallback
  // fills in only when discovery has not reported a Screens/Model/ row.
  const isModel = (e: Entry) => e.key === "model" || e.key === "models";
  const modelRow = discovered.find(isModel) ?? MODEL_FALLBACK;
  const entries: Entry[] = [modelRow, ...discovered.filter((e) => !isModel(e))];

  const activeHref = (href: string) => !isExternal(href) && strip(href) === here;

  return (
    <section aria-label="Navigation" className="rubric-panel p-4">
      <header className="mb-4 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="m15 9-4 1.5L9.5 15l4-1.5z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
          </svg>
          Navigation
        </p>
        <button type="button" className="pill" onClick={() => load()}>
          &#8635; Refresh
        </button>
      </header>

      <ul className="flex flex-col">
        {entries.map((e) => {
          const active = activeHref(e.href);
          const body = (
            <>
              <span
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded border text-dim"
                style={{ borderColor: active ? "#ff7a00" : "#333" }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                  {glyphFor(e.key)}
                </svg>
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] font-medium text-white">{e.label}</span>
                <span className="block truncate text-[11px] text-dim">{e.blurb}</span>
              </span>
              <span className="shrink-0 text-dim transition-colors group-hover:text-white">&rarr;</span>
            </>
          );
          const cls =
            "group flex items-center gap-3 border-t border-[#232323] py-3 first:border-t-0 no-underline";
          return (
            <li key={e.key}>
              {e.external ? (
                <a href={e.href} className={cls} data-active={active ? "" : undefined}>
                  {body}
                </a>
              ) : (
                <Link
                  href={e.href}
                  aria-current={active ? "page" : undefined}
                  className={cls}
                  data-active={active ? "" : undefined}
                >
                  {body}
                </Link>
              )}
            </li>
          );
        })}
      </ul>

      {!reachable ? (
        <p className="mt-3 text-[10px] uppercase tracking-[0.1em] text-[#6b7079]">
          screen list offline &mdash; showing built-in routes
        </p>
      ) : null}
    </section>
  );
}
