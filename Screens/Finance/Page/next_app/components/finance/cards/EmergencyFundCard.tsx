"use client";
import { useFinanceData } from "@/lib/api";
import { inrCompact, monthLabel, num, pctFromFraction } from "@/lib/format";
import { useOverviewScope } from "@/lib/useOverviewScope";
import HistoricalMarker from "@/components/finance/HistoricalMarker";
import type { EmergencyFundData } from "@/lib/types";

const R = 56;
const C = 2 * Math.PI * R; // 351.9

export default function EmergencyFundCard() {
  const scope = useOverviewScope();
  const { data, isLoading, error } = useFinanceData<EmergencyFundData>(
    `/overview/emergency-fund${scope.query}`
  );
  const progress = Math.min(Math.max(data?.progress ?? 0, 0), 1);

  return (
    <section className="panel flex h-full min-h-[300px] flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">Emergency Fund</div>
          {scope.isHistorical ? <HistoricalMarker label={scope.label} /> : null}

          <div className="mt-4 flex items-center gap-5">
            <svg width="140" height="140" viewBox="0 0 140 140" className="shrink-0">
              <defs>
                <linearGradient id="au-emg" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#F5DCA4" />
                  <stop offset="1" stopColor="#E4C07C" />
                </linearGradient>
              </defs>
              <circle
                cx="70"
                cy="70"
                r={R}
                fill="none"
                stroke="rgba(255,255,255,.06)"
                strokeWidth="11"
              />
              <circle
                cx="70"
                cy="70"
                r={R}
                fill="none"
                stroke="url(#au-emg)"
                strokeWidth="11"
                strokeDasharray={`${(progress * C).toFixed(1)} ${C.toFixed(1)}`}
                strokeLinecap="round"
                transform="rotate(-90 70 70)"
              />
              <text
                x="70"
                y="66"
                textAnchor="middle"
                className="font-serif"
                fontSize="30"
                fill="#F5DCA4"
              >
                {pctFromFraction(progress)}
              </text>
              <text
                x="70"
                y="88"
                textAnchor="middle"
                className="font-mono"
                fontSize="9"
                fill="#9A9DAA"
                letterSpacing="1.5"
              >
                OF TARGET
              </text>
            </svg>

            <div className="min-w-0 flex-1">
              <div className="aurum-row">
                <span className="k">Balance</span>
                <span className="v goldc">{inrCompact(data.balance)}</span>
              </div>
              <div className="aurum-row">
                <span className="k">Target</span>
                <span className="v">{inrCompact(data.target)}</span>
              </div>
              <div className="aurum-row">
                <span className="k">Months covered</span>
                <span className="v">{num(data.months_covered, 1)} / 6</span>
              </div>
            </div>
          </div>

          <div className="track mt-[18px]">
            <div
              className="fill"
              style={{
                width: `${progress * 100}%`,
                background: "linear-gradient(90deg,#E4C07C,#F5DCA4)",
              }}
            />
          </div>

          <div className="footnote mt-2.5">
            {progress >= 1
              ? "FULLY FUNDED · 6-MONTH TARGET MET"
              : data.eta_date
                ? `ON PACE · TARGET REACHED BY ${monthLabel(data.eta_date)}`
                : `NO EARMARK YET · ${inrCompact(data.target - data.balance)} SHORT`}
          </div>
        </>
      )}
    </section>
  );
}
