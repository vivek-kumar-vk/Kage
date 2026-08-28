"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

interface Money {
  raw: number | null;
  text: string;
  signed: string;
  known: boolean;
}

export interface DebtPayload {
  education_loan: {
    outstanding: Money;
    rate_pct: number;
    emi: Money;
    payoff_now: string;
    months_saved: number;
    interest_saved: Money;
  };
  personal_debt: {
    remaining: Money;
    monthly: Money;
    months_left: number | null;
    clears: string;
  };
}

export interface LedgerRow {
  name: string;
  kind: string;
  monthly_amount: Money;
  value: Money;
}

export interface LiabilitiesPayload {
  has_data: boolean;
  net_worth: { value: Money };
  total_assets: Money;
  total_liabilities: Money;
  monthly_recurring_liabilities: Money;
  assets: LedgerRow[];
  liabilities: LedgerRow[];
}

/** GET /api/finance/debt and /api/finance/liabilities - the loan
    amortisation + personal-debt countdown, and the separate net-worth
    ledger. Two real endpoints, matching the Loans / Net Worth sub-tabs
    the vanilla Debt tab already carries. */
export function useDebt() {
  const [debt, setDebt] = useState<DebtPayload | null>(null);
  const [liabilities, setLiabilities] = useState<LiabilitiesPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    Promise.all([
      fetch("/api/finance/debt").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
      fetch("/api/finance/liabilities").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
    ])
      .then(([d, l]) => {
        setDebt(d as DebtPayload);
        setLiabilities(l as LiabilitiesPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { debt, liabilities, state, reload: load };
}
