"use client";

import { useOverview, type GateRow } from "./useOverview";

const GATE_LOOK: Record<GateRow["state"], string> = {
  pass: "border-jade text-jade",
  fail: "border-p5red text-p5red",
  partial: "border-amber text-amber",
  not_reached: "border-line text-dim",
};

const GATE_WORD: Record<GateRow["state"], string> = {
  pass: "PASS",
  fail: "FAIL",
  partial: "PARTIAL",
  not_reached: "NOT REACHED",
};

/** Tab 1 - the "am I OK" screen: surplus, the four gates (G1-G4), the
    emergency buffer, both countdowns, and the composite health score.
    Every figure is what server_for_finance.py's /command, /health-score
    and /money endpoints answer right now - nothing here softens a gate
    result or the score to make the screen look better (a standing
    project rule: "do not improve the score by softening a threshold"). */
export function OverviewPanel() {
  const { command, health, money, state } = useOverview();

  const freshness = state === "fresh" ? "fresh" : state === "error" ? "unavailable" : "empty";

  return (
    <section aria-label="Overview" data-fresh={freshness} className="flex flex-col gap-4">
      {state === "loading" && !command && <p className="text-sm text-dim">loading the overview...</p>}
      {state === "error" && !command && (
        <p className="text-sm text-p5red">could not reach /api/finance/command</p>
      )}

      {command && (
        <div className="rounded-lg border border-line bg-panel p-4">
          <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="num text-sm tracking-[0.2em] text-dim">SURPLUS</h2>
            <span className="num text-2xl font-bold text-bone">{command.surplus.text}</span>
          </header>
          <p className="num text-xs text-dim">
            deployable {command.deployable.text}
            {command.blocked_at && (
              <span className="text-p5red"> · blocked at {command.blocked_at}: {command.blocked_reason}</span>
            )}
          </p>

          <div className="mt-4 flex flex-col gap-2">
            {command.gates.map((g) => (
              <div key={g.gate} className={`gate-row flex items-center justify-between gap-3 rounded border-l-2 bg-void px-3 py-2 ${GATE_LOOK[g.state].split(" ")[0]}`}>
                <span className="num text-xs text-bone">{g.gate}</span>
                <span className="flex-1 text-xs text-dim">
                  {g.state === "not_reached" && g.preview
                    ? `not reached - would ${g.preview.passed ? "pass" : "fail"}: ${g.preview.reason}`
                    : g.reason}
                </span>
                <span className={`num shrink-0 rounded border px-2 py-0.5 text-[10px] tracking-widest ${GATE_LOOK[g.state]}`}>
                  {GATE_WORD[g.state]}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded border border-line bg-void p-3">
              <p className="num text-[10px] tracking-widest text-dim">EMERGENCY BUFFER</p>
              <p className="num text-sm text-bone">
                {command.buffer.fund.text}
                {command.buffer.next_tier_target.known && (
                  <span className="text-dim"> / {command.buffer.next_tier_target.text} ({command.buffer.next_tier})</span>
                )}
              </p>
              <p className="text-[10px] text-dim">
                {command.buffer.tier_reached ? `${command.buffer.tier_reached} reached` : "no tier reached yet"}
                {command.buffer.distance.known && ` · ${command.buffer.distance.text} to go`}
              </p>
            </div>
            <div className="rounded border border-line bg-void p-3">
              <p className="num text-[10px] tracking-widest text-dim">PERSONAL DEBT</p>
              <p className="num text-sm text-bone">{command.countdowns.personal_debt.clears}</p>
              <p className="text-[10px] text-dim">
                {command.countdowns.personal_debt.months_left != null
                  ? `${command.countdowns.personal_debt.months_left} months left`
                  : "—"}
                {command.countdowns.personal_debt.surplus_after.known &&
                  ` · surplus steps to ${command.countdowns.personal_debt.surplus_after.text} after`}
              </p>
            </div>
          </div>
        </div>
      )}

      {health && (
        <div className="rounded-lg border border-line bg-panel p-4">
          <header className="mb-3 flex items-center justify-between gap-3">
            <h2 className="num text-sm tracking-[0.2em] text-dim">HEALTH SCORE</h2>
            <span className="num text-lg font-bold text-bone">
              {health.score ?? "—"}/100 <span className="text-dim">({health.grade ?? "—"})</span>
            </span>
          </header>
          <div className="flex flex-col gap-2">
            {health.categories.map((c) => (
              <div key={c.name} className="flex items-center justify-between gap-3 text-xs">
                <span className="text-bone">{c.name}</span>
                <span className="num text-dim">
                  {c.scored ? `${c.pct}%` : `not measured${c.could_not_measure ? ` - ${c.could_not_measure}` : ""}`}
                </span>
              </div>
            ))}
          </div>
          {health.weakest && (
            <p className="mt-3 text-[10px] text-dim">weakest category: {health.weakest}</p>
          )}
        </div>
      )}

      {money && (
        <div className="rounded-lg border border-line bg-panel p-4">
          <h2 className="num mb-2 text-sm tracking-[0.2em] text-dim">THE SURPLUS FORMULA</h2>
          <table className="num w-full text-xs">
            <tbody>
              {money.lines.map((l) => (
                <tr key={l.label} className="border-b border-line/40">
                  <td className="py-1 text-dim">{l.label}</td>
                  <td className="py-1 text-right text-bone">{l.amount.text}</td>
                </tr>
              ))}
              <tr>
                <td className="pt-2 text-dim">before Slice refill</td>
                <td className="pt-2 text-right text-bone">{money.before_slice_refill.text}</td>
              </tr>
              <tr>
                <td className="pt-1 font-bold text-bone">surplus</td>
                <td className="pt-1 text-right font-bold text-bone">{money.surplus.text}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
