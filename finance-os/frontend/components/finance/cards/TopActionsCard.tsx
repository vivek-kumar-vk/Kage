"use client";
import { Card } from "@/components/finance/Card";
import { useFinanceData } from "@/lib/api";

function inr(n: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

export default function TopActionsCard() {
  const { data, isLoading, error } = useFinanceData<Record<string, unknown>>(
    "/overview/top-actions"
  );

  return (
    <Card title="Top Actions" isLoading={isLoading} error={error}>
      {!data || Object.keys(data).length === 0 ? (
        <p className="text-sm text-racing-silver">No data yet.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {Object.entries(data)
            .filter(([, v]) => typeof v === "number" || typeof v === "string")
            .map(([k, v]) => (
              <li key={k} className="flex justify-between gap-4">
                <span className="text-racing-silver">{k.replace(/_/g, " ")}</span>
                <span className="font-mono">
                  {typeof v === "number" ? inr(v as number) : String(v)}
                </span>
              </li>
            ))}
        </ul>
      )}
    </Card>
  );
}
