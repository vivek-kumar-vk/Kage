"use client";
import { useFinanceData } from "@/lib/api";
import { inrCompact, num, pct } from "@/lib/format";
import { useOverviewScope } from "@/lib/useOverviewScope";
import HistoricalMarker from "@/components/finance/HistoricalMarker";
import type { DebtStatusData } from "@/lib/types";

// Loans are returned largest-first, so the ramp reads big → small.
const LOAN_COLORS = ["#8B93FF", "#6BE1FF", "#F5B85C", "#FF7A6B"];
const HIGH_APR = 20; // above this a loan is an "act now" rupee — the only red

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div>
      <div className="footnote">{label}</div>
      <div className={`value-md mt-1 ${cls ?? ""}`}>{value}</div>
    </div>
  );
}

export default function DebtStatusCard() {
  const scope = useOverviewScope();
  const { data, isLoading, error } = useFinanceData<DebtStatusData>(
    `/overview/debt-status${scope.query}`
  );
  const loans = data?.loans ?? [];

  return (
    <section className="panel flex h-full min-h-[262px] flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">
            Debt Status
            <span className={`tag ${data.count > 0 ? "r" : "dim"}`}>
              {data.count} {data.count === 1 ? "loan" : "loans"}
            </span>
          </div>
          {scope.isHistorical ? <HistoricalMarker label={scope.label} /> : null}

          <div className="mt-3.5 flex gap-6">
            <Stat label="OUTSTANDING" value={`₹${num(data.total_debt)}`} />
            <Stat label="EMI / MO" value={`₹${num(data.total_emi)}`} />
            <Stat label="WTD RATE" value={pct(data.weighted_rate)} cls="neg" />
          </div>

          {loans.length === 0 ? (
            <p className="mt-6 text-xs text-aurum-muted">Debt-free — nothing outstanding.</p>
          ) : (
            <>
              <div className="track mt-[18px] h-2">
                {loans.map((loan, i) => (
                  <div
                    key={loan.id}
                    className="fill"
                    style={{
                      width: `${loan.share * 100}%`,
                      background: LOAN_COLORS[i % LOAN_COLORS.length],
                      borderRadius:
                        i === 0
                          ? "4px 0 0 4px"
                          : i === loans.length - 1
                            ? "0 4px 4px 0"
                            : "0",
                    }}
                    title={`${loan.name} ${inrCompact(loan.outstanding)}`}
                  />
                ))}
              </div>

              <div className="mt-3">
                {loans.map((loan, i) => {
                  const hot = (loan.rate ?? 0) > HIGH_APR;
                  return (
                    <div key={loan.id} className="aurum-row">
                      <span className="k flex items-center gap-2">
                        <span
                          className="h-[9px] w-[9px] shrink-0 rounded-[3px]"
                          style={{ background: LOAN_COLORS[i % LOAN_COLORS.length] }}
                        />
                        {loan.name}
                      </span>
                      <span className={`v ${hot ? "neg" : ""}`}>
                        {inrCompact(loan.outstanding)} ·{" "}
                        {loan.rate === null ? "rate —" : pct(loan.rate)}
                        {hot ? " ⚠" : ""}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
