"use client";

/** Left column, top module - "MICRO APPS" from the reference: a + ADD
    APP pill in the header, then one row per app (square outline glyph,
    title, one-line description, a trailing arrow). Static content, an
    exact copy of the reference image. */

type App = { title: string; blurb: string; glyph: React.ReactNode };

const APPS: App[] = [
  {
    title: "Generations",
    blurb: "Every image and video you have generated",
    glyph: (
      <>
        <rect x="4" y="5" width="16" height="12" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="9" cy="10" r="1.6" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path d="m6 16 4-4 3 3 3-3 2 2" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      </>
    ),
  },
  {
    title: "Teleprompter",
    blurb: "Scripts you read on camera",
    glyph: (
      <>
        <rect x="3.5" y="5" width="17" height="11" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M7 9h10M7 12h7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        <path d="M9 19h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </>
    ),
  },
  {
    title: "Second Brain",
    blurb: "Your whole workspace as a living map",
    glyph: (
      <>
        <circle cx="12" cy="6" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="6" cy="17" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <circle cx="18" cy="17" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path d="M10.5 7.7 7.5 15M13.5 7.7 16.5 15M8 17h8" stroke="currentColor" strokeWidth="1.2" />
      </>
    ),
  },
  {
    title: "Excalidraw",
    blurb: "Hand-drawn diagrams ready to copy onto your canvas",
    glyph: (
      <>
        <path d="M4 20h4L18.5 9.5a2 2 0 0 0-2.83-2.83L5 17v3z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M14 8.5 16.5 11" stroke="currentColor" strokeWidth="1.2" />
      </>
    ),
  },
];

export function MicroAppsPanel() {
  return (
    <section aria-label="Micro apps" className="rubric-panel p-4">
      <header className="mb-4 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
            <rect x="4" y="4" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <rect x="13" y="4" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <rect x="4" y="13" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <rect x="13" y="13" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.8" />
          </svg>
          Micro Apps
        </p>
        <button type="button" className="pill">+ Add App</button>
      </header>

      <ul className="flex flex-col">
        {APPS.map((app) => (
          <li
            key={app.title}
            className="group flex items-center gap-3 border-t border-[#232323] py-3 first:border-t-0"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-[#333] text-dim">
              <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                {app.glyph}
              </svg>
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13px] font-medium text-white">{app.title}</span>
              <span className="block truncate text-[11px] text-dim">{app.blurb}</span>
            </span>
            <span className="shrink-0 text-dim transition-colors group-hover:text-white">&rarr;</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
