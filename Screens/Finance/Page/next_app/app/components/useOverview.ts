"use client";

import { useCallback, useEffect, useState } from "react";

export type FetchState = "loading" | "fresh" | "error";

interface Money {
  raw: number | null;
  text: string;
  signed: string;
  known: boolean;
}

export interface GateRow {
  gate: string;
  state: "pass" | "fail" | "partial" | "not_reached";
  reason: string;
  preview?: { passed: boolean; reason: string };
}

export interface CommandPayload {
  surplus: Money;
  deployable: Money;
  blocked_at: string | null;
  blocked_reason: string | null;
  gates: GateRow[];
  buffer: {
    fund: Money;
    tier_reached: string | null;
    next_tier: string | null;
    distance: Money;
    next_tier_target: Money;
  };
  countdowns: {
    personal_debt: { clears: string; months_left: number | null; surplus_before: Money; surplus_after: Money };
    education_loan: { clears: string; months_left: number | null; interest_remaining: Money };
  };
  portfolio_total: Money;
}

export interface HealthCategory {
  name: string;
  weight: number;
  scored: boolean;
  pct: number | null;
  measured: string | null;
  could_not_measure: string | null;
}

export interface HealthPayload {
  score: number | null;
  grade: string | null;
  signal: string | null;
  points_possible: number;
  points_total: number;
  coverage_pct: number | null;
  weakest: string | null;
  categories: HealthCategory[];
}

export interface MoneyLine {
  label: string;
  amount: Money;
}

export interface MoneyPayload {
  lines: MoneyLine[];
  surplus: Money;
  emergency_contribution: Money;
  deployable: Money;
  before_slice_refill: Money;
}

/** GET /api/finance/command, /health-score and /money - the "am I OK"
    screen, the composite score computed from the same figures, and the
    surplus formula's own line-by-line accounting. Three real endpoints,
    never merged server-side (the project's own rule for these three),
    so this hook keeps them as three answers with three fetch states. */
export function useOverview() {
  const [command, setCommand] = useState<CommandPayload | null>(null);
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [money, setMoney] = useState<MoneyPayload | null>(null);
  const [state, setState] = useState<FetchState>("loading");

  const load = useCallback(() => {
    setState((s) => (s === "fresh" ? s : "loading"));
    Promise.all([
      fetch("/api/finance/command").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
      fetch("/api/finance/health-score").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
      fetch("/api/finance/money").then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }),
    ])
      .then(([c, h, m]) => {
        setCommand(c as CommandPayload);
        setHealth(h as HealthPayload);
        setMoney(m as MoneyPayload);
        setState("fresh");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { command, health, money, state, reload: load };
}
