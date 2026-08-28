"use client";

import { useToday } from "./useToday";

// The three real boxes build_daily_checklist.py knows - core, trackb,
// capture. An unknown key is refused by the module itself.
const CHECKLIST_LABELS: Record<string, string> = {
  core: "Core track block done",
  trackb: "Track B block done",
  capture: "Captured what I learned",
};

export function TodayPanel() {
  const { data, state, fetchedAt, setChecklistKey } = useToday();

  if (state === "loading" && !data) {
    return <PanelShell freshness="empty"><p className="text-sm text-dim">loading today...</p></PanelShell>;
  }
  if (state === "error" && !data) {
    return <PanelShell freshness="unavailable"><p className="text-sm text-p5red">could not reach /api/learning/today</p></PanelShell>;
  }
  if (!data) return null;

  const freshness = state === "fresh" ? "fresh" : "stale";
  const { streak, schedule, recent_activity, checklist, due_cards, due_notes } = data;

  return (
    <PanelShell freshness={freshness} fetchedAt={fetchedAt}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatBlock label="STREAK" value={`${streak.days}d`} sub={streak.last_studied ? `last ${streak.last_studied}` : "not started"} />
        <StatBlock label="RECALL CARDS DUE" value={String(due_cards)} sub="SM-2 queue" />
        <StatBlock label="NOTES DUE" value={String(due_notes)} sub="Leitner queue" />
      </div>

      <div className="mt-4 rounded-md border border-line bg-void p-3">
        <h3 className="num text-xs tracking-widest text-dim">
          {schedule.week_found ? `WEEK ${schedule.week_num ?? "?"} · ${schedule.day_name || schedule.date}` : "NO WEEK PLANNED FOR TODAY"}
        </h3>
        {schedule.week_found ? (
          <>
            <p className="mt-1 text-sm text-bone">
              <span className="text-cyan">Track A</span> {schedule.track_a || "-"}
              <span className="mx-2 text-dim">·</span>
              <span className="text-yellow">Track B</span> {schedule.track_b || "-"}
            </p>
            {schedule.chunks?.length > 0 && (
              <ul className="mt-2 flex flex-col gap-1 text-xs text-dim">
                {schedule.chunks.map((c, i) => (
                  <li key={i}>- {c.label ?? "block"}{c.minutes ? ` (${c.minutes}m)` : ""}</li>
                ))}
              </ul>
            )}
            {schedule.note && <p className="mt-2 text-xs text-dim">{schedule.note}</p>}
          </>
        ) : (
          <p className="mt-1 text-sm text-dim">empty means not planned yet, stated plainly</p>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-md border border-line bg-void p-3">
          <h3 className="num mb-2 text-xs tracking-widest text-dim">TODAY&apos;S CHECKLIST</h3>
          <div className="flex flex-col gap-2">
            {Object.entries(CHECKLIST_LABELS).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm text-bone">
                <input
                  type="checkbox"
                  checked={Boolean(checklist?.[key])}
                  onChange={(e) => setChecklistKey(key, e.target.checked)}
                  className="h-4 w-4 accent-jade"
                />
                {label}
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-line bg-void p-3">
          <h3 className="num mb-2 text-xs tracking-widest text-dim">RECENT ACTIVITY</h3>
          {recent_activity.length === 0 ? (
            <p className="text-xs text-dim">nothing studied yet - empty beats fake</p>
          ) : (
            <ul className="flex flex-col gap-1 text-xs text-bone">
              {recent_activity.map((a, i) => (
                <li key={i} className="flex justify-between gap-2 border-b border-line/50 pb-1">
                  <span className="truncate">{a.topic || "-"}</span>
                  <span className="num shrink-0 text-dim">{a.minutes}m · {a.date}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </PanelShell>
  );
}

function StatBlock({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-md border border-line bg-void p-3">
      <p className="num text-[10px] tracking-widest text-dim">{label}</p>
      <p className="num text-2xl font-black text-jade">{value}</p>
      <p className="text-[11px] text-dim">{sub}</p>
    </div>
  );
}

function PanelShell({
  freshness,
  fetchedAt,
  children,
}: {
  freshness: string;
  fetchedAt?: Date | null;
  children: React.ReactNode;
}) {
  return (
    <section aria-label="Today" data-fresh={freshness} className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-2 flex items-center justify-between">
        <h2 className="num text-sm tracking-[0.2em] text-dim">TODAY</h2>
        {fetchedAt && (
          <span className="num text-[10px] text-dim">read {fetchedAt.toLocaleTimeString()}</span>
        )}
      </header>
      {children}
    </section>
  );
}
