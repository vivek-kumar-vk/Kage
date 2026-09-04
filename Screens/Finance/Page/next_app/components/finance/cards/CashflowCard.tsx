"use client";
import { useFinanceData } from "@/lib/api";
import { inrCompact, num } from "@/lib/format";
import { useOverviewScope } from "@/lib/useOverviewScope";
import HistoricalMarker from "@/components/finance/HistoricalMarker";
import type { CashflowData } from "@/lib/types";

const UP = "#3DDC97";
const DOWN = "#FF7A6B";

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div>
      <div className="footnote">{label}</div>
      <div className={`value-md mt-1 ${cls ?? ""}`}>{value}</div>
    </div>
  );
}

// Mirrored bars: income rises from the centre line, expenses fall from it.
// Both halves share one scale so a tall green bar really is bigger money.
function MirrorBars({ months }: { months: CashflowData["months"] }) {
  const peak = Math.max(1, ...months.map((m) => Math.max(m.income, m.expenses)));
  return (
    <div className="mt-4 flex h-[132px] items-center">
      {months.map((m) => (
        <div key={m.month} className="relative flex h-full flex-1 flex-col items-center">
          <div className="flex w-full flex-1 items-end justify-center">
            <div
              className="w-[46%] rounded-[5px]"
              style={{
                height: `${(m.income / peak) * 100}%`,
                background: `linear-gradient(180deg, ${UP}d9, ${UP}40)`,
              }}
              title={`Income ${inrCompact(m.income)}`}
            />
          </div>
          <div className="h-px w-full bg-white/[.14]" />
          <div className="flex w-full flex-1 justify-center">
            <div
              className="w-[46%] rounded-[5px]"
              style={{
                height: `${(m.expenses / peak) * 100}%`,
                background: `linear-gradient(180deg, ${DOWN}47, ${DOWN}cc)`,
              }}
              title={`Expenses ${inrCompact(m.expenses)}`}
            />
          </div>
          <div className="absolute -bottom-[18px] font-mono text-[9.5px] text-aurum-faint">
            {m.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function Legend({ swatch, children }: { swatch: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-[7px] text-[11px] text-aurum-muted">
      <span className="h-[9px] w-[9px] rounded-[3px]" style={{ background: swatch }} />
      {children}
    </div>
  );
}

export default function CashflowCard() {
  const scope = useOverviewScope();
  const { data, isLoading, error } = useFinanceData<CashflowData>(
    `/overview/cashflow${scope.query}`
  );
  const months = data?.months ?? [];

  // The headline follows the tag: sum the window actually charted, and only
  // fall back to the all-time totals when there is no month history yet.
  const windowed = months.length > 0;
  const income = windowed ? months.reduce((s, m) => s + m.income, 0) : data?.income ?? 0;
  const expenses = windowed ? months.reduce((s, m) => s + m.expenses, 0) : data?.expenses ?? 0;

  return (
    <section className="panel flex h-full min-h-[300px] flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">
            Cashflow
            <span className="tag dim">
              {windowed ? `last ${months.length} mo` : "all time"}
            </span>
          </div>
          {scope.isHistorical ? <HistoricalMarker label={scope.label} /> : null}
          <div className="mt-3.5 flex gap-[26px]">
            <Stat label="INCOME" value={`₹${num(income)}`} cls="pos" />
            <Stat label="EXPENSES" value={`₹${num(expenses)}`} cls="neg" />
            <Stat label="NET SURPLUS" value={`₹${num(income - expenses)}`} cls="goldc" />
          </div>

          {months.length > 0 ? (
            <MirrorBars months={months} />
          ) : (
            <p className="mt-6 text-xs text-aurum-faint">
              No dated transactions yet — import a statement to chart the months.
            </p>
          )}

          <div className="mt-auto flex flex-wrap gap-4 pt-7">
            <Legend swatch={UP}>Income</Legend>
            <Legend swatch={DOWN}>Expenses</Legend>
            <Legend swatch="#E4C07C">Surplus → auto-allocated</Legend>
          </div>
        </>
      )}
    </section>
  );
}
