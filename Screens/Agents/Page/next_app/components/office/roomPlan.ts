// The building. Six chambers attached in a 3x2 block with shared walls and
// doorways — one floor plan, not six floating tiles (D15).
//
// All coordinates are *buffer pixels*: the whole plan is 468 x 206, and the
// stage blits it at an integer scale. Room-local layout is written against a
// 150 x 96 room so a room can be moved without touching its furniture.

import {
  bench,
  bookshelf,
  brickWall,
  cabinet,
  checkerStrip,
  confTable,
  desk,
  fill,
  floorConcrete,
  floorRaised,
  floorTile,
  floorWood,
  artWall,
  kanbanBoard,
  ledWall,
  lobbySign,
  panelWall,
  px,
  receptionDesk,
  rug,
  serverRack,
  shade,
  sofa,
  tickerBoard,
  whiteboard,
  CLOCK,
  LOWTABLE,
  PLANT,
  PRINTER,
  TRASH,
  WATER_COOLER,
  type Ctx,
} from "./pixelArt";

export const RW = 150; // room width
export const RH = 96; // room height
export const WALLH = 12; // back-wall band inside each room
export const WALL = 4; // shared wall thickness
export const OUT = 5; // outer shell thickness
export const DOOR = 16; // doorway opening

export const COLS = 3;
export const ROWS = 2;
export const PLAN_W = OUT * 2 + RW * COLS + WALL * (COLS - 1);
export const PLAN_H = OUT * 2 + RH * ROWS + WALL * (ROWS - 1);

// A seat is the character's top-left. The desk and monitor hang off it, so the
// whole workstation moves as one when a seat moves.
export const SEAT_W = 30;
export const SEAT_H = 24;
export const DESK_DX = -6;
export const DESK_DY = 13;
export const DESK_W = 30;
export const DESK_H = 10;
export const MON_DX = 13;
export const MON_DY = 5;

export interface Seat {
  x: number;
  y: number;
}

export interface RoomDef {
  id: string;
  col: number;
  row: number;
  /** Work rooms get a desk + monitor per seat; lounges seat people on furniture. */
  desks: boolean;
  seats: Seat[];
  floor: (ctx: Ctx, x: number, y: number, w: number, h: number) => void;
  wall: (ctx: Ctx, x: number, y: number, w: number, h: number) => void;
  /** Signature back-wall fixture, drawn centred on the wall band. */
  fixture: (ctx: Ctx, x: number, y: number, w: number, h: number, accent: string) => void;
  fixtureW: number;
  decor: (ctx: Ctx, accent: string) => void;
}

// Four columns x three rows of seats is the densest room (Agent Deck, 11 subs).
function grid(cols: number[], rows: number[]): Seat[] {
  const out: Seat[] = [];
  for (const y of rows) for (const x of cols) out.push({ x, y });
  return out;
}

export const ROOMS: RoomDef[] = [
  {
    id: "model",
    col: 0,
    row: 0,
    desks: true,
    seats: grid([12, 46, 80, 114], [42, 69]),
    floor: floorRaised,
    wall: (ctx, x, y, w, h) => panelWall(ctx, x, y, w, h, "#243038"),
    fixture: ledWall,
    fixtureW: 64,
    decor: (ctx, accent) => {
      for (let i = 0; i < 5; i++) serverRack(ctx, 8 + i * 17, 14, 14, 24);
      px(ctx, PRINTER, 100, 16);
      cabinet(ctx, 116, 14, 12, 24);
      px(ctx, WATER_COOLER, 134, 14);
      px(ctx, TRASH, 140, 84);
      fill(ctx, 8, 40, 130, 1, shade(accent, 0.45));
    },
  },
  {
    id: "finance",
    col: 1,
    row: 0,
    desks: true,
    seats: grid([12, 46, 80, 114], [42, 69]),
    floor: floorWood,
    wall: brickWall,
    fixture: tickerBoard,
    fixtureW: 72,
    decor: (ctx) => {
      cabinet(ctx, 6, 14, 13, 24);
      cabinet(ctx, 21, 14, 13, 24);
      px(ctx, CLOCK, 68, 14);
      cabinet(ctx, 118, 14, 13, 24);
      px(ctx, PLANT, 134, 18);
      px(ctx, TRASH, 141, 84);
    },
  },
  {
    id: "learning",
    col: 2,
    row: 0,
    desks: true,
    seats: grid([22, 56, 90, 124], [42, 69]),
    floor: floorWood,
    wall: brickWall,
    fixture: whiteboard,
    fixtureW: 68,
    decor: (ctx) => {
      bookshelf(ctx, 3, 14, 16, 26);
      bookshelf(ctx, 131, 14, 16, 26);
      rug(ctx, 44, 16, 62, 24, "#5a4326", "#3f2f1a");
      confTable(ctx, 48, 22, 54, 14);
      px(ctx, CLOCK, 21, 14);
      px(ctx, PLANT, 4, 84);
    },
  },
  {
    id: "deck",
    col: 0,
    row: 1,
    desks: true,
    seats: grid([12, 46, 80, 114], [14, 41, 68]),
    floor: floorConcrete,
    wall: (ctx, x, y, w, h) => panelWall(ctx, x, y, w, h, "#2a2118"),
    fixture: kanbanBoard,
    fixtureW: 76,
    decor: (ctx) => {
      px(ctx, TRASH, 141, 84);
    },
  },
  {
    id: "anime",
    col: 1,
    row: 1,
    desks: false,
    seats: [
      { x: 30, y: 26 },
      { x: 30, y: 62 },
      { x: 104, y: 34 },
    ],
    floor: (ctx, x, y, w, h) => floorTile(ctx, x, y, w, h, "#4e6f98", "#5c7fa8", "#3f5c80", 7),
    wall: (ctx, x, y, w, h) => panelWall(ctx, x, y, w, h, "#33344a"),
    fixture: artWall,
    fixtureW: 72,
    decor: (ctx) => {
      sofa(ctx, 20, 24, 62, 18, "#c56680", "#f0b3c4", "#a2506a");
      sofa(ctx, 20, 60, 62, 18, "#c56680", "#f0b3c4", "#a2506a");
      sofa(ctx, 98, 32, 40, 18, "#b05c78", "#e6a8bc", "#8f4560");
      px(ctx, LOWTABLE, 44, 44);
      px(ctx, PLANT, 4, 14);
      px(ctx, PLANT, 134, 14);
      px(ctx, PLANT, 134, 74);
      checkerStrip(ctx, 26, 84, 100, 5);
    },
  },
  {
    id: "lobby",
    col: 2,
    row: 1,
    desks: false,
    seats: [
      { x: 69, y: 38 },
      { x: 36, y: 52 },
      { x: 102, y: 52 },
    ],
    floor: (ctx, x, y, w, h) => floorTile(ctx, x, y, w, h, "#c9c4b4", "#d7d1c0", "#b0a892", 10),
    wall: (ctx, x, y, w, h) => panelWall(ctx, x, y, w, h, "#2b2b2b"),
    fixture: lobbySign,
    fixtureW: 60,
    decor: (ctx, accent) => {
      receptionDesk(ctx, 46, 18, 58, 16, accent);
      bench(ctx, 22, 66, 40, 8);
      bench(ctx, 88, 66, 40, 8);
      px(ctx, PLANT, 6, 16);
      px(ctx, PLANT, 132, 16);
      px(ctx, LOWTABLE, 68, 78);
      checkerStrip(ctx, 5, 88, 140, 5);
    },
  },
];

export const ROOM_BY_ID = new Map(ROOMS.map((room) => [room.id, room]));

export function roomRect(room: RoomDef) {
  return {
    x: OUT + room.col * (RW + WALL),
    y: OUT + room.row * (RH + WALL),
    w: RW,
    h: RH,
  };
}

/** World position of a seat's character sprite. */
export function seatWorld(room: RoomDef, index: number) {
  const rect = roomRect(room);
  const seat = room.seats[index % room.seats.length];
  // Overflow seats (more agents than designed slots) queue along the back wall.
  const overflow = Math.floor(index / room.seats.length);
  return {
    x: rect.x + seat.x + overflow * 3,
    y: rect.y + seat.y + overflow * 3,
  };
}

/**
 * Paint the whole plan: floors, walls, doorways, fixtures, furniture, and a
 * desk for every seat the roster actually fills. Static — only re-run when the
 * roster changes.
 */
export function drawPlan(
  ctx: Ctx,
  accentOf: (roomId: string) => string,
  occupancy: Map<string, number>
) {
  const shellDark = "#2a1c12";
  const shellWood = "#3a2a20";

  fill(ctx, 0, 0, PLAN_W, PLAN_H, shellWood);
  fill(ctx, 0, 0, PLAN_W, 2, shellDark);
  fill(ctx, 0, PLAN_H - 2, PLAN_W, 2, shellDark);
  fill(ctx, 0, 0, 2, PLAN_H, shellDark);
  fill(ctx, PLAN_W - 2, 0, 2, PLAN_H, shellDark);

  for (const room of ROOMS) {
    const rect = roomRect(room);
    const accent = accentOf(room.id);

    room.floor(ctx, rect.x, rect.y, rect.w, rect.h);
    room.wall(ctx, rect.x, rect.y, rect.w, WALLH);

    const fw = Math.min(room.fixtureW, rect.w - 16);
    room.fixture(ctx, rect.x + Math.floor((rect.w - fw) / 2), rect.y + 1, fw, WALLH - 3, accent);

    ctx.save();
    ctx.translate(rect.x, rect.y);
    room.decor(ctx, accent);
    ctx.restore();

    if (room.desks) {
      const filled = occupancy.get(room.id) ?? 0;
      for (let i = 0; i < filled; i++) {
        const world = seatWorld(room, i);
        desk(ctx, world.x + DESK_DX, world.y + DESK_DY, DESK_W, DESK_H);
      }
    }
  }

  // Shared interior walls, each with a doorway so the rooms read as connected.
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      const x = OUT + col * (RW + WALL);
      const y = OUT + row * (RH + WALL);

      if (col < COLS - 1) {
        fill(ctx, x + RW, y - OUT, WALL, RH + OUT * 2, shellWood);
        fill(ctx, x + RW, y - OUT, 1, RH + OUT * 2, shellDark);
        fill(ctx, x + RW + WALL - 1, y - OUT, 1, RH + OUT * 2, shellDark);
        fill(ctx, x + RW, y + Math.floor(RH / 2) - DOOR / 2, WALL, DOOR, "#7a5b38");
        fill(ctx, x + RW, y + Math.floor(RH / 2) - DOOR / 2, WALL, 1, shellDark);
        fill(ctx, x + RW, y + Math.floor(RH / 2) + DOOR / 2 - 1, WALL, 1, shellDark);
      }

      if (row < ROWS - 1) {
        fill(ctx, x - OUT, y + RH, RW + OUT * 2, WALL, shellWood);
        fill(ctx, x - OUT, y + RH, RW + OUT * 2, 1, shellDark);
        fill(ctx, x - OUT, y + RH + WALL - 1, RW + OUT * 2, 1, shellDark);
        fill(ctx, x + Math.floor(RW / 2) - DOOR / 2, y + RH, DOOR, WALL, "#7a5b38");
        fill(ctx, x + Math.floor(RW / 2) - DOOR / 2, y + RH, 1, WALL, shellDark);
        fill(ctx, x + Math.floor(RW / 2) + DOOR / 2 - 1, y + RH, 1, WALL, shellDark);
      }
    }
  }
}
