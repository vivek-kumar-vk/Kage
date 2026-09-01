// Pixel-art tile + sprite kit for the AGENT DECK office (D15).
//
// Everything here is code-drawn: a palette, string-matrix sprites, and painter
// functions that write 1x1 rects into a small buffer. The buffer is blitted to
// the visible canvas at an integer scale with smoothing off, so one buffer unit
// is always a clean square of screen pixels. No binary assets, no WebGL.

export type Ctx = CanvasRenderingContext2D;
export type Palette = Record<string, string | null | undefined>;

// --- palette -------------------------------------------------------------
// Warm 16-bit set: wood + brick + bone, with cool metal for the server room
// and a rose/blue lounge. Keys are single chars used by the sprite matrices.
export const P: Palette = {
  " ": null,
  ".": null,

  "0": "#2a1c12", // outline / deep brown-black
  "1": "#8a6a42", // wood
  "2": "#7a5b38",
  "3": "#9c7a4e",
  "4": "#5d4327",
  "5": "#6b4e2f",

  "6": "#7c5142", // brick
  "7": "#8f6153",
  "8": "#5c3a30",

  "9": "#efe9da", // bone / paper / stone
  "-": "#dcd4c1",
  "=": "#c7bea6",

  a: "#464e58", // metal
  b: "#69737e",
  c: "#b7c0c9",
  d: "#7fd7e1", // screen cyan
  e: "#2f6a72",

  f: "#c74b3b", // spines / cards
  g: "#3f7fb0",
  h: "#4f9e5a",
  i: "#e0a63c",
  j: "#7b5aa6",
  k: "#d98a3c",

  l: "#3f7b3a", // plant
  m: "#5aa04d",
  n: "#294f27",
  o: "#b5623a", // terracotta
  p: "#8a4526",

  q: "#c56680", // sofa rose
  r: "#a2506a",
  s: "#e08aa0",
  S: "#f0b3c4",

  t: "#e9b78d", // skin
  v: "#cd9468",
  u: "#3a2a1c", // hair
  U: "#553a24",

  w: "#e8892b", // copper
  x: "#e0403a", // alert
  y: "#40c197", // jade

  z: "#1f232a", // server dark
  A: "#333b44",
  B: "#0f1418",
  C: "#8fd0d8", // led on
  D: "#2b5f66", // led off

  W: "#c9c4b4", // marble
  V: "#b3ab98",
  L: "#4e6f98", // lounge floor
  M: "#5c7fa8",
  N: "#3f5c80",
  T: "#1b1917", // checker dark
  G: "#c9c4b4", // checker light

  // character keys (kept separate so furniture and people never collide)
  "#": "#3f6b7a", // shirt
  "%": "#5b8b9a", // shirt highlight
  "@": "#3a2a1c", // hair
  "+": "#e9b78d", // skin
  "~": "#cd9468", // skin shade
  "!": "#241a12", // eye
  "&": "#33302c", // trousers
};

// --- colour helpers ------------------------------------------------------

function clamp255(v: number) {
  return v < 0 ? 0 : v > 255 ? 255 : Math.round(v);
}

/** Multiply a #rrggbb colour by a factor; >1 lightens, <1 darkens. */
export function shade(hex: string, factor: number): string {
  const n = hex.replace("#", "");
  const r = clamp255(parseInt(n.slice(0, 2), 16) * factor);
  const g = clamp255(parseInt(n.slice(2, 4), 16) * factor);
  const b = clamp255(parseInt(n.slice(4, 6), 16) * factor);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b
    .toString(16)
    .padStart(2, "0")}`;
}

/** Blend two #rrggbb colours; t=0 is a, t=1 is b. */
export function mix(a: string, b: string, t: number): string {
  const pa = a.replace("#", "");
  const pb = b.replace("#", "");
  const out: string[] = [];
  for (let i = 0; i < 3; i++) {
    const va = parseInt(pa.slice(i * 2, i * 2 + 2), 16);
    const vb = parseInt(pb.slice(i * 2, i * 2 + 2), 16);
    out.push(clamp255(va + (vb - va) * t).toString(16).padStart(2, "0"));
  }
  return `#${out.join("")}`;
}

// --- primitives ----------------------------------------------------------

export function fill(ctx: Ctx, x: number, y: number, w: number, h: number, color: string) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w, h);
}

/** Paint a string-matrix sprite. Unknown / null chars are transparent. */
export function px(ctx: Ctx, matrix: string[], ox: number, oy: number, pal?: Palette) {
  const map = pal ?? P;
  for (let y = 0; y < matrix.length; y++) {
    const row = matrix[y];
    for (let x = 0; x < row.length; x++) {
      const color = map[row[x]];
      if (!color) continue;
      ctx.fillStyle = color;
      ctx.fillRect(ox + x, oy + y, 1, 1);
    }
  }
}

export function spriteW(matrix: string[]) {
  let w = 0;
  for (const row of matrix) w = Math.max(w, row.length);
  return w;
}

/** Cheap deterministic hash so "random" grain is identical every repaint. */
function grain(x: number, y: number, seed: number) {
  const n = Math.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453;
  return n - Math.floor(n);
}

// --- floors --------------------------------------------------------------

export function floorWood(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["1"] as string);
  const plank = 6;
  for (let py = 0; py < h; py += plank) {
    const band = (py / plank) % 2;
    fill(ctx, x, y + py, w, plank - 1, (band ? P["2"] : P["3"]) as string);
    fill(ctx, x, y + py + plank - 1, w, 1, P["4"] as string);
    // staggered plank breaks + knots
    for (let bx = band * 15; bx < w; bx += 30) {
      fill(ctx, x + bx, y + py, 1, plank - 1, P["4"] as string);
      if (grain(bx, py, 3) > 0.62) {
        fill(ctx, x + Math.min(bx + 7, w - 3), y + py + 2, 2, 1, P["5"] as string);
      }
    }
  }
}

export function floorTile(
  ctx: Ctx,
  x: number,
  y: number,
  w: number,
  h: number,
  base: string,
  hi: string,
  grout: string,
  cell: number
) {
  fill(ctx, x, y, w, h, base);
  for (let py = 0; py < h; py += cell) {
    for (let pxx = 0; pxx < w; pxx += cell) {
      const alt = (pxx / cell + py / cell) % 2 === 0;
      fill(
        ctx,
        x + pxx + 1,
        y + py + 1,
        Math.min(cell - 1, w - pxx - 1),
        Math.min(cell - 1, h - py - 1),
        alt ? hi : base
      );
    }
  }
  ctx.fillStyle = grout;
  for (let py = 0; py <= h; py += cell) ctx.fillRect(x, y + py, w, 1);
  for (let pxx = 0; pxx <= w; pxx += cell) ctx.fillRect(x + pxx, y, 1, h);
}

/** Raised server-room floor: bolted metal panels. */
export function floorRaised(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["z"] as string);
  const cell = 12;
  for (let py = 0; py < h; py += cell) {
    for (let pxx = 0; pxx < w; pxx += cell) {
      const cw = Math.min(cell - 2, w - pxx - 1);
      const ch = Math.min(cell - 2, h - py - 1);
      if (cw <= 0 || ch <= 0) continue;
      fill(ctx, x + pxx + 1, y + py + 1, cw, ch, P["A"] as string);
      fill(ctx, x + pxx, y + py, Math.min(cell, w - pxx), 1, P["B"] as string);
      fill(ctx, x + pxx, y + py, 1, Math.min(cell, h - py), P["B"] as string);
      fill(ctx, x + pxx + 2, y + py + 2, 1, 1, P["D"] as string);
      fill(ctx, x + pxx + cell - 3, y + py + cell - 3, 1, 1, P["D"] as string);
    }
  }
}

/** Deck war-room floor: sealed concrete with a faint copper grid. */
export function floorConcrete(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, "#2a221a");
  const cell = 10;
  for (let py = 0; py < h; py += cell) {
    for (let pxx = 0; pxx < w; pxx += cell) {
      const tone = grain(pxx, py, 9) > 0.5 ? "#332a20" : "#302719";
      fill(
        ctx,
        x + pxx + 1,
        y + py + 1,
        Math.min(cell - 2, w - pxx - 1),
        Math.min(cell - 2, h - py - 1),
        tone
      );
    }
  }
  ctx.fillStyle = "rgba(232,137,43,0.10)";
  for (let py = 0; py <= h; py += cell) ctx.fillRect(x, y + py, w, 1);
  for (let pxx = 0; pxx <= w; pxx += cell) ctx.fillRect(x + pxx, y, 1, h);
}

export function rug(
  ctx: Ctx,
  x: number,
  y: number,
  w: number,
  h: number,
  body: string,
  edge: string
) {
  fill(ctx, x, y, w, h, body);
  fill(ctx, x, y, w, 1, edge);
  fill(ctx, x, y + h - 1, w, 1, edge);
  fill(ctx, x, y, 1, h, edge);
  fill(ctx, x + w - 1, y, 1, h, edge);
  fill(ctx, x + 2, y + 2, w - 4, 1, edge);
  fill(ctx, x + 2, y + h - 3, w - 4, 1, edge);
  // fringe
  for (let i = 1; i < w - 1; i += 3) {
    fill(ctx, x + i, y - 1, 1, 1, edge);
    fill(ctx, x + i, y + h, 1, 1, edge);
  }
}

/** The reference image's black/bone checker strip. */
export function checkerStrip(ctx: Ctx, x: number, y: number, w: number, cell = 5) {
  for (let i = 0; i < w; i += cell) {
    fill(ctx, x + i, y, Math.min(cell, w - i), cell, (i / cell) % 2 ? (P["T"] as string) : (P["G"] as string));
  }
  fill(ctx, x, y, w, 1, P["0"] as string);
  fill(ctx, x, y + cell - 1, w, 1, P["0"] as string);
}

// --- walls ---------------------------------------------------------------

export function brickWall(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["8"] as string);
  for (let ry = 1; ry < h - 2; ry += 3) {
    const off = ((ry - 1) / 3) % 2 ? 6 : 0;
    for (let rx = -12; rx < w; rx += 12) {
      const bx = x + rx + off + 1;
      const bw = Math.min(10, x + w - bx);
      if (bw <= 0 || bx < x) continue;
      fill(ctx, bx, y + ry, bw, 2, grain(rx, ry, 5) > 0.66 ? (P["7"] as string) : (P["6"] as string));
    }
  }
  fill(ctx, x, y, w, 1, "rgba(255,255,255,0.06)");
  fill(ctx, x, y + h - 2, w, 2, P["0"] as string);
}

export function panelWall(ctx: Ctx, x: number, y: number, w: number, h: number, tint: string) {
  fill(ctx, x, y, w, h, tint);
  fill(ctx, x, y, w, 1, shade(tint, 1.4));
  for (let sx = 10; sx < w; sx += 20) fill(ctx, x + sx, y + 1, 1, h - 3, shade(tint, 0.72));
  fill(ctx, x, y + h - 2, w, 2, P["0"] as string);
}

// --- wall fixtures (each room's signature back-wall piece) ---------------

const BOOK_COLORS = ["f", "g", "h", "i", "j", "k"].map((c) => P[c] as string);

export function ledWall(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["B"] as string);
  for (let ly = y + 2; ly < y + h - 2; ly += 2) {
    for (let lx = x + 2; lx < x + w - 2; lx += 3) {
      const on = grain(lx, ly, 1) > 0.55;
      fill(ctx, lx, ly, 2, 1, on ? accent : (P["D"] as string));
    }
  }
}

export function tickerBoard(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["B"] as string);
  // running bars: jade up-ticks, one amber down-tick (red stays act-now only)
  let cursor = x + 3;
  let step = 0;
  while (cursor < x + w - 4) {
    const bw = 2 + (step % 3);
    const bh = 2 + Math.floor(grain(cursor, step, 4) * (h - 6));
    const down = step % 5 === 3;
    fill(ctx, cursor, y + h - 3 - bh, bw, bh, down ? (P["i"] as string) : accent);
    cursor += bw + 2;
    step++;
  }
  fill(ctx, x + 2, y + 2, w - 4, 1, shade(accent, 0.6));
}

export function whiteboard(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["9"] as string);
  // scribbles: a couple of boxes and an arrow between them
  fill(ctx, x + 4, y + 3, 9, 6, P["="] as string);
  fill(ctx, x + 5, y + 4, 7, 4, P["9"] as string);
  fill(ctx, x + w - 15, y + 3, 9, 6, P["="] as string);
  fill(ctx, x + w - 14, y + 4, 7, 4, P["9"] as string);
  fill(ctx, x + 14, y + 6, w - 30, 1, accent);
  fill(ctx, x + w - 18, y + 5, 1, 3, accent);
  fill(ctx, x + 5, y + h - 4, w - 22, 1, P["="] as string);
  fill(ctx, x + 5, y + h - 6, Math.floor(w / 2), 1, P["="] as string);
}

export function kanbanBoard(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, "#3a2f24");
  const cols = 5;
  const cw = Math.floor((w - 4) / cols);
  for (let c = 0; c < cols; c++) {
    const cxp = x + 2 + c * cw;
    fill(ctx, cxp, y + 2, cw - 2, h - 4, "#4a3d2e");
    fill(ctx, cxp, y + 2, cw - 2, 1, "#5d4c39");
    for (let r = 0; r < 3; r++) {
      const cy = y + 5 + r * 4;
      if (cy + 3 > y + h - 3) break;
      const card = c === 2 && r === 0 ? accent : BOOK_COLORS[(c + r * 2) % BOOK_COLORS.length];
      fill(ctx, cxp + 1, cy, cw - 4, 3, card);
      fill(ctx, cxp + 1, cy, cw - 4, 1, shade(card, 1.25));
    }
  }
}

export function artWall(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  const frames = 3;
  const fw = Math.floor(w / frames) - 3;
  for (let i = 0; i < frames; i++) {
    const fx = x + i * (fw + 3);
    fill(ctx, fx, y, fw, h, P["0"] as string);
    fill(ctx, fx + 1, y + 1, fw - 2, h - 2, P["9"] as string);
    const art = i === 1 ? accent : i === 0 ? (P["L"] as string) : (P["q"] as string);
    fill(ctx, fx + 3, y + 3, fw - 6, h - 6, art);
    fill(ctx, fx + 3, y + 3, fw - 6, 1, shade(art, 1.3));
    fill(ctx, fx + 4, y + h - 6, fw - 10, 2, shade(art, 0.7));
  }
}

export function lobbySign(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["9"] as string);
  fill(ctx, x + 3, y + 3, w - 6, h - 6, P["="] as string);
  // engraved bar + accent underline
  fill(ctx, x + 6, y + Math.floor(h / 2) - 1, w - 12, 2, P["0"] as string);
  fill(ctx, x + 6, y + h - 5, Math.floor((w - 12) / 2), 1, accent);
}

// --- furniture painters --------------------------------------------------

export function bookshelf(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["5"] as string);
  let shelf = 0;
  for (let sy = y + 2; sy + 7 <= y + h - 1; sy += 8) {
    let bx = x + 2;
    while (bx < x + w - 3) {
      const bw = 1 + Math.floor(grain(bx, sy, shelf) * 3);
      if (bx + bw > x + w - 2) break;
      const bh = 4 + (grain(bx, shelf, 2) > 0.5 ? 1 : 0);
      const col = BOOK_COLORS[Math.floor(grain(bx, sy, shelf + 7) * BOOK_COLORS.length)];
      fill(ctx, bx, sy + (6 - bh), bw, bh, col);
      fill(ctx, bx, sy + (6 - bh), 1, bh, shade(col, 1.3));
      bx += bw + 1;
    }
    fill(ctx, x + 1, sy + 6, w - 2, 1, P["4"] as string);
    fill(ctx, x + 1, sy + 7, w - 2, 1, P["0"] as string);
    shelf++;
  }
}

export function serverRack(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["z"] as string);
  for (let uy = y + 2; uy + 4 <= y + h - 4; uy += 4) {
    fill(ctx, x + 2, uy, w - 4, 3, P["A"] as string);
    fill(ctx, x + 2, uy + 3, w - 4, 1, P["B"] as string);
    for (let lx = x + 3; lx < x + w - 4; lx += 3) {
      fill(ctx, lx, uy + 1, 1, 1, grain(lx, uy, 6) > 0.42 ? (P["C"] as string) : (P["D"] as string));
    }
  }
  fill(ctx, x + 1, y + h - 4, w - 2, 3, P["a"] as string);
  fill(ctx, x + 2, y + h - 3, w - 4, 1, P["b"] as string);
}

export function sofa(
  ctx: Ctx,
  x: number,
  y: number,
  w: number,
  h: number,
  base: string,
  hi: string,
  dark: string
) {
  fill(ctx, x, y, w, h, P["0"] as string);
  // back rest
  fill(ctx, x + 1, y + 1, w - 2, 4, dark);
  fill(ctx, x + 1, y + 1, w - 2, 1, hi);
  // seat
  fill(ctx, x + 1, y + 5, w - 2, h - 6, base);
  // arms
  fill(ctx, x + 1, y + 5, 3, h - 6, dark);
  fill(ctx, x + w - 4, y + 5, 3, h - 6, dark);
  // cushion splits
  const seats = Math.max(2, Math.round((w - 8) / 20));
  for (let s = 1; s < seats; s++) {
    const sx = x + 4 + Math.round(((w - 8) / seats) * s);
    fill(ctx, sx, y + 5, 1, h - 6, P["0"] as string);
  }
  fill(ctx, x + 4, y + 5, w - 8, 1, hi);
  fill(ctx, x + 1, y + h - 2, w - 2, 1, P["0"] as string);
}

export function confTable(ctx: Ctx, x: number, y: number, w: number, h: number) {
  // chairs along the long sides
  for (let cx = x + 6; cx + 8 <= x + w - 2; cx += 14) {
    px(ctx, CHAIR, cx, y - 7);
    px(ctx, CHAIR, cx, y + h);
  }
  fill(ctx, x, y + 1, w, h - 2, P["0"] as string);
  fill(ctx, x + 1, y, w - 2, h, P["0"] as string);
  fill(ctx, x + 1, y + 2, w - 2, h - 4, P["3"] as string);
  fill(ctx, x + 2, y + 3, w - 4, h - 6, P["1"] as string);
  fill(ctx, x + 2, y + 3, w - 4, 1, P["3"] as string);
  // papers + a mug
  fill(ctx, x + 6, y + Math.floor(h / 2) - 2, 8, 5, P["-"] as string);
  fill(ctx, x + 7, y + Math.floor(h / 2) - 1, 6, 1, P["="] as string);
  fill(ctx, x + 7, y + Math.floor(h / 2) + 1, 4, 1, P["="] as string);
  fill(ctx, x + w - 18, y + Math.floor(h / 2) - 1, 7, 4, P["9"] as string);
  fill(ctx, x + w - 9, y + Math.floor(h / 2) - 1, 3, 3, P["c"] as string);
  fill(ctx, x + w - 9, y + Math.floor(h / 2) - 1, 3, 1, P["9"] as string);
}

export function receptionDesk(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["3"] as string);
  fill(ctx, x + 2, y + 2, w - 4, h - 6, P["1"] as string);
  fill(ctx, x + 1, y + h - 4, w - 2, 3, P["="] as string);
  fill(ctx, x + 1, y + h - 4, w - 2, 1, P["9"] as string);
  // counter accent strip + a desk bell
  fill(ctx, x + 3, y + 3, w - 6, 1, accent);
  fill(ctx, x + w - 12, y + 4, 5, 4, P["w"] as string);
  fill(ctx, x + w - 11, y + 5, 3, 1, P["9"] as string);
}

export function cabinet(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["a"] as string);
  const drawers = Math.max(2, Math.floor((h - 2) / 6));
  for (let d = 0; d < drawers; d++) {
    const dy = y + 2 + d * 6;
    if (dy + 4 > y + h - 1) break;
    fill(ctx, x + 2, dy, w - 4, 4, P["b"] as string);
    fill(ctx, x + Math.floor(w / 2) - 2, dy + 2, 4, 1, P["c"] as string);
  }
}

export function bench(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["5"] as string);
  for (let sx = x + 2; sx < x + w - 2; sx += 4) fill(ctx, sx, y + 1, 2, h - 2, P["3"] as string);
  fill(ctx, x + 1, y + h - 2, w - 2, 1, P["4"] as string);
}

// --- sprite matrices -----------------------------------------------------

/** A worked desk seen from the front-three-quarter angle of the reference. */
export function desk(ctx: Ctx, x: number, y: number, w: number, h: number, wood = P["1"] as string) {
  const edge = shade(wood, 1.16);
  const dark = shade(wood, 0.68);
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 4, edge);
  fill(ctx, x + 2, y + 2, w - 4, h - 6, wood);
  // grain
  for (let gy = y + 3; gy < y + h - 4; gy += 3) fill(ctx, x + 3, gy, w - 6, 1, shade(wood, 0.92));
  // keyboard, notepad, mug
  fill(ctx, x + 4, y + h - 8, 10, 4, P["a"] as string);
  fill(ctx, x + 5, y + h - 7, 8, 2, P["b"] as string);
  fill(ctx, x + 16, y + h - 8, 5, 4, P["-"] as string);
  fill(ctx, x + 17, y + h - 7, 3, 1, P["="] as string);
  fill(ctx, x + 23, y + h - 7, 3, 3, P["9"] as string);
  fill(ctx, x + 23, y + h - 7, 3, 1, P["c"] as string);
  // front edge + legs
  fill(ctx, x + 1, y + h - 3, w - 2, 2, dark);
  fill(ctx, x + 1, y + h - 1, 2, 1, P["0"] as string);
  fill(ctx, x + w - 3, y + h - 1, 2, 1, P["0"] as string);
}

export const MONITOR = [
  "00000000000",
  "0aaaaaaaaa0",
  "0a$$$$$$$a0",
  "0a$$$$$$$a0",
  "0a$$$$$$$a0",
  "0a$$$$$$$a0",
  "0aaaaaaaaa0",
  "00000000000",
  "....0a0....",
  "..00aaa00..",
];

export const CHAIR = [
  ".000000.",
  "04444440",
  "05555550",
  "05555550",
  "04444440",
  ".0.00.0.",
];

export const STOOL = [
  ".0000.",
  "044440",
  "055550",
  "044440",
  ".0..0.",
];

export const PLANT = [
  "....lmml....",
  "..lmmmmmml..",
  ".lmmnmmnmml.",
  "lmmmmmmmmmml",
  ".lmmmmmmmml.",
  "..lmmnmmml..",
  "...0oooo0...",
  "...0oppo0...",
  "...0oooo0...",
  "....0000....",
];

export const CLOCK = [
  "...00000...",
  "..0999990..",
  ".099999990.",
  "09999099990",
  "09999099990",
  "09999000990",
  ".099999990.",
  "..0999990..",
  "...00000...",
];

export const LOWTABLE = [
  "00000000000000",
  "03333333333330",
  "03111111111130",
  "03111c9-111130",
  "03111111111130",
  "03333333333330",
  "00.0......0.00",
  "...0......0...",
];

export const TRASH = [
  ".0000.",
  "0aaaa0",
  "0abba0",
  "0aaaa0",
  "0abba0",
  ".0000.",
];

export const WATER_COOLER = [
  "..0000..",
  ".0dddd0.",
  ".0dddd0.",
  ".0dddd0.",
  "..0990..",
  ".099990.",
  ".090090.",
  ".099990.",
  "..0000..",
];

export const PRINTER = [
  "0000000000",
  "0aaaaaaaa0",
  "0a------a0",
  "0aaaaaaaa0",
  "0abbbbbba0",
  "0aaaaaaaa0",
  "0000000000",
];

export const CABLE_TRAY = [
  "0000000000000000",
  "0dgdgdgdgdgdgdg0",
  "0gdgdgdgdgdgdgd0",
  "0000000000000000",
];

/** Alert glyph floated over a stuck agent. */
export const ALERT = [
  "..0..",
  ".0x0.",
  ".0x0.",
  ".0x0.",
  ".....",
  ".0x0.",
  "..0..",
];

// --- characters ----------------------------------------------------------

export const POSE_IDLE = [
  "....0000....",
  "...0@@@@0...",
  "..0@@@@@@0..",
  "..0@++++@0..",
  "..0+!++!+0..",
  "..0++~~++0..",
  "...0++++0...",
  "...0####0...",
  "..0######0..",
  ".0##%##%##0.",
  ".0########0.",
  "..0######0..",
  "..0&&00&&0..",
  "..0&&..&&0..",
  "..000..000..",
  "............",
];

export const POSE_TYPING = [
  "....0000....",
  "...0@@@@0...",
  "..0@@@@@@0..",
  "..0@++++@0..",
  "..0+!++!+0..",
  "..0++~~++0..",
  "...0++++0...",
  "...0####0...",
  "..0######0..",
  "..0######0..",
  ".0#%####%#0.",
  "..0++##++0..",
  "..0&&00&&0..",
  "..0&&..&&0..",
  "..000..000..",
  "............",
];

export const CHAR_W = 12;
export const CHAR_H = 16;

export function charPalette(shirt: string, hair: string): Palette {
  return {
    ...P,
    "#": shirt,
    "%": shade(shirt, 1.35),
    "@": hair,
    "&": shade(shirt, 0.42),
  };
}

export function shadowBlob(ctx: Ctx, x: number, y: number, w: number) {
  fill(ctx, x + 1, y, w - 2, 1, "rgba(0,0,0,0.26)");
  fill(ctx, x + 2, y + 1, w - 4, 1, "rgba(0,0,0,0.18)");
}

/** Soft status halo under a character — an ellipse of 1px marks, not a stroke. */
export function halo(ctx: Ctx, cx: number, cy: number, rx: number, ry: number, color: string) {
  ctx.fillStyle = color;
  for (let a = 0; a < 32; a++) {
    const t = (a / 32) * Math.PI * 2;
    ctx.fillRect(Math.round(cx + Math.cos(t) * rx), Math.round(cy + Math.sin(t) * ry), 1, 1);
  }
}
