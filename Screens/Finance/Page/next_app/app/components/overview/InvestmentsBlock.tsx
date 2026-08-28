import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { formatINR } from "@/app/lib/formatINR";
import { TelemetryCard, StatDial } from "../f1";

export function InvestmentsBlock() {
  const { current } = BLUEPRINT_SEED.investments;
  return (
    <TelemetryCard label="Investments" value={formatINR(current)} sub="seed">
      <StatDial pct={68} value="68%" label="of target" size={132} />
    </TelemetryCard>
  );
}
