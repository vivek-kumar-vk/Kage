"use client";

import { useSectors, useOverlap } from "./usePortfolio";
import { AskStrip } from "./AskStrip";

/** Tab 4 - fund overlap/concentration and the money-weighted sector map
    (arithmetic over live-fetched per-fund holdings, ADR-056: "no model
    was asked anything" - but both genuinely network-bound and slow on a
    cold cache, sometimes unreachable entirely). The two cards are
    fetched independently on purpose: a slow or down network for one
    must never hide the other's own honest loading/error state. The
    sector map's [UNVERIFIED] state is never hidden - the reference file
    behind it has not been checked by a person, and this UI says so
    exactly as loudly as the vanilla page does. */
export function PortfolioPanel() {
  const sectors = useSectors();
  const overlap = useOverlap();

  // The section's own freshness mirrors the sector card's state - an
  // honest signal of "this panel has rendered something", not a claim
  // that live network data arrived. The overlap card carries its own
  // separate data-fresh rather than gating on a fetch that can take
  // minutes or never return on a network-constrained host.
  const freshness = sectors.state === "fresh" ? "fresh" : sectors.state === "error" ? "unavailable" : "empty";

  return (
    <section aria-label="Portfolio Analysis" data-fresh={freshness} className="flex flex-col gap-4">
      <div
        aria-label="Fund overlap"
        data-fresh={overlap.state === "fresh" ? "fresh" : overlap.state === "error" ? "unavailable" : "empty"}
        className="rounded-lg border border-line bg-panel p-4"
      >
        <h2 className="num mb-2 text-sm tracking-[0.2em] text-dim">CONCENTRATION &amp; OVERLAP</h2>
        {overlap.state === "loading" && (
          <p className="text-xs text-dim">
            fetching each fund&apos;s published holdings live - this can take a while on a cold
            cache (12h cache after the first ask)
          </p>
        )}
        {overlap.state === "error" && (
          <p className="text-xs text-p5red">could not reach /api/finance/portfolio-analysis</p>
        )}
        {overlap.state === "fresh" && overlap.data && !overlap.data.has_data && (
          <p className="text-xs text-dim">{overlap.data.note}</p>
        )}
        {overlap.state === "fresh" && overlap.data?.has_data && (
          <>
            <p className="num mb-2 text-sm text-bone">
              {overlap.data.whole_portfolio?.companies_you_own} companies ·
              {" "}top 10 = {overlap.data.whole_portfolio?.top_ten_percent}%
            </p>
            <div className="flex flex-col gap-1">
              {overlap.data.pairs?.map((p) => (
                <div key={`${p.first_fund}-${p.second_fund}`} className="flex items-center justify-between gap-3 text-xs">
                  <span className="truncate text-bone">{p.first_fund} vs {p.second_fund}</span>
                  <span className="num text-dim">{p.overlap_percent}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="rounded-lg border border-line bg-panel p-4">
        <header className="mb-2 flex items-center justify-between gap-3">
          <h2 className="num text-sm tracking-[0.2em] text-dim">SECTOR MAP</h2>
          {!sectors.data?.verified_by_a_person && sectors.data?.has_data && (
            <span className="num rounded border border-p5red px-2 py-0.5 text-[9px] tracking-widest text-p5red">
              UNVERIFIED
            </span>
          )}
        </header>
        {sectors.state === "loading" && !sectors.data && <p className="text-xs text-dim">loading the sector map...</p>}
        {sectors.state === "error" && <p className="text-xs text-p5red">could not reach /api/finance/portfolio-analysis/sectors</p>}
        {sectors.data && !sectors.data.has_data && <p className="text-xs text-dim">{sectors.data.note || "no sector data yet"}</p>}
        {sectors.data?.has_data && (
          <>
            {sectors.data.unverified_warning && (
              <p className="mb-2 text-[10px] text-p5red">{sectors.data.unverified_warning}</p>
            )}
            <div className="flex flex-col gap-1">
              {sectors.data.sectors?.map((s) => (
                <div key={s.name} className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-bone">{s.name}</span>
                  <span className="num text-dim">{s.percent_of_portfolio}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <AskStrip
        endpoint="/api/finance/portfolio-analysis/ask"
        placeholder="Ask about overlap, concentration or sector spread..."
      />
    </section>
  );
}
