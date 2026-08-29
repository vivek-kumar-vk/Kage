"use client";
import { useMemo, useState } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData, useSubmit } from "@/lib/api";
import {
  RollingReturnsLine,
  DrawdownArea,
  AllocationDonut,
} from "@/components/finance/charts/InvestmentCharts";

interface Holding {
  id: number;
  symbol: string;
  name: string | null;
  type: string | null;
  units: number;
  avg_cost: number;
  value: number | null;
  weight: number;
  priced: boolean;
  lots_count: number;
}

function inr(n: number | null | undefined) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function HoldingsTable() {
  const { data, isLoading, error, refetch } = useFinanceData<Holding[]>(
    "/investments/holdings"
  );
  const { submit } = useSubmit("/investments/holdings", "POST");
  const [busy, setBusy] = useState<number | null>(null);

  async function archive(id: number) {
    setBusy(id);
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE ?? ""}/api/finance/investments/holdings/${id}/archive`,
        { method: "POST" }
      );
      refetch();
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card title="Holdings" isLoading={isLoading} error={error}>
      {!data || data.length === 0 ? (
        <p className="text-sm text-racing-silver">No holdings yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-racing-silver">
                <th className="py-1 pr-4">Asset</th>
                <th className="py-1 pr-4">Units</th>
                <th className="py-1 pr-4">Value</th>
                <th className="py-1 pr-4">Weight</th>
                <th className="py-1 pr-4" />
              </tr>
            </thead>
            <tbody>
              {data.map((h) => (
                <tr key={h.id} className="border-t border-carbon-light">
                  <td className="py-1 pr-4">
                    {h.symbol}
                    {!h.priced && (
                      <span className="ml-1 text-xs text-racing-yellow">
                        unpriced
                      </span>
                    )}
                  </td>
                  <td className="py-1 pr-4 font-mono">{h.units}</td>
                  <td className="py-1 pr-4 font-mono">{inr(h.value)}</td>
                  <td className="py-1 pr-4 font-mono">
                    {Math.round(h.weight * 100)}%
                  </td>
                  <td className="py-1 pr-4">
                    <button
                      className="text-xs text-racing-blue disabled:opacity-50"
                      disabled={busy === h.id}
                      onClick={() => archive(h.id)}
                    >
                      Archive
                    </button>
                    {h.lots_count === 0 && (
                      <button
                        className="ml-2 text-xs text-racing-red"
                        onClick={() =>
                          submit({ _method: "DELETE", id: h.id }).then(refetch)
                        }
                      >
                        Delete
                      </button>
                    )}
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

function RollingReturnsCard() {
  const { data, isLoading, error } = useFinanceData<{
    state: string;
    series: { date: string; return: number }[];
  }>("/investments/visuals/rolling-returns");

  const points = useMemo(
    () => (data?.series ?? []).map((p) => p.return),
    [data]
  );

  return (
    <Card title="Rolling returns (30d)" isLoading={isLoading} error={error}>
      {!data || data.state === "pending" ? (
        <p className="text-sm text-racing-silver">
          Backfill pending — price history is still loading.
        </p>
      ) : data.state === "partial" || points.length === 0 ? (
        <p className="text-sm text-racing-silver">
          Partial history — not enough data for a full window yet.
        </p>
      ) : (
        <RollingReturnsLine points={points} />
      )}
    </Card>
  );
}

function DrawdownCard() {
  const { data, isLoading, error } = useFinanceData<{
    state: string;
    series: { date: string; drawdown: number }[];
    max_drawdown?: number;
  }>("/investments/visuals/drawdown");

  const points = useMemo(
    () => (data?.series ?? []).map((p) => p.drawdown),
    [data]
  );

  return (
    <Card title="Drawdown" isLoading={isLoading} error={error}>
      {!data || data.state === "pending" ? (
        <p className="text-sm text-racing-silver">
          Backfill pending — price history is still loading.
        </p>
      ) : points.length === 0 ? (
        <p className="text-sm text-racing-silver">Partial history.</p>
      ) : (
        <>
          <p className="value-large">
            {Math.round((data.max_drawdown ?? 0) * 100)}%
          </p>
          <DrawdownArea points={points} />
        </>
      )}
    </Card>
  );
}

function AllocationCard() {
  const { data, isLoading, error } = useFinanceData<{
    state: string;
    allocation: { bucket: string; value: number; weight: number }[];
  }>("/investments/visuals/asset-allocation");

  return (
    <Card title="Asset allocation" isLoading={isLoading} error={error}>
      {!data || data.state === "pending" || data.allocation.length === 0 ? (
        <p className="text-sm text-racing-silver">No priced holdings yet.</p>
      ) : (
        <AllocationDonut
          slices={data.allocation.map((a) => ({
            label: a.bucket,
            weight: a.weight,
          }))}
        />
      )}
    </Card>
  );
}

export default function InvestmentsPage() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div className="xl:col-span-2">
        <HoldingsTable />
      </div>
      <RollingReturnsCard />
      <DrawdownCard />
      <AllocationCard />
    </div>
  );
}
