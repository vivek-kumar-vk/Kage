"use client";

import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  colour: string;
}

const COLOURS = ["#7C6FF2", "#ff2bd6", "#00e5ff", "#E8E4DA"];

/** The glowing centre core - purely decorative ambient motion, matching
    the reference image's particle cloud. It represents nothing and is
    never wired to real data (C12: a status-looking visual that isn't a
    real status is the failure mode, so this one is styled clearly as
    background art, not a gauge). Canvas, not an image asset or a
    library - keeps the static export self-contained. */
export function CenterParticles({ size = 220 }: { size?: number }) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const particles: Particle[] = Array.from({ length: 90 }, () => {
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * (size / 2.4);
      return {
        x: size / 2 + Math.cos(angle) * dist,
        y: size / 2 + Math.sin(angle) * dist,
        r: Math.random() * 1.6 + 0.4,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        colour: COLOURS[Math.floor(Math.random() * COLOURS.length)],
      };
    });

    let raf = 0;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function tick() {
      if (!ctx) return;
      ctx.clearRect(0, 0, size, size);
      for (const p of particles) {
        if (!reduceMotion) {
          p.x += p.vx;
          p.y += p.vy;
          const cx = size / 2;
          const cy = size / 2;
          const d = Math.hypot(p.x - cx, p.y - cy);
          if (d > size / 2.2) {
            p.vx *= -1;
            p.vy *= -1;
          }
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.colour;
        ctx.globalAlpha = 0.75;
        ctx.fill();
      }
      raf = requestAnimationFrame(tick);
    }
    tick();
    return () => cancelAnimationFrame(raf);
  }, [size]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        borderRadius: "9999px",
        filter: "blur(0.3px)",
      }}
    />
  );
}
