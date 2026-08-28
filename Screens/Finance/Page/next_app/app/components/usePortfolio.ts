"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

export interface OverlapPair {
  first_fund: string;
  second_fund: string;
  overlap_percent: number;
  in_plain_words: string;
}

export interface PortfolioAnalysisPayload {
  has_data: boolean;
  note?: string;
  whole_portfolio?: { companies_you_own: number; top_ten_percent: number };
  pairs?: OverlapPair[];
}

export interface SectorRow {
  name: string;
  percent_of_portfolio: number;
}

export interface SectorsPayload {
  has_data: boolean;
  note?: string;
  verified_by_a_person: boolean;
  unverified_warning?: string;
  sectors?: SectorRow[];
}

/** GET /api/finance/portfolio-analysis/sectors - the money-weighted
    sector map. Like /portfolio-analysis below, this calls
    fetch_fund_facts.holdings() per fund live (cached 12h after the
    first ask) to know each fund's underlying stocks before it can map
    sectors - so it is NOT local-only, and is kept as its own
    independent fetch state for the same reason: a slow network must
    never block the overlap card, or vice versa. Carries its own
    [UNVERIFIED] badge when the sector reference file has not been
    checked by a person - rendered exactly as the server states it. */
export function useSectors() {
  const [data, setData] = useState<SectorsPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/finance/portfolio-analysis/sectors")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setData(body as SectorsPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { data, state, reload: load };
}

/** GET /api/finance/portfolio-analysis - fund overlap and concentration
    (pure arithmetic over data fetched live per fund from each fund's
    published portfolio - ADR-056: "no model was asked anything"). This
    is the one Finance endpoint that can genuinely take a long time on a
    cold cache (fetch_fund_facts.holdings, 20s per fund, cached 12
    hours after) or fail outright with no network reachable - kept as
    its own independent fetch state so a slow or unreachable network
    never blocks the sector map above from showing. */
export function useOverlap() {
  const [data, setData] = useState<PortfolioAnalysisPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    fetch("/api/finance/portfolio-analysis")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then((body) => {
        setData(body as PortfolioAnalysisPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { data, state, reload: load };
}
