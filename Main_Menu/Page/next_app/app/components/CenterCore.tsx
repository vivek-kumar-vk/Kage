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

function HeaderIcon({ label, d }: { label: string; d: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      className="flex h-7 w-7 items-center justify-center rounded text-dim transition-colors hover:text-white"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
        {d}
      </svg>
    </button>
  );
}

/** The centre column: the RUBRIC title block, then the agent ring
    spinning around the live 3D particle core - the reference image's
    focal element. */
export function CenterCore() {
  const { box, radius } = useRingSize();

  return (
    <div className="flex flex-col items-center gap-6 py-2">
      <header className="flex flex-col items-center gap-2 text-center">
        <div className="flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 2.5 20.5 7v10L12 21.5 3.5 17V7z"
              fill="none"
              stroke="#ff7a00"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
          </svg>
          <h1 className="text-xl font-semibold tracking-[0.14em]">
            Kage<span className="rubric-accent font-normal">.GG</span>
          </h1>
        </div>
        <p className="rubric-sub text-[10px]">Vivek Kumar &nbsp;|&nbsp; KageEnsui</p>
        <div className="mt-1 flex items-center gap-2">
          <HeaderIcon
            label="edit"
            d={
              <path
                d="M4 20h4L18.5 9.5a2 2 0 0 0-2.83-2.83L5 17v3z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
            }
          />
          <HeaderIcon
            label="search"
            d={
              <>
                <circle cx="11" cy="11" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <path d="m20 20-4.3-4.3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </>
            }
          />
          <HeaderIcon
            label="apps"
            d={
              <>
                <rect x="4" y="4" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <rect x="13" y="4" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <rect x="4" y="13" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <rect x="13" y="13" width="7" height="7" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
              </>
            }
          />
          <HeaderIcon
            label="info"
            d={
              <>
                <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <path d="M12 11v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                <circle cx="12" cy="7.7" r="1.05" fill="currentColor" />
              </>
            }
          />
        </div>
      </header>

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
