"use client";
import { useFinanceData } from "@/lib/api";
import { useOverviewScope } from "@/lib/useOverviewScope";
import HistoricalMarker from "@/components/finance/HistoricalMarker";
import type { DataHealthData, ObservabilitySummary } from "@/lib/types";

const R = 36;
const C = 2 * Math.PI * R; // 226.2

function scoreColor(score: number): string {
  if (score >= 80) return "#3DDC97";
  if (score >= 50) return "#F5B85C";
  return "#FF7A6B";
}

// missing_info is a comma-joined list and can run to a dozen keys — the
// footnote names the first and counts the rest rather than wrapping forever.
function missingSummary(raw: string | null): string {
  const items = (raw ?? "")
    .split(",")
    .map((s) => s.trim().replace(/_/g, " "))
    .filter(Boolean);
  if (items.length === 0) return "";
  const rest = items.length - 1;
  return ` · ${items[0]}${rest > 0 ? ` +${rest} MORE` : ""}`.toUpperCase();
}

function Freshness({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="aurum-row py-1">
      <span className="k text-[11px]">{label}</span>
      <span className={`v text-[11px] ${value ? "" : "fainttx"}`}>{value ?? "never"}</span>
    </div>
  );
}

// Rendered inside the shared panel in app/finance/page.tsx — no .panel here.
export default function DataHealthCard() {
  const scope = useOverviewScope();
  const { data, isLoading, error } = useFinanceData<DataHealthData>(
    `/overview/data-health${scope.query}`
  );
  const score = data?.score ?? null;
  const ring = score === null ? 0 : (Math.min(Math.max(score, 0), 100) / 100) * C;
  // PLAN item 7: this screen's request/error observability, folded into the
  // existing Data Health block rather than a 10th card — restarts the
  // backend clears the window, which is honest, not a bug.
  const { data: obs } = useFinanceData<ObservabilitySummary>("/observability/summary");

  return (
    <div className="flex h-full flex-col">
      {isLoading ? (
        <p className="footnote">LOADING…</p>
      ) : error ? (
        <p className="text-xs text-aurum-coral">Failed to load: {error.message}</p>
      ) : !data ? null : (
        <>
          <div className="plabel">Data Health</div>
          {scope.isHistorical ? <HistoricalMarker label={scope.label} /> : null}

          <div className="mt-3.5 flex items-center gap-3.5">
            <svg width="92" height="92" viewBox="0 0 92 92" className="shrink-0">
              <circle
                cx="46"
                cy="46"
                r={R}
                fill="none"
                stroke="rgba(255,255,255,.07)"
                strokeWidth="8"
              />
              {score !== null && (
                <circle
                  cx="46"
                  cy="46"
                  r={R}
                  fill="none"
                  stroke={scoreColor(score)}
                  strokeWidth="8"
                  strokeDasharray={`${ring.toFixed(1)} ${C.toFixed(1)}`}
                  strokeLinecap="round"
                  transform="rotate(-90 46 46)"
                />
              )}
              <text
                x="46"
                y="52"
                textAnchor="middle"
                className="font-serif"
                fontSize="21"
                fill="#ECEAE2"
              >
                {score ?? "—"}
              </text>
            </svg>

            <div className="min-w-0 flex-1">
              <div className="footnote mb-2">FRESHNESS</div>
              <Freshness label="CAS" value={data.freshness.cas} />
              <Freshness label="Prices" value={data.freshness.prices} />
              <Freshness label="SMS" value={data.freshness.sms} />
            </div>
          </div>

          <div className="footnote mt-2.5">
            {data.unmatched_transactions > 0 ? (
              <span className="neg">{data.unmatched_transactions} UNMATCHED TXNS</span>
            ) : (
              <span className="pos">ALL TXNS MATCHED</span>
            )}
            {missingSummary(data.missing_info)}
          </div>

          <div className="footnote mt-1">
            {obs === null || obs.window === 0 ? (
              "SYSTEM · NO REQUESTS YET"
            ) : (
              <>
                SYSTEM ·{" "}
                <span className={obs.error_rate_pct ? "neg" : ""}>
                  {obs.error_rate_pct ?? 0}% ERR
                </span>{" "}
                · {obs.avg_duration_ms ?? "—"}MS AVG · {obs.window} REQ
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
