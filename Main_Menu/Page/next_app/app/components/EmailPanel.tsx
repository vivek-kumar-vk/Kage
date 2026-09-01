"use client";

/** Right column, top module - "EMAIL" from the reference: a 24h count,
    a flagged list, a TODAY'S MIX bar with its legend, and a synced
    footer. Static content, an exact copy of the reference image. */

const FLAGGED = [
  { subject: "Sponsorship proposal – AI dev tools brand", age: "2h" },
  { subject: "Enterprise plan inquiry – 40 seats", age: "4h" },
  { subject: "Partnership: newsletter cross-promo", age: "7h" },
];

const MIX = [
  { label: "PARTNERS", value: 6, colour: "#ff7a00" },
  { label: "14 LEADS", value: 14, colour: "#6b6b6b" },
  { label: "PERSONA", value: 4, colour: "#3f3f3f" },
  { label: "18 OTHER", value: 18, colour: "#2a2a2a" },
];

const MIX_TOTAL = MIX.reduce((n, s) => n + s.value, 0);

function EnvelopeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true" className="shrink-0 text-dim">
      <rect x="3" y="5" width="18" height="14" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3.5 6.5 12 13l8.5-6.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function EmailPanel() {
  return (
    <section aria-label="Email" className="rubric-panel p-4">
      <header className="mb-3 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <EnvelopeIcon />
          Email
        </p>
        <span className="rubric-sub text-[8px] normal-case tracking-normal text-dim">synced 4m ago</span>
      </header>

      <div className="flex items-baseline gap-2">
        <span className="num rubric-accent text-[26px] font-semibold leading-none">47</span>
        <span className="rubric-sub text-[9px]">
          Emails
          <br />
          Past 24h
        </span>
      </div>

      <p className="rubric-sub mt-3 text-[8px]">Flagged &middot; Needs Jay</p>
      <ul className="mt-1.5 flex flex-col">
        {FLAGGED.map((row) => (
          <li
            key={row.subject}
            className="flex items-center gap-2 border-t border-[#232323] py-2 first:border-t-0"
          >
            <EnvelopeIcon />
            <span className="min-w-0 flex-1 truncate text-[11px] text-white">{row.subject}</span>
            <span className="num shrink-0 text-[10px] text-dim">{row.age}</span>
          </li>
        ))}
      </ul>

      <p className="rubric-sub mt-3 text-[8px]">Today&rsquo;s Mix</p>
      <div className="mt-1.5 flex h-1.5 overflow-hidden rounded-full">
        {MIX.map((seg) => (
          <div
            key={seg.label}
            style={{ width: `${(seg.value / MIX_TOTAL) * 100}%`, background: seg.colour }}
          />
        ))}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
        {MIX.map((seg) => (
          <span key={seg.label} className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: seg.colour }} />
            <span className="rubric-sub text-[7px]">{seg.label}</span>
          </span>
        ))}
      </div>

      <p className="num mt-3 border-t border-[#232323] pt-2 text-[8px] text-dim">
        SYNCED 02:31 PM &middot; team@robonuggets.com
      </p>
    </section>
  );
}
