"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

interface Money {
  raw: number | null;
  text: string;
  signed: string;
  known: boolean;
}

export interface SnapshotHolding {
  scheme_name: string;
  category: string;
  invested: Money;
  current: Money;
  pl_abs: Money;
}

export interface InvestmentsPayload {
  has_snapshot: boolean;
  snapshot_note: string | null;
  snapshot_total_invested: Money;
  snapshot_total_current: Money;
  snapshot_total_pl: Money;
  snapshot_holdings: SnapshotHolding[];
  has_logged_data: boolean;
  logged_note: string | null;
}

export interface NavRow {
  scheme_name: string;
  nav: number | null;
  nav_date: string | null;
  state: "fresh" | "stale" | string;
}

export interface NavLedgerPayload {
  has_data: boolean;
  rows: NavRow[];
}

export interface XirrRow {
  name: string;
  xirr_pct: number | null;
}

export interface XirrPayload {
  has_data: boolean;
  holdings: XirrRow[];
}

/** GET /api/finance/investments, /investments/nav-ledger and
    /investments/xirr - the two real holdings sources (snapshot ledger,
    transaction log), the NAV ledger with its own honest fresh/stale
    badge per row, and true per-holding annualised return. Three real
    endpoints, kept separate the same way the server keeps them separate. */
export function useInvestments() {
  const [investments, setInvestments] = useState<InvestmentsPayload | null>(null);
  const [navLedger, setNavLedger] = useState<NavLedgerPayload | null>(null);
  const [xirr, setXirr] = useState<XirrPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    Promise.all([
      fetch("/api/finance/investments").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
      fetch("/api/finance/investments/nav-ledger").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
      fetch("/api/finance/investments/xirr").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
    ])
      .then(([i, n, x]) => {
        setInvestments(i as InvestmentsPayload);
        setNavLedger(n as NavLedgerPayload);
        setXirr(x as XirrPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { investments, navLedger, xirr, state, reload: load };
}
