"use client";

import { useCallback, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";

/** Pointer-tracked 3D tilt for a card. Returns a ref, an inline style
    (a `perspective` transform plus `--mx`/`--my` cursor-position custom
    properties for a specular highlight), and pointer handlers. No-ops on
    a coarse pointer or when the OS asks for reduced motion. */
export function useTilt(maxDeg = 6) {
  const ref = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<CSSProperties>({});

  const onPointerMove = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      const el = ref.current;
      if (!el) return;
      if (window.matchMedia("(pointer: coarse)").matches) return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      const rx = (0.5 - py) * 2 * maxDeg;
      const ry = (px - 0.5) * 2 * maxDeg;
      setStyle({
        transform: `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg)`,
        ["--mx" as string]: `${(px * 100).toFixed(1)}%`,
        ["--my" as string]: `${(py * 100).toFixed(1)}%`,
      } as CSSProperties);
    },
    [maxDeg],
  );

  const onPointerLeave = useCallback(() => {
    setStyle({ transform: "perspective(900px) rotateX(0deg) rotateY(0deg)" });
  }, []);

  return { ref, style, onPointerMove, onPointerLeave };
}
