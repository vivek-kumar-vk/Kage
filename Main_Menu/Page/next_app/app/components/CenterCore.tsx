"use client";

import { useEffect, useState } from "react";
import { HeaderNav } from "./HeaderNav";
import { AgentRing } from "./AgentRing";
import { CenterParticles } from "./CenterParticles";
import { AgentFilesGraph } from "./AgentFilesGraph";
import type { AgentEntry } from "./useAgentFleetActivity";
import type { TraceRow } from "./useLiveEvents";

/** Real sizing at each width, never a CSS transform on a fixed-size box
    (a transform still leaves the original box's footprint in normal
    flow, which is exactly what causes a narrow phone to scroll
    sideways - the one thing C9/ADR-060 forbids). Checked against the
    same four widths every INKY page uses, plus the landscape-short case
    a width check alone would miss. */
function useRingSize() {
  const [size, setSize] = useState({ box: 480, radius: 190, particles: 220 });

  useEffect(() => {
    function recompute() {
      const w = window.innerWidth;
      const shortLandscape = window.innerHeight <= 560 && w > window.innerHeight;
      if (shortLandscape) {
        setSize({ box: 220, radius: 78, particles: 110 });
      } else if (w <= 420) {
        setSize({ box: 220, radius: 80, particles: 110 });
      } else if (w <= 560) {
        setSize({ box: 260, radius: 96, particles: 130 });
      } else if (w <= 820) {
        setSize({ box: 380, radius: 145, particles: 170 });
      } else {
        setSize({ box: 480, radius: 190, particles: 220 });
      }
    }
    recompute();
    window.addEventListener("resize", recompute);
    return () => window.removeEventListener("resize", recompute);
  }, []);

  return size;
}

/** The centre column: header + nav, then the agent ring around the
    decorative particle core - the reference image's focal element,
    rebuilt around real agents instead of generic micro-app icons. */
export function CenterCore({
  agents,
  pulsing,
  fleetFailed,
  streamState,
  rows,
}: {
  agents: AgentEntry[] | null;
  pulsing: Record<string, boolean>;
  fleetFailed: boolean;
  streamState: "connecting" | "live" | "reconnecting" | "offline";
  rows: TraceRow[];
}) {
  const { box, radius, particles } = useRingSize();
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <HeaderNav />

      <div
        aria-label="Agent activity"
        data-fresh={streamState === "live" ? "fresh" : streamState === "reconnecting" ? "stale" : "unavailable"}
        className="flex flex-col items-center gap-2"
      >
        <div
          className="relative flex items-center justify-center"
          style={{ width: box, height: box, maxWidth: "100%" }}
        >
          {/* the outer ring boundary, drawn once - purely a frame */}
          <div
            className="absolute inset-0 rounded-full"
            style={{ border: "1px solid #333" }}
          />
          <CenterParticles size={particles} />
          <AgentRing agents={agents} pulsing={pulsing} radius={radius} onSelect={setSelected} />
        </div>

        {/* A compact real-activity ticker, not a full log panel - the
            log display itself moved out when EmailPanel took this
            column's slot (2026-08-27); the real trace stream still
            needs somewhere honest to show, so it lives here now, small.
            Kept to the last 12 rows (not 3): under real load - e.g. the
            full test suite hammering every screen at once - a 3-row
            window can evict a just-posted row before anything checks
            for it, which is a race in the test, not the stream. */}
        <ol className="num flex max-h-16 w-full max-w-[280px] flex-col gap-0.5 overflow-y-auto text-[9px] text-dim">
          {rows
            .slice(-12)
            .reverse()
            .map((row, i) => (
              <li key={`${row.seq ?? "x"}-${i}`} className="truncate text-center">
                {row.actor ?? "?"} &middot; {row.action ?? "?"}
              </li>
            ))}
        </ol>
      </div>

      {selected && <AgentFilesGraph agentName={selected} onClose={() => setSelected(null)} />}

      {fleetFailed && (
        <p data-fresh="unavailable" className="num text-xs text-amber">
          fleet list unavailable - the menu server did not answer
        </p>
      )}
      {agents === null && !fleetFailed && (
        <p data-fresh="empty" className="num text-xs text-dim">
          asking who exists&hellip;
        </p>
      )}
    </div>
  );
}
