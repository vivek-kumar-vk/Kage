"use client";
import { useMemo } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData } from "@/lib/api";
import TransactionForm from "@/components/finance/forms/TransactionForm";

interface Txn {
  id: number;
  date: string;
  description: string | null;
  amount: number;
  category: string | null;
  type: string | null;
}

function inr(n: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function TransactionsCard() {
  const { data, isLoading, error, refetch } = useFinanceData<Txn[]>(
    "/tracker/transactions"
  );
  return (
    <Card title="Transactions" isLoading={isLoading} error={error}>
      <div className="mb-4">
        <TransactionForm onSaved={refetch} />
      </div>
      {!data || data.length === 0 ? (
        <p className="text-sm text-racing-silver">No transactions yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-racing-silver">
                <th className="py-1 pr-4">Date</th>
                <th className="py-1 pr-4">Description</th>
                <th className="py-1 pr-4">Category</th>
                <th className="py-1 pr-4 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {data.map((t) => (
                <tr key={t.id} className="border-t border-carbon-light">
                  <td className="py-1 pr-4 font-mono">{t.date}</td>
                  <td className="py-1 pr-4">{t.description ?? "—"}</td>
                  <td className="py-1 pr-4 text-racing-silver">
                    {t.category ?? "—"}
                  </td>
                  <td
                    className={`py-1 pr-4 text-right font-mono ${
                      t.amount < 0 ? "value-negative" : "value-positive"
                    }`}
                  >
                    {inr(t.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function CategoryBreakdownCard() {
  const { data, isLoading, error } = useFinanceData<{
    state: string;
    categories: { category: string; spent: number; count: number }[];
  }>("/tracker/categories");
  const max = useMemo(
    () => Math.max(1, ...(data?.categories ?? []).map((c) => c.spent)),
    [data]
  );
  return (
    <Card title="Spend by category" isLoading={isLoading} error={error}>
      {!data || data.state === "pending" || data.categories.length === 0 ? (
        <p className="text-sm text-racing-silver">No spending recorded yet.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {data.categories
            .filter((c) => c.spent > 0)
            .map((c) => (
              <li key={c.category}>
                <div className="flex justify-between">
                  <span className="text-racing-silver">{c.category}</span>
                  <span className="font-mono">{inr(c.spent)}</span>
                </div>
                <div className="mt-0.5 h-1 rounded bg-carbon-light">
                  <div
                    className="h-1 rounded bg-racing-blue"
                    style={{ width: `${(c.spent / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
        </ul>
      )}
    </Card>
  );
}

function TrendCard() {
  const { data, isLoading, error } = useFinanceData<{
    state: string;
    series: { month: string; income: number; expense: number }[];
  }>("/tracker/trends");
  const series = data?.series ?? [];
  const max = Math.max(1, ...series.flatMap((s) => [s.income, s.expense]));
  return (
    <Card title="Monthly trend" isLoading={isLoading} error={error}>
      {!data || data.state === "pending" || series.length === 0 ? (
        <p className="text-sm text-racing-silver">Not enough history yet.</p>
      ) : (
        <div className="flex items-end gap-2">
          {series.map((s) => (
            <div key={s.month} className="flex flex-1 flex-col items-center gap-1">
              <div className="flex h-24 items-end gap-0.5">
                <div
                  className="w-2 rounded-t bg-racing-green"
                  style={{ height: `${(s.income / max) * 100}%` }}
                />
                <div
                  className="w-2 rounded-t bg-racing-red"
                  style={{ height: `${(s.expense / max) * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-racing-silver">{s.month}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function RecurringCard() {
  const { data, isLoading, error } = useFinanceData<{
    recurring: { payee: string; occurrences: number; avg_amount: number }[];
  }>("/tracker/recurring");
  return (
    <Card title="Recurring" isLoading={isLoading} error={error}>
      {!data || data.recurring.length === 0 ? (
        <p className="text-sm text-racing-silver">Nothing detected yet.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {data.recurring.map((r) => (
            <li key={r.payee} className="flex justify-between">
              <span>{r.payee}</span>
              <span className="font-mono text-racing-silver">
                ×{r.occurrences} · {inr(r.avg_amount)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function TrackerPage() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div className="xl:col-span-2">
        <TransactionsCard />
      </div>
      <CategoryBreakdownCard />
      <TrendCard />
      <RecurringCard />
    </div>
  );
}
