import { BLUEPRINT_SEED } from "@/app/lib/blueprintSeed";
import { TelemetryCard, SegmentMeter } from "../f1";

export function BucketBlock() {
  const segments = BLUEPRINT_SEED.buckets.map((b) => ({ label: b.name, pct: b.fillPct }));
  return <TelemetryCard label="3-Bucket System"><SegmentMeter segments={segments} /></TelemetryCard>;
}
