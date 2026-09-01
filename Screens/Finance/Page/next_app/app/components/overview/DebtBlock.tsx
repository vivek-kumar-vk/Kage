import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { formatINR } from "@/app/lib/formatINR";
import { TelemetryCard, SegmentMeter } from "../f1";

export function DebtBlock() {
  const { totalDebt } = BLUEPRINT_SEED;
  return (
    <TelemetryCard label="Total Debt" value={formatINR(totalDebt)} sub="seed">
      <SegmentMeter segments={[{ label: "Paid", pct: 32 }, { label: "Outstanding", pct: 68 }]} />
    </TelemetryCard>
  );
}
