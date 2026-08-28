"use client";

import { useEffect, useState } from "react";

interface ScreenRow {
  key: string;
  label: string;
  order: number;
  address: string;
  tabs: { key: string; label: string; endpoint: string }[];
}
interface Navigation {
  screens: ScreenRow[];
  not_built: { key: string; label: string; clickable: false }[];
}

/** The centre-column header: title + greeting, then one nav tab per
    built screen (discovered live from /api/main_menu/navigation, never
    a hardcoded list). The clock lives in TodayPanel now, matching the
    reference layout's calendar module - this header stays just title +
    nav, same as the reference's title-and-icon-row. */
export function HeaderNav() {
  const [nav, setNav] = useState<Navigation | null>(null);
  const [failed, setFailed] = useState(false);
  const [hour, setHour] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/main_menu/navigation")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        if (!cancelled) setNav(body);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setHour(new Date().getHours());
  }, []);

  const greeting = hour === null ? "hey" : hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";

  return (
    <header aria-label="INKY home header" className="flex flex-col items-center gap-3 text-center">
      <div>
        <h1 className="num text-2xl font-bold tracking-tight text-white">
          INKY <span style={{ color: "var(--agentic-amber, #ff7a00)" }}>// home</span>
        </h1>
        <p className="num text-xs text-dim">good {greeting}</p>
      </div>

      <nav aria-label="Screens" className="flex flex-wrap items-center justify-center gap-1.5">
        {failed && (
          <span data-fresh="unavailable" className="num text-xs text-amber">
            screen discovery unavailable
          </span>
        )}
        {!nav && !failed && (
          <span data-fresh="empty" className="num text-xs text-dim">
            walking the Screens folder&hellip;
          </span>
        )}
        {nav?.screens.map((s) => (
          <a
            key={s.key}
            href={s.address}
            data-screen={s.key}
            className="num rounded-full border px-3 py-1 text-[10px] uppercase tracking-widest text-dim transition-colors"
            style={{ borderColor: "#333" }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--agentic-amber, #ff7a00)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#333")}
          >
            {s.label}
          </a>
        ))}
        {nav?.not_built.map((n) => (
          <span
            key={n.key}
            data-not-built={n.key}
            className="num rounded-full border border-dashed px-3 py-1 text-[10px] uppercase tracking-widest text-dim opacity-50"
            style={{ borderColor: "#333" }}
          >
            {n.label}
          </span>
        ))}
      </nav>
    </header>
  );
}
