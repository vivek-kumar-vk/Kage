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

export default function OverviewPage() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <NetWorthCard />
      <CashflowCard />
      <PortfolioPulseCard />
      <EmergencyFundCard />
      <DebtStatusCard />
      <SurplusAllocationCard />
      <GoalsCard />
      <TopActionsCard />
      <DataHealthCard />
    </div>
  );
}
