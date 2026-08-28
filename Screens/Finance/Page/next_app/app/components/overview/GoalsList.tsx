import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { TelemetryCard, TimingRow } from "../f1";

export function GoalsList() {
  return (
    <TelemetryCard label="Goals \u2014 timing tower">
      {BLUEPRINT_SEED.goals.map((g, i) => (
        <TimingRow
          key={g.label}
          rank={String(i + 1).padStart(2, "0")}
          name={g.label}
          value={`${g.pct}%`}
          pct={g.pct}
          tone={g.pct >= 75 ? "best" : g.pct >= 40 ? "ahead" : "flat"}
        />
      ))}
    </TelemetryCard>
  );
}
