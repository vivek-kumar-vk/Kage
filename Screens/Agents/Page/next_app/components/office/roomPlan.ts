// The building, opened up (D16.2 / D18.7 responsive). Six zones on one
// continuous floor — no walls, no doorways, no outer shell. Zones are
// separated by rugs, floor tone and furniture, and one honey walkway loop
// links all six.
//
// RESPONSIVE GEOMETRY: the zone layouts are hand-placed in a fixed 140 x 128
// box, but the walkways between them flex. buildLayout() is called with the
// viewport size (device pixels) and returns an integer blit scale plus a plan
// buffer size that EXACTLY covers the viewport — the spare width/height is
// absorbed by the corridors and outer aprons, so on any screen the six
// chambers fill the frame with nothing cropped and no dead margins.

import {
  bench,
  bookshelf,
  cabinet,
  checkerStrip,
  desk,
  fill,
  floorLamp,
  floorPath,
  floorRaised,
  floorSand,
  floorSealed,
  floorTile,
  artWall,
  kanbanBoard,
  ledWall,
  lobbySign,
  pinboard,
  px,
  PLANT,
  receptionDesk,
  roundTable,
  rug,
  serverRack,
  shade,
  sofa,
  cushion,
  tickerBoard,
  whiteboard,
  welcomeMat,
  CLOCK,
  CRT_TV,
  CABLE_TRAY,
  ESPRESSO,
  LOWTABLE,
  PRINTER,
  TRASH,
  WATER_COOLER,
  type Ctx,
} from "./pixelArt";

export const RW = 140; // zone width (fixed — room layouts are hand-placed)
export const RH = 128; // zone height (fixed)
export const APRON_MIN = 3; // outer walkway ring, smallest width
export const CORR_MIN = 6; // inner corridors, smallest width

// Contain ratio for the initial scale guess: 442 x 268.
export const PLAN_MIN_W = APRON_MIN * 2 + RW * 3 + CORR_MIN * 2; // 442
export const PLAN_MIN_H = APRON_MIN * 2 + RH * 2 + CORR_MIN; // 268
// Hard floor for a feasible scale: zones + a minimal corridor + 1px aprons.
const FEASIBLE_W = RW * 3 + CORR_MIN * 2 + 2; // 434
const FEASIBLE_H = RH * 2 + CORR_MIN + 2; // 264

function clampInt(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, Math.round(v)));
}

export interface Layout {
  /** Integer blit scale — one art pixel is exactly `scale` device pixels. */
  scale: number;
  /** Plan buffer size == ceil(viewport / scale): fills the viewport exactly. */
  bw: number;
  bh: number;
  /** Zone top-left corners (buffer px). */
  colX: [number, number, number];
  rowY: [number, number];
  /** Vertical corridor centres + the horizontal corridor centre. */
  corrX: [number, number];
  corrW: number;
  midY: number;
  /** Outer ring centres for the walk-in path. */
  ringTopY: number;
  ringBottomY: number;
  /** Ambient anchors (steam, lamps, LEDs, CRT, dust, cat) in buffer px. */
  ambient: {
    steam: { x: number; y: number }[];
    lamps: { x: number; y: number }[];
    leds: { x: number; y: number; w: number; h: number }[];
    crt: { x: number; y: number; w: number; h: number };
    dust: { x: number; y: number; w: number; h: number };
    catY: number;
  };
  /** Where walk-in agents start: the lobby café floor. */
  lobbySpawn: { x: number; y: number };
}

export function buildLayout(vw: number, vh: number): Layout {
  // Nearest integer scale to the contain ratio — round, not floor, so a
  // viewport a hair short of the next scale still gets the denser zoom; the
  // flexible aprons absorb the few px of overflow.
  let scale = clampInt(Math.min(vw / PLAN_MIN_W, vh / PLAN_MIN_H), 2, 6);
  while (scale > 2 && (Math.ceil(vw / scale) < FEASIBLE_W || Math.ceil(vh / scale) < FEASIBLE_H)) {
    scale -= 1;
  }
  const bw = Math.ceil(vw / scale);
  const bh = Math.ceil(vh / scale);

  // Spare space becomes wider walkways: quarter each to the two vertical
  // corridors and the two side aprons (same split top/bottom + corridor).
  // Negative spare (dense zoom on a short viewport) squeezes the aprons
  // toward their 1px floor before it touches the corridors.
  const extraW = bw - PLAN_MIN_W;
  const extraH = bh - PLAN_MIN_H;
  const corrW = Math.max(CORR_MIN, CORR_MIN + extraW * 0.25);
  const apronSide = Math.max(1, APRON_MIN + extraW * 0.25);
  const corrH = Math.max(CORR_MIN, CORR_MIN + extraH * 0.5);
  const apronTop = Math.max(1, APRON_MIN + extraH * 0.25);

  const colX: [number, number, number] = [
    Math.round(apronSide),
    Math.round(apronSide + RW + corrW),
    Math.round(apronSide + 2 * (RW + corrW)),
  ];
  const rowY: [number, number] = [
    Math.round(apronTop),
    Math.round(apronTop + RH + corrH),
  ];
  const corrX: [number, number] = [
    Math.round(colX[0] + RW + corrW / 2),
    Math.round(colX[1] + RW + corrW / 2),
  ];
  const midY = Math.round(rowY[0] + RH + corrH / 2);

  // Ambient anchors, resolved from the live zone positions.
  const modelX = colX[0];
  const animeX = colX[1];
  const learningX = colX[2];
  const topY = rowY[0];
  const bottomY = rowY[1];

  return {
    scale,
    bw,
    bh,
    colX,
    rowY,
    corrX,
    corrW,
    midY,
    ringTopY: Math.round(apronTop / 2),
    ringBottomY: Math.round(bh - (bh - (rowY[1] + RH)) / 2),
    ambient: {
      steam: [
        { x: learningX + 14, y: bottomY + 24 }, // lobby espresso
        { x: modelX + 22, y: bottomY + 56 }, // deck round-table mug
      ],
      lamps: [
        { x: learningX + 4, y: topY + 64 },
        { x: learningX + 132, y: topY + 64 },
      ],
      leds: [
        { x: modelX + 8, y: topY + 36, w: 12, h: 18 },
        { x: modelX + 106, y: topY + 36, w: 12, h: 18 },
      ],
      crt: { x: animeX + 109, y: bottomY + 85, w: 17, h: 8 },
      dust: { x: learningX + 10, y: topY + 26, w: RW - 20, h: RH - 40 },
      catY: bh - 6,
    },
    lobbySpawn: { x: learningX + 70, y: bottomY + RH - 16 },
  };
}

export interface RoomDef {
  id: string;
  col: number;
  row: number;
  /** Work rooms get a desk + monitor per seat; lounges seat people on furniture. */
  desks: boolean;
  seats: { x: number; y: number }[];
  floor: (ctx: Ctx, x: number, y: number, w: number, h: number) => void;
  /** Big zone rug: body + edge — a lighter tint of the department accent. */
  rugBody: string;
  rugEdge: string;
  /** Signature fixture — a freestanding board drawn centred at the top. */
  fixture: (ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) => void;
  fixtureW: number;
  decor: (ctx: Ctx, accent: string) => void;
}

function grid(cols: number[], rows: number[]): { x: number; y: number }[] {
  const out: { x: number; y: number }[] = [];
  for (const y of rows) for (const x of cols) out.push({ x, y });
  return out;
}

export const ROOMS: RoomDef[] = [
  {
    id: "model",
    col: 0,
    row: 0,
    desks: true,
    seats: grid([12, 44, 76, 108], [66, 100]),
    floor: floorRaised,
    rugBody: "#A9C7BC", // sage-teal tint
    rugEdge: "#8FB5A8",
    fixture: ledWall,
    fixtureW: 64,
    decor: (ctx, accent) => {
      // warm server garden: rack clusters flanking the status board
      serverRack(ctx, 8, 34, 14, 22);
      serverRack(ctx, 24, 34, 14, 22);
      serverRack(ctx, 106, 34, 14, 22);
      serverRack(ctx, 122, 34, 14, 22);
      px(ctx, CABLE_TRAY, 8, 30);
      px(ctx, CABLE_TRAY, 106, 30);
      px(ctx, PRINTER, 44, 36);
      px(ctx, WATER_COOLER, 96, 36);
      cabinet(ctx, 44, 116, 24, 10);
      px(ctx, PLANT, 4, 76);
      px(ctx, PLANT, 122, 116);
      px(ctx, TRASH, 132, 80);
      fill(ctx, 8, 62, 124, 1, shade(accent, 0.55));
    },
  },
  {
    id: "finance",
    col: 1,
    row: 0,
    desks: true,
    seats: grid([12, 44, 76, 108], [66, 100]),
    floor: floorSand,
    rugBody: "#EBCF9A", // mustard tint
    rugEdge: "#D9B878",
    fixture: tickerBoard,
    fixtureW: 72,
    decor: (ctx, accent) => {
      cabinet(ctx, 6, 36, 13, 20);
      cabinet(ctx, 21, 36, 13, 20);
      px(ctx, CLOCK, 66, 38);
      px(ctx, PRINTER, 92, 38);
      cabinet(ctx, 116, 36, 13, 20);
      px(ctx, PLANT, 4, 116);
      px(ctx, PLANT, 60, 116);
      px(ctx, TRASH, 132, 116);
      // brass ticker rail under the board
      fill(ctx, 34, 42, 72, 1, shade(accent, 0.6));
    },
  },
  {
    id: "learning",
    col: 2,
    row: 0,
    desks: true,
    seats: grid([22, 54, 86, 118], [66, 100]),
    floor: floorSand,
    rugBody: "#C4D0AC", // sage tint
    rugEdge: "#ADBE93",
    fixture: whiteboard,
    fixtureW: 68,
    decor: (ctx) => {
      bookshelf(ctx, 3, 36, 16, 22);
      bookshelf(ctx, 121, 36, 16, 22);
      px(ctx, CLOCK, 24, 38);
      floorLamp(ctx, 4, 64);
      floorLamp(ctx, 132, 64);
      px(ctx, PLANT, 4, 116);
      px(ctx, PLANT, 70, 116);
      px(ctx, PLANT, 124, 116);
    },
  },
  {
    id: "deck",
    col: 0,
    row: 1,
    desks: true,
    seats: grid([46, 78, 110], [16, 56, 96]),
    floor: floorSealed,
    rugBody: "#E8B39B", // terracotta tint
    rugEdge: "#DC9A78",
    fixture: kanbanBoard,
    fixtureW: 76,
    decor: (ctx, accent) => {
      // war room: round table + ENH pinboard beside the kanban board
      roundTable(ctx, 22, 60, 13);
      pinboard(ctx, 4, 4, 26, 16, accent);
      px(ctx, LOWTABLE, 22, 116);
      px(ctx, TRASH, 132, 116);
      px(ctx, PLANT, 4, 30);
      fill(ctx, 46, 80, 90, 1, shade(accent, 0.5));
    },
  },
  {
    id: "anime",
    col: 1,
    row: 1,
    desks: false,
    seats: [
      { x: 36, y: 40 },
      { x: 64, y: 40 },
      { x: 104, y: 46 },
      { x: 36, y: 92 },
      { x: 64, y: 92 },
    ],
    floor: (ctx, x, y, w, h) => floorTile(ctx, x, y, w, h, "#E7B9C4", "#EFC2CF", "#D89FAF", 7),
    rugBody: "#EFC2CF",
    rugEdge: "#E5AEBB",
    fixture: artWall,
    fixtureW: 72,
    decor: (ctx) => {
      sofa(ctx, 20, 40, 62, 18, "#DCA98F", "#F2CDBB", "#C08D74");
      sofa(ctx, 20, 92, 62, 18, "#DCA98F", "#F2CDBB", "#C08D74");
      sofa(ctx, 98, 46, 40, 18, "#D4A085", "#ECC0AB", "#B57F66");
      cushion(ctx, 88, 92, "#E8BBA4");
      cushion(ctx, 8, 72, "#ADBE93");
      cushion(ctx, 96, 32, "#E5B44A");
      px(ctx, LOWTABLE, 44, 72);
      // CRT on its stand, bottom right
      px(ctx, CRT_TV, 108, 84);
      px(ctx, PLANT, 4, 16);
      px(ctx, PLANT, 124, 16);
      px(ctx, PLANT, 124, 116);
      checkerStrip(ctx, 26, 120, 100, 4);
    },
  },
  {
    id: "lobby",
    col: 2,
    row: 1,
    desks: false,
    seats: [
      { x: 70, y: 34 },
      { x: 36, y: 72 },
      { x: 110, y: 88 },
    ],
    floor: (ctx, x, y, w, h) => floorTile(ctx, x, y, w, h, "#EFE3C8", "#F6EDD8", "#DCCBAA", 10),
    rugBody: "#E3C9A8",
    rugEdge: "#D3B48C",
    fixture: lobbySign,
    fixtureW: 60,
    decor: (ctx, accent) => {
      // café reception: espresso corner, welcome mat, sofa + bench
      welcomeMat(ctx, 62, 116);
      cabinet(ctx, 6, 40, 16, 18);
      px(ctx, ESPRESSO, 9, 27);
      receptionDesk(ctx, 46, 42, 58, 16, accent);
      sofa(ctx, 100, 88, 38, 18, "#DCA98F", "#F2CDBB", "#C08D74");
      bench(ctx, 22, 88, 40, 8);
      px(ctx, LOWTABLE, 74, 74);
      px(ctx, PLANT, 4, 16);
      px(ctx, PLANT, 124, 16);
      px(ctx, PLANT, 4, 116);
      checkerStrip(ctx, 5, 124, 140, 4);
    },
  },
];

export const ROOM_BY_ID = new Map(ROOMS.map((room) => [room.id, room]));

export function roomRect(room: RoomDef, layout: Layout) {
  return {
    x: layout.colX[room.col],
    y: layout.rowY[room.row],
    w: RW,
    h: RH,
  };
}

/** World position of a seat's character sprite. */
export function seatWorld(room: RoomDef, index: number, layout: Layout) {
  const rect = roomRect(room, layout);
  const seat = room.seats[index % room.seats.length];
  // Overflow seats (more agents than designed slots) queue along the back wall.
  const overflow = Math.floor(index / room.seats.length);
  return {
    x: rect.x + seat.x + overflow * 3,
    y: rect.y + seat.y + overflow * 3,
  };
}

/**
 * Paint the whole plan for a layout: honey walkways, zone floors, rugs,
 * freestanding boards on legs, furniture, walkway greenery, and a desk for
 * every seat the roster actually fills. Static per layout + roster.
 */
export function drawPlan(
  ctx: Ctx,
  layout: Layout,
  accentOf: (roomId: string) => string,
  occupancy: Map<string, number>
) {
  // The one connected walkway surface first; zones paint over their own rects.
  floorPath(ctx, 0, 0, layout.bw, layout.bh);

  for (const room of ROOMS) {
    const zx = layout.colX[room.col];
    const zy = layout.rowY[room.row];
    const accent = accentOf(room.id);

    room.floor(ctx, zx, zy, RW, RH);
    rug(ctx, zx + 6, zy + 6, RW - 12, RH - 12, room.rugBody, room.rugEdge);

    // Freestanding signature board on legs, centred at the top of the zone.
    const fw = Math.min(room.fixtureW, RW - 24);
    const fx = zx + Math.floor((RW - fw) / 2);
    const fy = zy + 3;
    const fh = 18;
    room.fixture(ctx, fx, fy, fw, fh, accent);
    fill(ctx, fx + 3, fy + fh, 2, 5, "#8A5F36");
    fill(ctx, fx + fw - 5, fy + fh, 2, 5, "#8A5F36");
    fill(ctx, fx + 1, fy + fh + 4, fw - 2, 1, "rgba(74,53,39,0.18)");

    ctx.save();
    ctx.translate(zx, zy);
    room.decor(ctx, accent);
    ctx.restore();

    if (room.desks) {
      const filled = occupancy.get(room.id) ?? 0;
      for (let i = 0; i < filled; i++) {
        const world = seatWorld(room, i, layout);
        desk(ctx, world.x + DESK_DX, world.y + DESK_DY, DESK_W, DESK_H);
      }
    }
  }

  // Greenery on the wider walkways so the flex streets read as gardens, not
  // empty paper. Skipped when the corridors are at their minimum width.
  if (layout.corrW >= 34) {
    for (const cx of layout.corrX) {
      const leftEdge = Math.round(cx - layout.corrW / 2) + 2;
      px(ctx, PLANT, leftEdge, layout.rowY[0] + 24);
      px(ctx, PLANT, leftEdge, layout.rowY[0] + RH + 8);
      if (layout.corrW >= 52) {
        bench(ctx, leftEdge, layout.rowY[0] + Math.floor(RH / 2) + 14, 40, 8);
      }
    }
  }
  if (layout.bh - (layout.rowY[1] + RH) >= 16) {
    px(ctx, PLANT, Math.round(layout.corrX[0] - 24), layout.rowY[1] + RH + 4);
    px(ctx, PLANT, Math.round(layout.corrX[1] + 12), layout.rowY[1] + RH + 4);
  }
}

export const DESK_DX = -6;
export const DESK_DY = 13;
export const DESK_W = 30;
export const DESK_H = 10;
export const MON_DX = 13;
export const MON_DY = 5;
