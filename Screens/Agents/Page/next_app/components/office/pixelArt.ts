// Pixel-art tile + sprite kit for the AGENT DECK office (D15, warm rebuild D16).
//
// Everything here is code-drawn: a palette, string-matrix sprites, and painter
// functions that write 1x1 rects into a small buffer. The buffer is blitted to
// the visible canvas at an integer scale with smoothing off, so one buffer unit
// is always a clean square of screen pixels. No binary assets, no WebGL.

export type Ctx = CanvasRenderingContext2D;
export type Palette = Record<string, string | null | undefined>;

// --- palette -------------------------------------------------------------
// D16.1 warm set: paper, sand, oak and honey grounds, terracotta / mustard /
// sage / dusty-rose accents, warm-brown ink. No near-black anywhere — even the
// outlines are walnut ink. Keys are single chars used by the sprite matrices
// and are unchanged from D15, so every matrix keeps working.
export const P: Palette = {
  " ": null,
  ".": null,

  "0": "#4A3527", // outline / walnut ink
  "1": "#B9804E", // oak wood
  "2": "#A56D3F",
  "3": "#C89563",
  "4": "#8A5F36",
  "5": "#96683B",

  "6": "#C98A6B", // warm brick
  "7": "#D89A7B",
  "8": "#A96A50",

  "9": "#FBF3E2", // cream / paper / bone
  "-": "#EFE3C8",
  "=": "#DFCDA8",

  a: "#9B8B76", // warm greige metal
  b: "#B3A48D",
  c: "#D9CDB4",
  d: "#F2DCA8", // pale-amber screen
  e: "#C9AE72",

  f: "#C96F4A", // terracotta spine / card
  g: "#7E9BAA", // dusty teal spine
  h: "#9AA86B", // olive spine
  i: "#E5B44A", // mustard spine
  j: "#C77B9E", // rose spine
  k: "#DBA768", // honey spine

  l: "#7E9463", // sage deep
  m: "#ADBE93", // sage
  n: "#5F7A4A", // sage shadow
  o: "#C96F4A", // terracotta pot
  p: "#9A5636",

  q: "#DCA98F", // dusty rose sofa
  r: "#C08D74",
  s: "#E8BBA4",
  S: "#F2CDBB",

  t: "#F2C9A0", // skin
  v: "#DBA97F",
  u: "#4A3527", // hair
  U: "#6B4A2F",

  w: "#E8A13C", // amber
  x: "#D95F43", // coral — act-now only (D13.1 rule carries over)
  y: "#8FAF7E", // sage success

  z: "#6B5138", // rack body walnut
  A: "#7A5E42", // rack unit
  B: "#4A3527", // rack dark
  C: "#FFD98E", // LED on (warm amber)
  D: "#A98C5F", // LED off (dim amber)

  W: "#EFE3C8", // cream stone
  V: "#DCCBAA",
  L: "#E7B9C4", // rose lounge tile
  M: "#EFC2CF",
  N: "#D89FAF",
  T: "#B9804E", // checker oak
  G: "#FBF3E2", // checker cream

  // character keys (kept separate so furniture and people never collide)
  "#": "#6F8B7E", // shirt (recoloured per department at draw time)
  "%": "#8AA694", // shirt highlight
  "@": "#4A3527", // hair
  "+": "#F2C9A0", // skin
  "~": "#DBA97F", // skin shade
  "!": "#4A3527", // eye
  "&": "#7A5E42", // trousers
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

/** Paint a sprite mirrored horizontally (for the cat and left-walkers). */
export function pxFlipX(ctx: Ctx, matrix: string[], ox: number, oy: number, pal?: Palette) {
  const map = pal ?? P;
  for (let y = 0; y < matrix.length; y++) {
    const row = matrix[y];
    const w = row.length;
    for (let x = 0; x < w; x++) {
      const color = map[row[x]];
      if (!color) continue;
      ctx.fillStyle = color;
      ctx.fillRect(ox + (w - 1 - x), oy + y, 1, 1);
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

/** Honey walkway planks — the one connected path loop (D16.2). */
export function floorPath(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, "#DBA768");
  const plank = 6;
  for (let py = 0; py < h; py += plank) {
    const band = (py / plank) % 2;
    fill(ctx, x, y + py, w, plank - 1, band ? "#D19C5C" : "#E2B173");
    fill(ctx, x, y + py + plank - 1, w, 1, "#C08A52");
    for (let bx = band * 14; bx < w; bx += 28) {
      fill(ctx, x + bx, y + py, 1, plank - 1, "#C08A52");
      if (grain(bx, py, 3) > 0.7) {
        fill(ctx, x + Math.min(bx + 8, w - 3), y + py + 2, 2, 1, "#C89563");
      }
    }
  }
}

/** Warm sand planks — the default zone ground. */
export function floorSand(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, "#E7D3AC");
  const plank = 7;
  for (let py = 0; py < h; py += plank) {
    const band = (py / plank) % 2;
    fill(ctx, x, y + py, w, plank - 1, band ? "#E0C99E" : "#EAD6B4");
    fill(ctx, x, y + py + plank - 1, w, 1, "#CBAD82");
    for (let bx = band * 16; bx < w; bx += 32) {
      fill(ctx, x + bx, y + py, 1, plank - 1, "#CBAD82");
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

/** Model room floor: warm walnut access panels with amber bolts. */
export function floorRaised(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, "#C4A374");
  const cell = 12;
  for (let py = 0; py < h; py += cell) {
    for (let pxx = 0; pxx < w; pxx += cell) {
      const cw = Math.min(cell - 2, w - pxx - 1);
      const ch = Math.min(cell - 2, h - py - 1);
      if (cw <= 0 || ch <= 0) continue;
      fill(ctx, x + pxx + 1, y + py + 1, cw, ch, "#CDAD7E");
      fill(ctx, x + pxx, y + py, Math.min(cell, w - pxx), 1, "#B08F60");
      fill(ctx, x + pxx, y + py, 1, Math.min(cell, h - py), "#B08F60");
      fill(ctx, x + pxx + 2, y + py + 2, 1, 1, "#A98C5F");
      fill(ctx, x + pxx + cell - 3, y + py + cell - 3, 1, 1, "#A98C5F");
    }
  }
}

/** Deck war-room floor: sealed warm concrete with a faint terracotta grid. */
export function floorSealed(ctx: Ctx, x: number, y: number, w: number, h: number) {
  fill(ctx, x, y, w, h, "#E3CFA5");
  const cell = 10;
  for (let py = 0; py < h; py += cell) {
    for (let pxx = 0; pxx < w; pxx += cell) {
      const tone = grain(pxx, py, 9) > 0.5 ? "#E9D7B0" : "#E0CBA0";
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
  ctx.fillStyle = "rgba(201,111,74,0.14)";
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

/** The café checker strip: oak / cream, warm. */
export function checkerStrip(ctx: Ctx, x: number, y: number, w: number, cell = 5) {
  for (let i = 0; i < w; i += cell) {
    fill(ctx, x + i, y, Math.min(cell, w - i), cell, (i / cell) % 2 ? (P["T"] as string) : (P["G"] as string));
  }
  fill(ctx, x, y, w, 1, P["0"] as string);
  fill(ctx, x, y + cell - 1, w, 1, P["0"] as string);
}

// --- freestanding boards -------------------------------------------------
// With no walls (D16.2) each zone's signature fixture is a board on legs;
// drawPlan adds the legs + ground shadow around whatever these fill.

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
  // running bars: sage up-ticks, one honey down-tick (coral stays act-now only)
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
  fill(ctx, x + 1, y + 1, w - 2, h - 2, "#EFE3C8");
  const cols = 5;
  const cw = Math.floor((w - 4) / cols);
  for (let c = 0; c < cols; c++) {
    const cxp = x + 2 + c * cw;
    fill(ctx, cxp, y + 2, cw - 2, h - 4, "#E5D5AE");
    fill(ctx, cxp, y + 2, cw - 2, 1, "#D8C4A0");
    for (let r = 0; r < 3; r++) {
      const cy = y + 5 + r * 4;
      if (cy + 3 > y + h - 3) break;
      const card = c === 2 && r === 0 ? accent : BOOK_COLORS[(c + r * 2) % BOOK_COLORS.length];
      fill(ctx, cxp + 1, cy, cw - 4, 3, card);
      fill(ctx, cxp + 1, cy, cw - 4, 1, shade(card, 1.25));
    }
  }
}

/** Cork ENH pinboard with pinned notes. */
export function pinboard(ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) {
  fill(ctx, x, y, w, h, P["0"] as string);
  fill(ctx, x + 1, y + 1, w - 2, h - 2, P["k"] as string);
  for (let gy = y + 1; gy < y + h - 1; gy += 3) {
    for (let gx = x + 1; gx < x + w - 1; gx += 3) {
      if (grain(gx, gy, 11) > 0.72) fill(ctx, gx, gy, 1, 1, shade(P["k"] as string, 0.88));
    }
  }
  let n = 0;
  for (let ny = y + 3; ny + 4 <= y + h - 2; ny += 5) {
    for (let nx = x + 3; nx + 4 <= x + w - 2; nx += 6) {
      const card = n === 2 ? accent : BOOK_COLORS[(n * 3 + 1) % BOOK_COLORS.length];
      fill(ctx, nx, ny, 4, 3, card);
      fill(ctx, nx, ny + 3, 4, 1, shade(card, 0.72));
      fill(ctx, nx + 1, ny - 1, 1, 1, P["c"] as string);
      n++;
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

export function cushion(ctx: Ctx, x: number, y: number, base: string) {
  fill(ctx, x + 1, y, 7, 1, P["0"] as string);
  fill(ctx, x, y + 1, 9, 4, P["0"] as string);
  fill(ctx, x + 1, y + 1, 7, 3, base);
  fill(ctx, x + 2, y + 1, 5, 1, shade(base, 1.22));
  fill(ctx, x + 1, y + 5, 7, 1, P["0"] as string);
}

/** Round war-room table with stools around it. */
export function roundTable(ctx: Ctx, cx: number, cy: number, r = 13) {
  for (let dy = -r; dy <= r; dy++) {
    const half = Math.round(Math.sqrt(Math.max(0, r * r - dy * dy)) * 0.92);
    if (half <= 0) continue;
    fill(ctx, cx - half, cy + dy, half * 2, 1, dy < -r + 2 ? (P["0"] as string) : (P["0"] as string));
  }
  for (let dy = -r + 2; dy <= r - 2; dy++) {
    const half = Math.round(Math.sqrt(Math.max(0, (r - 2) * (r - 2) - dy * dy)) * 0.92);
    if (half <= 0) continue;
    fill(ctx, cx - half, cy + dy, half * 2, 1, dy < 0 ? (P["3"] as string) : (P["1"] as string));
  }
  // highlight sheen + a mug and papers
  fill(ctx, cx - 5, cy - 6, 8, 1, P["3"] as string);
  fill(ctx, cx + 2, cy - 2, 5, 4, P["-"] as string);
  fill(ctx, cx + 3, cy - 1, 3, 1, P["="] as string);
  fill(ctx, cx - 7, cy + 1, 3, 3, P["9"] as string);
  fill(ctx, cx - 7, cy + 1, 3, 1, P["c"] as string);
  // stools at three sides
  px(ctx, STOOL, cx - 3, cy + r + 1);
  px(ctx, STOOL, cx - r - 7, cy - 3);
  px(ctx, STOOL, cx + r + 1, cy - 3);
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

/** Floor lamp: mustard shade on an oak pole (library light pools). */
export function floorLamp(ctx: Ctx, x: number, y: number) {
  fill(ctx, x, y, 9, 2, P["0"] as string);
  fill(ctx, x + 1, y + 1, 7, 4, P["i"] as string);
  fill(ctx, x + 2, y + 2, 5, 2, shade(P["i"] as string, 1.18));
  fill(ctx, x + 4, y + 5, 1, 12, P["4"] as string);
  fill(ctx, x + 2, y + 17, 5, 2, P["0"] as string);
}

/** Striped welcome mat. */
export function welcomeMat(ctx: Ctx, x: number, y: number) {
  for (let i = 0; i < 3; i++) {
    fill(ctx, x + i * 6, y, 6, 7, i % 2 ? (P["9"] as string) : (P["o"] as string));
  }
  fill(ctx, x, y, 18, 1, P["0"] as string);
  fill(ctx, x, y + 6, 18, 1, P["0"] as string);
  fill(ctx, x, y, 1, 7, P["0"] as string);
  fill(ctx, x + 17, y, 1, 7, P["0"] as string);
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

/** Espresso machine on its cabinet — the lobby café corner. */
export const ESPRESSO = [
  ".00000000.",
  "0aaaaaaaa0",
  "0abbbbbb0",
  "0abppppb0",
  "0abp99pb0",
  "0aaaaaaaa0",
  "0aaa00aaa0",
  "0aaa00aaa0",
  "0aaaaaaaa0",
  ".00000000.",
  "..044490..",
  "..099990..",
  "..000000..",
];

/** Wooden CRT TV for the anime lounge. */
export const CRT_TV = [
  "..0.......0........",
  "...0.....0.........",
  "....0...0..........",
  "0000000000000000000",
  "0111111111111111110",
  "01ddddddddddddddd10",
  "01dd=dddddd=dddd=10",
  "01ddddddddddddddd10",
  "01d=dddd=ddddddd=10",
  "01ddddddddddddddd10",
  "0111111111111111110",
  "0a0a0a0a0a0a0a0a0a0",
  "0000000000000000000",
  "..04...........04..",
  "..040.........040..",
];

/** The office cat, walking right (mirrored for left). */
export const CAT = [
  ".0...0.....",
  ".00.00.....",
  ".0mmm0.....",
  ".0m!m0..0..",
  ".0mmm00000.",
  "0mmmmmmmmm0",
  ".00.0..0.0.",
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

export const POSE_WALK = [
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
  ".0&&0..0&&0.",
  "0&&......&&0",
  "000......000",
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
  fill(ctx, x + 1, y, w - 2, 1, "rgba(74,53,39,0.30)");
  fill(ctx, x + 2, y + 1, w - 4, 1, "rgba(74,53,39,0.20)");
}

/** Soft status halo under a character — an ellipse of 1px marks, not a stroke. */
export function halo(ctx: Ctx, cx: number, cy: number, rx: number, ry: number, color: string) {
  ctx.fillStyle = color;
  for (let a = 0; a < 32; a++) {
    const t = (a / 32) * Math.PI * 2;
    ctx.fillRect(Math.round(cx + Math.cos(t) * rx), Math.round(cy + Math.sin(t) * ry), 1, 1);
  }
}

/** Spawn sparkle: rays that fly outward then fade (D16.4 materialize). */
export function sparkle(ctx: Ctx, cx: number, cy: number, progress: number, color: string) {
  const rays = 8;
  for (let k = 0; k < rays; k++) {
    const t = (k / rays) * Math.PI * 2;
    const r1 = 2 + progress * 10;
    const r0 = Math.max(1, r1 - 2.5);
    ctx.fillStyle = k % 2 ? color : "#FFE9AE";
    for (let r = r0; r <= r1; r++) {
      ctx.fillRect(Math.round(cx + Math.cos(t) * r), Math.round(cy + Math.sin(t) * r * 0.7), 1, 1);
    }
  }
  if (progress < 0.5) {
    ctx.fillStyle = "#FFE9AE";
    ctx.fillRect(Math.round(cx - 1), Math.round(cy - 1), 3, 3);
  }
}

/** Puff ring for the leave animation — a quick expanding outline. */
export function puff(ctx: Ctx, cx: number, cy: number, progress: number, color: string) {
  const r = 2 + progress * 9;
  ctx.globalAlpha = 1 - progress;
  ctx.fillStyle = color;
  for (let a = 0; a < 20; a++) {
    const t = (a / 20) * Math.PI * 2;
    ctx.fillRect(Math.round(cx + Math.cos(t) * r), Math.round(cy + Math.sin(t) * r * 0.6), 1, 1);
  }
  ctx.globalAlpha = 1;
}
