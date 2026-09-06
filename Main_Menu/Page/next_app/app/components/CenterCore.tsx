"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AgentRing } from "./AgentRing";

// The 3D core is a client-only WebGL canvas - never server-rendered, so
// `output: "export"` has nothing to try to pre-render. It fades in once
// the browser has it.
const ParticleCore3D = dynamic(
  () => import("./ParticleCore3D").then((m) => m.ParticleCore3D),
  { ssr: false },
);

/** Real sizing at each width, never a CSS transform on a fixed-size box
    (a transform still leaves the original box's footprint in normal
    flow, which is what makes a narrow phone scroll sideways). Checked
    against the four widths every INKY page uses plus the
    landscape-short case. */
function useRingSize() {
  const [size, setSize] = useState({ box: 560, radius: 250 });

  useEffect(() => {
    function recompute() {
      const w = window.innerWidth;
      const shortLandscape = window.innerHeight <= 560 && w > window.innerHeight;
      if (shortLandscape) setSize({ box: 240, radius: 104 });
      else if (w <= 420) setSize({ box: 250, radius: 108 });
      else if (w <= 560) setSize({ box: 300, radius: 132 });
      else if (w <= 900) setSize({ box: 420, radius: 186 });
      else if (w <= 1280) setSize({ box: 500, radius: 222 });
      else setSize({ box: 560, radius: 250 });
    }
    recompute();
    window.addEventListener("resize", recompute);
    return () => window.removeEventListener("resize", recompute);
  }, []);

  return size;
}

/** The centre column: the turning agent ring around the live 3D particle
    core - every main and sub aboard one circle (owner's call 2026-09-06).
    (The Kage.GG title block lives in the TopBar.) */
export function CenterCore() {
  const { box, radius } = useRingSize();

  return (
    <div className="flex flex-col items-center gap-6 py-2">
      <div
        className="relative flex items-center justify-center"
        style={{ width: box, height: box, maxWidth: "100%" }}
      >
        {/* the outer ring boundary, drawn once - purely a frame */}
        <div
          className="absolute rounded-full"
          style={{
            width: radius * 2 + 4,
            height: radius * 2 + 4,
            border: "1px solid #2a2a2a",
          }}
        />
        <ParticleCore3D />
        <AgentRing radius={radius} />
      </div>
    </div>
  );
}
