"use client";

import { PulseCore } from "./PulseCore";

/** TELEMETRY tab — slimmed (P9 Phase 4). Overview now owns the cash-flow / goals / investments / debt / bucket panels; only the PulseCore hero stays here. Inherits the Ferrari livery from the shell. */
export function TelemetryPanel() {
  return (
    <section aria-label="Telemetry" className="flex flex-col gap-4">
      <PulseCore />
    </section>
  );
}
