"use client";
import NetWorthCard from "@/components/finance/cards/NetWorthCard";
import CashflowCard from "@/components/finance/cards/CashflowCard";
import PortfolioPulseCard from "@/components/finance/cards/PortfolioPulseCard";
import EmergencyFundCard from "@/components/finance/cards/EmergencyFundCard";
import DebtStatusCard from "@/components/finance/cards/DebtStatusCard";
import SurplusAllocationCard from "@/components/finance/cards/SurplusAllocationCard";
import GoalsCard from "@/components/finance/cards/GoalsCard";
import TopActionsCard from "@/components/finance/cards/TopActionsCard";
import DataHealthCard from "@/components/finance/cards/DataHealthCard";

// 12-col mockup grid: 8+4 / 5+4+3 / 4+4+4. TopActions and DataHealth share
// one panel, split 1.15/0.85 like the design.
export default function OverviewPage() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <div className="lg:col-span-8">
        <NetWorthCard />
      </div>
      <div className="lg:col-span-4">
        <PortfolioPulseCard />
      </div>
      <div className="lg:col-span-5">
        <CashflowCard />
      </div>
      <div className="lg:col-span-4">
        <SurplusAllocationCard />
      </div>
      <div className="lg:col-span-3">
        <EmergencyFundCard />
      </div>
      <div className="lg:col-span-4">
        <DebtStatusCard />
      </div>
      <div className="lg:col-span-4">
        <GoalsCard />
      </div>
      <div className="panel lg:col-span-4 flex flex-col">
        <div className="flex min-h-0 flex-1 gap-4">
          <div className="min-w-0 flex-[1.15]">
            <TopActionsCard />
          </div>
          <div className="w-px shrink-0 bg-white/[.07]" />
          <div className="min-w-0 flex-[.85]">
            <DataHealthCard />
          </div>
        </div>
      </div>
    </div>
  );
}
