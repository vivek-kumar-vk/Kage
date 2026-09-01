"use client";
import { useState } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData, useSubmit } from "@/lib/api";

interface DebtRow {
  id: number;
  lender: string;
  type: string | null;
  outstanding: number;
  interest_rate: number | null;
  emi: number | null;
  remaining_months: number | null;
}

interface Overview {
  total_outstanding: number;
  highest_interest: number;
  next_emi: { lender: string | null; emi: number; next_due: string | null };
  count: number;
}

interface PayoffPlan {
  method: string;
  steps: {
    id: number;
    lender: string;
    outstanding: number;
    interest_rate: number;
    emi: number;
    months_to_clear: number | null;
  }[];
  longest_months: number | null;
}

interface SimResult {
  baseline_months: number | null;
  new_months: number | null;
  months_saved: number;
  interest_saved: number;
  new_payoff_date: string;
}

function inr(n: number | null | undefined) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function OverviewCard() {
  const { data, isLoading, error } = useFinanceData<Overview>("/debt/overview");
  return (
    <Card title="Debt overview" isLoading={isLoading} error={error}>
      {!data || data.count === 0 ? (
        <p className="text-sm text-racing-silver">No debts recorded.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          <li className="flex justify-between">
            <span className="text-racing-silver">Total outstanding</span>
            <span className="value-negative font-mono">
              {inr(data.total_outstanding)}
            </span>
          </li>
          <li className="flex justify-between">
            <span className="text-racing-silver">Highest rate</span>
            <span className="font-mono">{data.highest_interest}%</span>
          </li>
          <li className="flex justify-between">
            <span className="text-racing-silver">Next EMI</span>
            <span className="font-mono">
              {inr(data.next_emi.emi)}
              {data.next_emi.next_due ? ` · ${data.next_emi.next_due}` : ""}
            </span>
          </li>
        </ul>
      )}
    </Card>
  );
}

function DebtTableCard() {
  const { data, isLoading, error } = useFinanceData<DebtRow[]>("/debt/table");
  return (
    <Card title="Debts" isLoading={isLoading} error={error}>
      {!data || data.length === 0 ? (
        <p className="text-sm text-racing-silver">Nothing here yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-racing-silver">
                <th className="py-1 pr-4">Lender</th>
                <th className="py-1 pr-4">Outstanding</th>
                <th className="py-1 pr-4">Rate</th>
                <th className="py-1 pr-4">EMI</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id} className="border-t border-carbon-light">
                  <td className="py-1 pr-4">{d.lender}</td>
                  <td className="py-1 pr-4 font-mono">{inr(d.outstanding)}</td>
                  <td className="py-1 pr-4 font-mono">{d.interest_rate ?? "—"}%</td>
                  <td className="py-1 pr-4 font-mono">{inr(d.emi)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function PayoffPlanCard() {
  const { data, isLoading, error } = useFinanceData<PayoffPlan>(
    "/debt/payoff-plan"
  );
  return (
    <Card title="Payoff plan (avalanche)" isLoading={isLoading} error={error}>
      {!data || data.steps.length === 0 ? (
        <p className="text-sm text-racing-silver">No plan — add a debt first.</p>
      ) : (
        <ol className="space-y-1 text-sm">
          {data.steps.map((s, i) => (
            <li key={s.id} className="flex justify-between">
              <span>
                {i + 1}. {s.lender}{" "}
                <span className="text-racing-silver">({s.interest_rate}%)</span>
              </span>
              <span className="font-mono">
                {s.months_to_clear === null
                  ? "EMI ≤ interest"
                  : `${s.months_to_clear} mo`}
              </span>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function SimulateCard() {
  const { submit, isSubmitting, error } = useSubmit<Record<string, number>, SimResult>(
    "/debt/simulate",
    "POST"
  );
  const [extra, setExtra] = useState(5000);
  const [result, setResult] = useState<SimResult | null>(null);

  async function run() {
    const r = await submit({ extra_payment: extra, salary_increase: 0, bonus: 0 });
    setResult(r);
  }

  return (
    <Card title="What if I pay extra?" error={error}>
      <div className="flex items-center gap-3">
        <label className="text-sm text-racing-silver" htmlFor="extra">
          Extra / month
        </label>
        <input
          id="extra"
          type="number"
          min={0}
          step={500}
          value={extra}
          onChange={(e) => setExtra(Number(e.target.value))}
          className="w-32 rounded bg-carbon-dark px-2 py-1 font-mono text-sm"
        />
        <button
          onClick={run}
          disabled={isSubmitting}
          className="rounded bg-racing-blue px-3 py-1 text-sm text-carbon-dark disabled:opacity-50"
        >
          {isSubmitting ? "…" : "Simulate"}
        </button>
      </div>
      {result && (
        <ul className="mt-3 space-y-1 text-sm">
          <li className="flex justify-between">
            <span className="text-racing-silver">Months saved</span>
            <span className="value-positive font-mono">{result.months_saved}</span>
          </li>
          <li className="flex justify-between">
            <span className="text-racing-silver">Interest saved</span>
            <span className="value-positive font-mono">
              {inr(result.interest_saved)}
            </span>
          </li>
          <li className="flex justify-between">
            <span className="text-racing-silver">New payoff date</span>
            <span className="font-mono">{result.new_payoff_date}</span>
          </li>
        </ul>
      )}
    </Card>
  );
}

function LearningCard() {
  const { data, isLoading, error } = useFinanceData<{
    action: string;
    reason: string;
    learn: string;
  }>("/debt/learning/avalanche");
  return (
    <Card title="Action · Reason · Learn" isLoading={isLoading} error={error}>
      {!data ? (
        <p className="text-sm text-racing-silver">—</p>
      ) : (
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-racing-yellow">Action</dt>
            <dd>{data.action}</dd>
          </div>
          <div>
            <dt className="text-racing-yellow">Reason</dt>
            <dd className="text-racing-silver">{data.reason}</dd>
          </div>
          <div>
            <dt className="text-racing-yellow">Learn</dt>
            <dd className="text-racing-silver">{data.learn}</dd>
          </div>
        </dl>
      )}
    </Card>
  );
}

export default function DebtPage() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <OverviewCard />
      <SimulateCard />
      <div className="xl:col-span-2">
        <DebtTableCard />
      </div>
      <PayoffPlanCard />
      <LearningCard />
    </div>
  );
}
