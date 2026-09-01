"use client";

import { ReplicaSummary } from "./investments/ReplicaSummary";
import { ReplicaTable } from "./investments/ReplicaTable";

/** Tab 2 — Red Bull livery. An exact re-theme of the 2026-08-22 holdings
    screenshot: a summary header + the holdings table. Data is
    app/lib/replicaHoldings.ts (placeholder values, owner swaps real ones
    in). Editable fields + analysis/save/delete buttons render as
    non-functional visual placeholders. */
export function InvestmentsPanel() {
  return (
    <section aria-label="Investments" className="flex flex-col gap-6">
      <ReplicaSummary />
      <ReplicaTable />
    </section>
  );
}
