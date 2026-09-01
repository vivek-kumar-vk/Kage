import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { formatINR } from "@/app/lib/formatINR";
import { TelemetryCard, Sparkline, DeltaBadge } from "../f1";

export function TotalBalanceBlock() {
  const { totalBalance, investments } = BLUEPRINT_SEED;
  return (
    <TelemetryCard label="Total Balance" value={formatINR(totalBalance)} sub="seed \u00b7 wire live (P8)">
      <div style={{ marginBottom: 8 }}>
        <DeltaBadge value="+4.2%" tone="ahead" />
      </div>
      <Sparkline series={[...investments.series]} height={64} />
    </TelemetryCard>
  );
}
