import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { formatINR } from "@/app/lib/formatINR";
import { TelemetryCard, SegmentMeter } from "../f1";

export function CashFlowBlock() {
  const { income, expenses } = BLUEPRINT_SEED.cashFlow;
  const surplus = income - expenses;
  const segments = [
    { label: "Income", pct: 100 },
    { label: "Expenses", pct: Math.round((expenses / income) * 100) },
    { label: "Surplus", pct: Math.round((surplus / income) * 100) }
  ];

  return (
    <TelemetryCard label="Cash Flow" value={formatINR(surplus)} sub={`income ${formatINR(income)} \u00b7 expenses ${formatINR(expenses)}`}>
      <SegmentMeter segments={segments} />
    </TelemetryCard>
  );
}
