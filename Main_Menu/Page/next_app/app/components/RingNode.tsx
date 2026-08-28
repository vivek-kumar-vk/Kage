"use client";

/** One node on the agent ring - a thin outline glyph inside a circular
    badge, with a tiny monospace cadence tag beneath it (1d, 3d, 14d,
    ...), exactly the visual language of the reference image. The glyph
    is chosen from a small hand-drawn set (no icon font, so the static
    export stays self-contained). The `info` variant is the one enlarged,
    amber-outlined node on the right of the ring. */

const GLYPHS: Record<string, (s: string) => React.ReactNode> = {
  bolt: (s) => (
    <path d="M13 2 5 14h5l-1 8 8-13h-5l1-7z" fill="none" stroke={s} strokeWidth="1.5" strokeLinejoin="round" />
  ),
  mail: (s) => (
    <>
      <rect x="3" y="5" width="18" height="14" rx="1.5" fill="none" stroke={s} strokeWidth="1.5" />
      <path d="M3.5 6.5 12 13l8.5-6.5" fill="none" stroke={s} strokeWidth="1.5" />
    </>
  ),
  play: (s) => (
    <>
      <circle cx="12" cy="12" r="8.5" fill="none" stroke={s} strokeWidth="1.5" />
      <path d="M10 8.5 16 12l-6 3.5z" fill="none" stroke={s} strokeWidth="1.5" strokeLinejoin="round" />
    </>
  ),
  doc: (s) => (
    <>
      <path d="M7 3h7l4 4v14H7z" fill="none" stroke={s} strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M9.5 12h5M9.5 16h5" stroke={s} strokeWidth="1.3" />
    </>
  ),
  gear: (s) => (
    <>
      <circle cx="12" cy="12" r="3.3" fill="none" stroke={s} strokeWidth="1.5" />
      <path
        d="M12 3v2.4M12 18.6V21M21 12h-2.4M5.4 12H3M18.1 5.9l-1.7 1.7M7.6 16.4l-1.7 1.7M18.1 18.1l-1.7-1.7M7.6 7.6 5.9 5.9"
        stroke={s}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </>
  ),
  chart: (s) => (
    <>
      <path d="M4 4v16h16" fill="none" stroke={s} strokeWidth="1.4" strokeLinecap="round" />
      <polyline points="6,16 10,11 14,14 19,6" fill="none" stroke={s} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  grid: (s) => (
    <>
      <rect x="4" y="4" width="7" height="7" rx="1" fill="none" stroke={s} strokeWidth="1.4" />
      <rect x="13" y="4" width="7" height="7" rx="1" fill="none" stroke={s} strokeWidth="1.4" />
      <rect x="4" y="13" width="7" height="7" rx="1" fill="none" stroke={s} strokeWidth="1.4" />
      <rect x="13" y="13" width="7" height="7" rx="1" fill="none" stroke={s} strokeWidth="1.4" />
    </>
  ),
  node: (s) => (
    <>
      <circle cx="6" cy="7" r="2" fill="none" stroke={s} strokeWidth="1.4" />
      <circle cx="18" cy="7" r="2" fill="none" stroke={s} strokeWidth="1.4" />
      <circle cx="12" cy="18" r="2" fill="none" stroke={s} strokeWidth="1.4" />
      <path d="M7.6 8.3 10.6 16.3M16.4 8.3 13.4 16.3M8 7h8" stroke={s} strokeWidth="1.2" />
    </>
  ),
  eye: (s) => (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" fill="none" stroke={s} strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.6" fill="none" stroke={s} strokeWidth="1.5" />
    </>
  ),
  target: (s) => (
    <>
      <circle cx="12" cy="12" r="8" fill="none" stroke={s} strokeWidth="1.4" />
      <circle cx="12" cy="12" r="3.4" fill="none" stroke={s} strokeWidth="1.4" />
    </>
  ),
  brain: (s) => (
    <path
      d="M9 5a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8V16a3 3 0 0 0 5 2 3 3 0 0 0 5-2v-2.2A3 3 0 0 0 15 8a3 3 0 0 0-3-3 3 3 0 0 0-3 0z"
      fill="none"
      stroke={s}
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
  ),
  terminal: (s) => (
    <>
      <rect x="3" y="4" width="18" height="16" rx="1.5" fill="none" stroke={s} strokeWidth="1.4" />
      <path d="M7 9l3 3-3 3M12.5 15H17" stroke={s} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  info: (s) => (
    <>
      <circle cx="12" cy="12" r="8.5" fill="none" stroke={s} strokeWidth="1.6" />
      <path d="M12 11v5" stroke={s} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="7.7" r="1.05" fill={s} />
    </>
  ),
};

export type GlyphName = keyof typeof GLYPHS;

export function RingNode({
  glyph,
  cadence,
  variant = "default",
}: {
  glyph: GlyphName;
  cadence?: string;
  variant?: "default" | "active" | "info";
}) {
  const isInfo = variant === "info";
  const isActive = variant === "active";
  const stroke = isInfo || isActive ? "#ff7a00" : "#c7ccd4";
  const dim = 44;

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="flex items-center justify-center rounded-full border"
        style={{
          width: isInfo ? 56 : dim,
          height: isInfo ? 56 : dim,
          borderColor: isInfo || isActive ? "#ff7a00" : "#333333",
          background: "#141212",
          boxShadow: isInfo
            ? "0 0 18px rgba(255,122,0,0.55)"
            : isActive
              ? "0 0 10px rgba(255,122,0,0.35)"
              : "inset 0 0 10px rgba(255,255,255,0.03)",
        }}
      >
        <svg
          width={isInfo ? 26 : 20}
          height={isInfo ? 26 : 20}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          {GLYPHS[glyph](stroke)}
        </svg>
      </div>
      {cadence ? (
        <span
          className="num text-[7px] leading-none tracking-wide"
          style={{ color: "#6b7079" }}
        >
          {cadence}
        </span>
      ) : null}
    </div>
  );
}
