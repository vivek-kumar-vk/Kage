"use client";

import { useEffect, useRef } from "react";
import { mix } from "../office/pixelArt";

const SKIN = "#F2C9A0";
const INK = "#4A3527";

function hashOf(name: string) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 997;
  return h;
}

/** Pixel face drawn per agent — deterministic from the name (D17.1). */
export default function PixelAvatar({
  name,
  color,
  size = 36,
}: {
  name: string;
  color: string;
  size?: number;
}) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const S = 12;
    canvas.width = S;
    canvas.height = S;
    ctx.imageSmoothingEnabled = false;

    const hash = hashOf(name);
    const hairLong = hash % 3; // how far side hair comes down
    const fringe = hash % 2 === 0;

    // warm tinted backdrop
    ctx.fillStyle = mix("#FBF3E2", color, 0.28);
    ctx.fillRect(0, 0, S, S);

    // hair top
    ctx.fillStyle = INK;
    ctx.fillRect(2, 1, 8, 3);
    if (fringe) {
      ctx.fillRect(3, 4, 2, 1);
      ctx.fillRect(7, 4, 2, 1);
    } else {
      ctx.fillRect(2, 4, 8, 1);
    }
    // side hair
    ctx.fillRect(2, 4, 1, 2 + hairLong);
    ctx.fillRect(9, 4, 1, 2 + hairLong);

    // face
    ctx.fillStyle = SKIN;
    ctx.fillRect(3, 4, 6, 5);
    // eyes
    ctx.fillStyle = INK;
    ctx.fillRect(4, 5, 1, 1);
    ctx.fillRect(7, 5, 1, 1);
    // shade
    ctx.fillStyle = "#DBA97F";
    ctx.fillRect(3, 8, 6, 1);

    // shoulders / shirt in the department accent
    ctx.fillStyle = color;
    ctx.fillRect(2, 9, 8, 3);
    ctx.fillStyle = mix(color, "#FFFFFF", 0.3);
    ctx.fillRect(2, 9, 8, 1);
    // neck
    ctx.fillStyle = SKIN;
    ctx.fillRect(5, 8, 2, 1);
  }, [name, color]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      style={{ width: size, height: size, imageRendering: "pixelated" }}
    />
  );
}
