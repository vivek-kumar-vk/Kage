import { REPLICA_SUMMARY, REPLICA_GATE } from "@/app/lib/replicaHoldings";
import { formatINR } from "@/app/lib/formatINR";
import { TelemetryCard, DeltaBadge } from "../f1";

export function ReplicaSummary() {
  const gain = REPLICA_SUMMARY.gainLoss;
  return (
    <TelemetryCard label="Portfolio" value={formatINR(REPLICA_SUMMARY.currentValue)} sub={`invested ${formatINR(REPLICA_SUMMARY.invested)}`}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <DeltaBadge value={formatINR(gain)} tone={gain >= 0 ? "ahead" : "alert"} />
      </div>
      <div style={{ marginTop: 8, fontFamily: "ui-monospace, monospace", fontSize: 11, color: "var(--liv-text-dim)" }}>
        {REPLICA_GATE.code}{REPLICA_GATE.text}
      </div>
    </TelemetryCard>
  );
}
