"use client";
import { useFinanceData } from "@/lib/api";
import { inr, inrCompact } from "@/lib/format";
import type { SurplusAllocationData } from "@/lib/types";

const R = 66;
const C = 2 * Math.PI * R; // 414.7

// Emergency / Investments / Goals, in the order the sweep rule pays them.
const SLICE_COLORS = ["#E4C07C", "#8B93FF", "#6BE1FF"];

export default function SurplusAllocationCard() {
  const { data, isLoading, error } = useFinanceData<SurplusAllocationData>(
    "/overview/surplus-allocation"
  );

  const slices = (data?.allocation ?? []).map((a, i) => ({
    ...a,
    color: SLICE_COLORS[i % SLICE_COLORS.length] as string,
  }));
  const total = slices.reduce((s, a) => s + a.amount, 0);

  let offset = 0;
  const arcs = slices.map((s) => {
    const len = total > 0 ? (s.amount / total) * C : 0;
    const arc = { ...s, len, offset };
    offset -= len;
    return arc;
  });

  return (
    <section className="panel flex h-full min-h-[300px] flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">
            Surplus Allocation <span className="tag dim">this month</span>
          </div>

          <div className="mt-5 flex items-center gap-5">
            <svg width="170" height="170" viewBox="0 0 170 170" className="shrink-0">
              <circle
                cx="85"
                cy="85"
                r={R}
                fill="none"
                stroke="rgba(255,255,255,.06)"
                strokeWidth="16"
              />
              {arcs.map((a) => (
                <circle
                  key={a.category}
                  cx="85"
                  cy="85"
                  r={R}
                  fill="none"
                  stroke={a.color}
                  strokeWidth="16"
                  strokeDasharray={`${a.len.toFixed(1)} ${C.toFixed(1)}`}
                  strokeDashoffset={a.offset.toFixed(1)}
                  strokeLinecap="round"
                  transform="rotate(-90 85 85)"
                />
              ))}
              <text
                x="85"
                y="78"
                textAnchor="middle"
                className="font-serif"
                fontSize="26"
                fill="#ECEAE2"
              >
                {inrCompact(data.surplus)}
              </text>
              <text
                x="85"
                y="100"
                textAnchor="middle"
                className="font-mono"
                fontSize="9"
                fill="#9A9DAA"
                letterSpacing="2"
              >
                SURPLUS
              </text>
            </svg>

            <div className="min-w-0 flex-1">
              {slices.length > 0 ? (
                slices.map((s) => (
                  <div key={s.category} className="aurum-row">
                    <span className="k flex items-center gap-2">
                      <span
                        className="h-[9px] w-[9px] shrink-0 rounded-[3px]"
                        style={{ background: s.color }}
                      />
                      {s.category}
                    </span>
                    <span className="v">{inr(s.amount)}</span>
                  </div>
                ))
              ) : (
                <>
                  <p className="text-xs leading-relaxed text-aurum-muted">
                    Nothing to sweep — expenses and EMI take the whole month&apos;s net.
                  </p>
                  <div className="aurum-row mt-2">
                    <span className="k">Monthly net</span>
                    <span className="v">{inr(data.monthly_net)}</span>
                  </div>
                  <div className="aurum-row">
                    <span className="k">Expenses + EMI</span>
                    <span className="v neg">
                      {inr(data.monthly_expenses + data.monthly_emi)}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="footnote mt-auto pt-4">
            AUTO-SWEEP RULE: {data.rule.emergency} / {data.rule.investments} /{" "}
            {data.rule.goals} SPLIT · ADJUST IN SETTINGS
          </div>
        </>
      )}
    </section>
  );
}
