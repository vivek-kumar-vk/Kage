"use client";
import { Card } from "@/components/finance/Card";
import { useFinanceData } from "@/lib/api";
import type { NetWorthData } from "@/lib/types";

function inr(n: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const w = 100;
  const h = 32;
  const d = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((p - min) / range) * h;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 h-8 w-full" preserveAspectRatio="none">
      <path d={d} fill="none" stroke="#00ff87" strokeWidth="2" />
    </svg>
  );
}

export default function NetWorthCard() {
  const { data, isLoading, error } = useFinanceData<NetWorthData>("/overview/net-worth");

  return (
    <Card title="Net Worth" isLoading={isLoading} error={error}>
      {!data || !data.trend || data.trend.length === 0 ? (
        <p className="text-sm text-racing-silver">No data yet.</p>
      ) : (
        <>
          <p className="value-large">{inr(data.net_worth)}</p>
          <p className="text-xs text-racing-silver">
            Assets {inr(data.assets)} · Liabilities {inr(data.liabilities)}
          </p>
          <Sparkline points={data.trend.map((t) => t.net_worth)} />
        </>
      )}
    </Card>
  );
}
