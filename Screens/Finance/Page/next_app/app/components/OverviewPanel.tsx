"use client";

import { TotalBalanceBlock } from "./overview/TotalBalanceBlock";
import { CashFlowBlock } from "./overview/CashFlowBlock";
import { InvestmentsBlock } from "./overview/InvestmentsBlock";
import { DebtBlock } from "./overview/DebtBlock";
import { EmergencyFundBlock } from "./overview/EmergencyFundBlock";
import { BucketBlock } from "./overview/BucketBlock";
import { GoalsList } from "./overview/GoalsList";

/** Tab 1 — Ferrari livery. Seed-data blocks, one visualization each
    (PLANNED_WORK.md P8 wires them live). The live-endpoint blocks
    (gates G1–G4, health score, surplus formula) are deferred to P8 —
    they have no seed equivalent. */
export function OverviewPanel() {
  return (
    <section aria-label="Overview" className="flex flex-col gap-6">
      <TotalBalanceBlock />
      <div className="grid gap-6 sm:grid-cols-2">
        <CashFlowBlock />
        <InvestmentsBlock />
        <DebtBlock />
        <EmergencyFundBlock />
      </div>
      <BucketBlock />
      <GoalsList />
    </section>
  );
}
