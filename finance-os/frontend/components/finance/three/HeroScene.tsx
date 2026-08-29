"use client";
import { useEffect, useState } from "react";

export default function HeroScene() {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <div className="relative h-48 w-full overflow-hidden rounded-lg bg-carbon-dark">
      <svg viewBox="0 0 200 120" className="h-full w-full" role="img" aria-label="Finance OS">
        <defs>
          <radialGradient id="hero-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00d2ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#00d2ff" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="100" cy="60" r="40" fill="url(#hero-glow)" />
        <g fill="none" stroke="#e10600" strokeWidth="1.5" opacity="0.7">
          <ellipse cx="100" cy="60" rx="70" ry="28">
            {!reduced && (
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="0 100 60"
                to="360 100 60"
                dur="18s"
                repeatCount="indefinite"
              />
            )}
          </ellipse>
        </g>
      </svg>
    </div>
  );
}
