import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { formatINR } from "@/app/lib/formatINR";
import { TelemetryCard, SegmentMeter } from "../f1";

export function EmergencyFundBlock() {
  const ef = BLUEPRINT_SEED.emergencyFund;
  const held = ef.tiers.reduce((a, t) => a + t.amount, 0);
  const segments = ef.tiers.map((t) => ({ label: t.label, pct: Math.round((t.amount / ef.target) * 100) }));
  return <TelemetryCard label="Emergency Fund" value={formatINR(held)} sub={`target ${formatINR(ef.target)}`}><SegmentMeter segments={segments} /></TelemetryCard>;
}
