"use client";

/** Right column, middle module - "SKILLS DECK" from the reference: a
    + ADD SKILL pill, a "tap play to run" hint, then a 2x2 grid of skill
    cards, each with a glyph, a /name, a MODEL . TIER line, and a
    play + gear control row. Static content, an exact copy of the
    reference image. */

type Skill = { name: string; model: string; tier: string; glyph: React.ReactNode };

const SKILLS: Skill[] = [
  {
    name: "/sprint-planning",
    model: "OPUS",
    tier: "XHIGH",
    glyph: (
      <>
        <rect x="4" y="5" width="16" height="15" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M4 9h16M8 3v4M16 3v4M8 13h4M8 16h7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </>
    ),
  },
  {
    name: "/newsletter",
    model: "OPUS",
    tier: "XHIGH",
    glyph: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M3.5 6.5 12 13l8.5-6.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </>
    ),
  },
  {
    name: "/games",
    model: "OPUS",
    tier: "XHIGH",
    glyph: (
      <>
        <rect x="3" y="7" width="18" height="10" rx="4" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M7 12h3M8.5 10.5v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        <circle cx="15.5" cy="11" r="1" fill="currentColor" />
        <circle cx="17.5" cy="13" r="1" fill="currentColor" />
      </>
    ),
  },
  {
    name: "/clean-up",
    model: "FABLE",
    tier: "XHIGH",
    glyph: (
      <>
        <path d="M6 21 4 8h16l-2 13z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M9 8V5a3 3 0 0 1 6 0v3" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </>
    ),
  },
];

function PlayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 6 18 12 8 18z" fill="currentColor" />
    </svg>
  );
}
function GearIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="3.3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 3v2.4M12 18.6V21M21 12h-2.4M5.4 12H3M18.1 5.9l-1.7 1.7M7.6 16.4l-1.7 1.7M18.1 18.1l-1.7-1.7M7.6 7.6 5.9 5.9"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function SkillsDeckPanel() {
  return (
    <section aria-label="Skills deck" className="rubric-panel p-3">
      <header className="mb-2 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
            <path d="M13 2 5 14h5l-1 8 8-13h-5l1-7z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
          </svg>
          Skills Deck
        </p>
        <div className="flex items-center gap-2">
          <span className="rubric-sub text-[8px] normal-case tracking-normal text-dim">tap &#9654; to run</span>
          <button type="button" className="pill">+ Add Skill</button>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-2">
        {SKILLS.map((s) => (
          <div key={s.name} className="flex flex-col gap-1.5 rounded border border-[#2a2a2a] bg-[#1a1818] p-2">
            <span className="text-dim">
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
                {s.glyph}
              </svg>
            </span>
            <span className="num truncate text-[11px] font-medium text-white" title={s.name}>
              {s.name}
            </span>
            <span className="rubric-sub text-[7px]">
              <span className="rubric-accent">{s.model}</span> &middot; {s.tier}
            </span>
            <div className="mt-0.5 flex items-center gap-1.5">
              <button
                type="button"
                aria-label={`run ${s.name}`}
                className="flex h-5 w-5 items-center justify-center rounded border border-[#ff7a00] text-[#ff7a00]"
              >
                <PlayIcon />
              </button>
              <button
                type="button"
                aria-label={`configure ${s.name}`}
                className="flex h-5 w-5 items-center justify-center rounded border border-[#333] text-dim"
              >
                <GearIcon />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
