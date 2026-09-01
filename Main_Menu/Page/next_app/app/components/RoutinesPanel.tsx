"use client";

/** Right column, bottom module - "ROUTINES" from the reference: a
    fired-today count in the header, then a TIME / ROUTINE / STATUS
    table. The "NEXT" row is highlighted amber. Static content, an exact
    copy of the reference image. */

type Status = "FIRED" | "NEXT" | "QUEUED";
type Routine = { time: string; name: string; host: string; status: Status };

const ROUTINES: Routine[] = [
  { time: "11:00", name: "deliverables status sweep", host: "HERMES", status: "FIRED" },
  { time: "13:00", name: "community pulse digest", host: "HERMES", status: "FIRED" },
  { time: "15:00", name: "invoice reconciliation", host: "DESKTOP", status: "NEXT" },
  { time: "16:30", name: "content pipeline check", host: "HERMES", status: "QUEUED" },
  { time: "18:00", name: "client report drafts", host: "HERMES", status: "QUEUED" },
  { time: "20:00", name: "evening ritual", host: "DESKTOP", status: "QUEUED" },
  { time: "21:30", name: "CRM enrich + next-day prep", host: "DESKTOP", status: "QUEUED" },
];

const STATUS_COLOUR: Record<Status, string> = {
  FIRED: "#8b9099",
  NEXT: "#ff7a00",
  QUEUED: "#6b7079",
};

export function RoutinesPanel() {
  return (
    <section aria-label="Routines" className="rubric-panel p-4">
      <header className="mb-3 flex items-center justify-between">
        <p className="rubric-label flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
            <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M12 7v5l3.5 2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          Routines
        </p>
        <span className="rubric-sub text-[8px] normal-case tracking-normal text-dim">7/12 fired today</span>
      </header>

      <div className="grid grid-cols-[46px_1fr_58px] gap-x-2 border-b border-[#232323] pb-1.5">
        <span className="rubric-sub text-[7px]">Time</span>
        <span className="rubric-sub text-[7px]">Routine</span>
        <span className="rubric-sub text-right text-[7px]">Status</span>
      </div>

      <ul>
        {ROUTINES.map((r) => {
          const isNext = r.status === "NEXT";
          return (
            <li
              key={r.time}
              className="grid grid-cols-[46px_1fr_58px] items-center gap-x-2 border-b border-[#1f1f1f] py-2 last:border-b-0"
              style={isNext ? { background: "rgba(255,122,0,0.10)" } : undefined}
            >
              <span
                className="num text-[10px]"
                style={{ color: isNext ? "#ff7a00" : "#8b9099" }}
              >
                {r.time}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[11px] text-white">{r.name}</span>
                <span className="rubric-sub text-[7px]">&#9670; {r.host}</span>
              </span>
              <span
                className="num text-right text-[8px] tracking-wide"
                style={{ color: STATUS_COLOUR[r.status] }}
              >
                {r.status}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
