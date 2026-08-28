"use client";

/** One ring node - a bespoke minimalist outline glyph per agent, in the
    reference image's own visual language (thin outline icons in a
    circular badge), never a hardcoded per-agent assignment: the glyph is
    picked deterministically from the agent's own name, the same
    "discovered, never configured" rule the fleet roster itself already
    follows. A new agent gets a glyph automatically the first time the
    fleet endpoint returns it. */

function hash_name(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return h;
}

// Eight bespoke outline glyphs, drawn once here - not a third-party icon
// font, so the static export stays self-contained.
const GLYPHS: Array<(stroke: string) => React.ReactNode> = [
  // bolt
  (s) => <path d="M13 3 6 14h5l-1 8 8-13h-5l1-6z" fill="none" stroke={s} strokeWidth="1.6" strokeLinejoin="round" />,
  // shield
  (s) => <path d="M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6l7-3z" fill="none" stroke={s} strokeWidth="1.6" strokeLinejoin="round" />,
  // radar
  (s) => (
    <>
      <circle cx="12" cy="12" r="8" fill="none" stroke={s} strokeWidth="1.4" />
      <circle cx="12" cy="12" r="3.2" fill="none" stroke={s} strokeWidth="1.4" />
      <line x1="12" y1="12" x2="17" y2="7" stroke={s} strokeWidth="1.4" />
    </>
  ),
  // document
  (s) => (
    <>
      <path d="M7 3h7l4 4v14H7z" fill="none" stroke={s} strokeWidth="1.5" strokeLinejoin="round" />
      <line x1="9.5" y1="12" x2="15" y2="12" stroke={s} strokeWidth="1.3" />
      <line x1="9.5" y1="16" x2="15" y2="16" stroke={s} strokeWidth="1.3" />
    </>
  ),
  // gear
  (s) => (
    <>
      <circle cx="12" cy="12" r="3.4" fill="none" stroke={s} strokeWidth="1.5" />
      <path
        d="M12 3v2.4M12 18.6V21M21 12h-2.4M5.4 12H3M18.1 5.9l-1.7 1.7M7.6 16.4l-1.7 1.7M18.1 18.1l-1.7-1.7M7.6 7.6 5.9 5.9"
        stroke={s}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </>
  ),
  // eye / watcher
  (s) => (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" fill="none" stroke={s} strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.6" fill="none" stroke={s} strokeWidth="1.5" />
    </>
  ),
  // chart
  (s) => (
    <>
      <line x1="4" y1="20" x2="4" y2="4" stroke={s} strokeWidth="1.4" strokeLinecap="round" />
      <line x1="4" y1="20" x2="20" y2="20" stroke={s} strokeWidth="1.4" strokeLinecap="round" />
      <polyline points="6,16 10,11 14,14 19,6" fill="none" stroke={s} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  // node / graph
  (s) => (
    <>
      <circle cx="6" cy="7" r="2" fill="none" stroke={s} strokeWidth="1.4" />
      <circle cx="18" cy="7" r="2" fill="none" stroke={s} strokeWidth="1.4" />
      <circle cx="12" cy="18" r="2" fill="none" stroke={s} strokeWidth="1.4" />
      <line x1="7.6" y1="8.3" x2="10.6" y2="16.3" stroke={s} strokeWidth="1.2" />
      <line x1="16.4" y1="8.3" x2="13.4" y2="16.3" stroke={s} strokeWidth="1.2" />
      <line x1="8" y1="7" x2="16" y2="7" stroke={s} strokeWidth="1.2" />
    </>
  ),
];

export function AgentGlyphNode({ name, active }: { name: string; active: boolean }) {
  const h = hash_name(name);
  const glyph = GLYPHS[h % GLYPHS.length];
  const stroke = active ? "var(--agentic-amber, #ff7a00)" : "#8B9099";

  return (
    <div
      className="flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-150"
      style={{
        borderColor: active ? "var(--agentic-amber, #ff7a00)" : "#333",
        background: "var(--agentic-panel, #141212)",
        boxShadow: active ? "0 0 10px rgba(255,122,0,0.55)" : "none",
      }}
    >
      <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
        {glyph(stroke)}
      </svg>
    </div>
  );
}
