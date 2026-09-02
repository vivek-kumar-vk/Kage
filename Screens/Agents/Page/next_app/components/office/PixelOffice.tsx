"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import {
  ALERT,
  CAT,
  CHAR_H,
  CHAR_W,
  MONITOR,
  P as PALETTE,
  POSE_IDLE,
  POSE_TYPING,
  POSE_WALK,
  px,
  pxFlipX,
  charPalette,
  fill,
  halo,
  mix,
  puff,
  shade,
  shadowBlob,
  sparkle,
  type Palette,
} from "./pixelArt";
import {
  MON_DX,
  MON_DY,
  RH,
  ROOMS,
  ROOM_BY_ID,
  RW,
  buildLayout,
  drawPlan,
  roomRect,
  seatWorld,
  type Layout,
  type RoomDef,
} from "./roomPlan";
import type { AgentView, OfficeAgent, OfficeDepartment } from "../../lib/office";

const MIN_ZOOM = 2; // never below 2× — below that the floor can't cover a desktop viewport
const MAX_SCALE = 16;
// D18.3: agents exist only while working — done, they stretch, puff and are
// gone. Dormant desks sit empty.
const LEAVE_MS = 6000;
const SPAWN_MS = 700;
const PUFF_MS = 500;
const WALK_SPEED = 0.06; // buffer px per ms
const BUBBLE_LINGER_MS = 8000;
const MAX_CLOUDS = 3; // D18.5 — up to three speakers, most-recent win

// Warm screens: off is pale beige, working glows amber, stuck is coral.
const STATUS_SCREEN: Record<string, string> = {
  off: "#CBB894",
  working: "#E8A13C",
  stuck: "#D95F43",
};

interface View {
  scale: number;
  ox: number;
  oy: number;
}

interface Placed {
  agent: OfficeAgent;
  room: RoomDef;
  x: number;
  y: number;
}

type Pt = { x: number; y: number };

interface Life {
  mode: "materialize" | "walk";
  t0: number;
  path?: Pt[];
  segs?: number[];
  total?: number;
}

function shortName(name: string) {
  return name.replace(/_Agent$/, "");
}

function clamp(v: number, lo: number, hi: number) {
  return v < lo ? lo : v > hi ? hi : v;
}

function pickBox(placed: Placed) {
  return placed.room.desks
    ? { x: placed.x - 8, y: placed.y - 2, w: 32, h: 28 }
    : { x: placed.x - 6, y: placed.y - 3, w: 24, h: 24 };
}

/** Walk-in route from the lobby café to a seat, along the honey walkways. */
function walkPath(from: Pt, to: Pt, targetRow: number, layout: Layout): Pt[] {
  const corr =
    Math.abs(to.x - layout.corrX[0]) <= Math.abs(to.x - layout.corrX[1]) ? 0 : 1;
  const cx = layout.corrX[corr];
  if (targetRow === 0) {
    return [
      from,
      { x: from.x, y: layout.ringBottomY },
      { x: cx, y: layout.ringBottomY },
      { x: cx, y: layout.midY },
      { x: to.x, y: layout.midY },
      to,
    ];
  }
  return [from, { x: from.x, y: layout.ringBottomY }, { x: to.x, y: layout.ringBottomY }, to];
}

function measurePath(path: Pt[]) {
  const segs: number[] = [];
  let total = 0;
  for (let i = 1; i < path.length; i++) {
    const len = Math.abs(path[i].x - path[i - 1].x) + Math.abs(path[i].y - path[i - 1].y);
    segs.push(len);
    total += len;
  }
  return { segs, total };
}

function pointAt(path: Pt[], segs: number[], dist: number): Pt {
  let acc = 0;
  for (let i = 0; i < segs.length; i++) {
    if (dist <= acc + segs[i] || i === segs.length - 1) {
      const t = segs[i] === 0 ? 0 : clamp((dist - acc) / segs[i], 0, 1);
      return {
        x: path[i].x + (path[i + 1].x - path[i].x) * t,
        y: path[i].y + (path[i + 1].y - path[i].y) * t,
      };
    }
    acc += segs[i];
  }
  return path[path.length - 1];
}

interface Props {
  agents: OfficeAgent[];
  departments: OfficeDepartment[];
  states: Map<string, AgentView>;
  /** Agents whose task was handed over by another zone's agent — they walk in. */
  walkIns: Set<string>;
  selected: string | null;
  onSelect: (name: string) => void;
  now: number;
}

export default function PixelOffice({
  agents,
  departments,
  states,
  walkIns,
  selected,
  onSelect,
  now,
}: Props) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const planRef = useRef<HTMLCanvasElement | null>(null);
  const sizeRef = useRef({ w: 0, h: 0 });
  const dprRef = useRef(1);

  const [view, setView] = useState<View>({ scale: 2, ox: 0, oy: 0 });
  const viewRef = useRef(view);
  // The responsive layout owns the zoom floor: fit scale = cover scale, and
  // pan is clamped so the space beyond the floor can never be shown (D18.7).
  const layoutRef = useRef<Layout | null>(null);
  const fitScaleRef = useRef(MIN_ZOOM);
  const setViewBoth = useCallback((next: View) => {
    const l = layoutRef.current;
    const size = sizeRef.current;
    const scale = clamp(Math.round(next.scale), fitScaleRef.current, MAX_SCALE);
    const slackX = l ? size.w - l.bw * scale : 0;
    const slackY = l ? size.h - l.bh * scale : 0;
    const nextView: View = {
      scale,
      ox: slackX >= 0 ? Math.round(slackX / 2) : clamp(Math.round(next.ox), slackX, 0),
      oy: slackY >= 0 ? Math.round(slackY / 2) : clamp(Math.round(next.oy), slackY, 0),
    };
    viewRef.current = nextView;
    setView(nextView);
  }, []);

  // The responsive plan layout: rebuilt from the viewport on every resize.
  const [layout, setLayout] = useState<Layout | null>(null);

  const [hovered, setHovered] = useState<string | null>(null);
  const hoveredRef = useRef<string | null>(null);
  // Fit-all is the resting camera (D16.2); Follow is opt-in per session.
  const [follow, setFollow] = useState(false);
  const followRef = useRef(false);
  useEffect(() => {
    followRef.current = follow;
  }, [follow]);

  const [reducedMotion] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  // --- roster -> seats ---------------------------------------------------

  const accentOf = useCallback(
    (roomId: string) => departments.find((d) => d.id === roomId)?.color ?? "#A08762",
    [departments]
  );

  const { placed, byName } = useMemo(() => {
    const layout = layoutRef.current;
    const buckets = new Map<string, OfficeAgent[]>();
    for (const room of ROOMS) buckets.set(room.id, []);
    for (const agent of agents) {
      const roomId = buckets.has(agent.department) ? agent.department : "deck";
      buckets.get(roomId)!.push(agent);
    }

    const rank = (a: OfficeAgent) => (a.tier === "head" ? 0 : a.tier === "main" ? 1 : 2);
    const list: Placed[] = [];
    const index = new Map<string, Placed>();
    if (!layout) return { placed: list, byName: index };

    for (const room of ROOMS) {
      const members = buckets
        .get(room.id)!
        .slice()
        .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));

      members.forEach((agent, i) => {
        const world = seatWorld(room, i, layout);
        const entry: Placed = { agent, room, x: world.x, y: world.y };
        list.push(entry);
        index.set(agent.name, entry);
      });
    }

    return { placed: list, byName: index };
  }, [agents, layout]);

  const occupancy = useMemo(() => {
    const counts = new Map<string, number>();
    for (const entry of placed) counts.set(entry.room.id, (counts.get(entry.room.id) ?? 0) + 1);
    return counts;
  }, [placed]);

  // --- static plan buffer (rebuilt per responsive layout) ----------------

  useEffect(() => {
    if (!layout) return;
    const buffer = document.createElement("canvas");
    buffer.width = layout.bw;
    buffer.height = layout.bh;
    const ctx = buffer.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    drawPlan(ctx, layout, accentOf, occupancy);
    planRef.current = buffer;
  }, [layout, accentOf, occupancy]);

  // --- camera ------------------------------------------------------------

  const fitAll = useCallback(() => {
    const l = layoutRef.current;
    if (!l) return;
    setViewBoth({ scale: l.scale, ox: 0, oy: 0 });
  }, [setViewBoth]);

  const focusRoom = useCallback(
    (roomId: string) => {
      const l = layoutRef.current;
      const room = ROOM_BY_ID.get(roomId);
      const { w, h } = sizeRef.current;
      if (!l || !room || !w || !h) return;
      const rect = roomRect(room, l);
      const scale = clamp(
        Math.floor(Math.min(w / (RW + 24), h / (RH + 24))),
        Math.max(MIN_ZOOM, 2),
        MAX_SCALE
      );
      setViewBoth({
        scale,
        ox: w / 2 - (rect.x + rect.w / 2) * scale,
        oy: h / 2 - (rect.y + rect.h / 2) * scale,
      });
    },
    [setViewBoth]
  );

  // Size + responsive layout + first fit. Re-runs on every resize.
  useEffect(() => {
    const el = wrapRef.current;
    const canvas = canvasRef.current;
    if (!el || !canvas) return;

    const measure = () => {
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      dprRef.current = dpr;
      const w = el.clientWidth;
      const h = el.clientHeight;
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      // Everything downstream works in device pixels; the DOM overlay divides
      // back out by dpr. One art pixel stays an exact square of device pixels.
      sizeRef.current = { w: canvas.width, h: canvas.height };
      const l = buildLayout(canvas.width, canvas.height);
      layoutRef.current = l;
      fitScaleRef.current = l.scale;
      setLayout(l);
    };

    measure();
    fitAll();

    const observer = new ResizeObserver(() => {
      measure();
      fitAll();
    });
    observer.observe(el);
    return () => observer.disconnect();
    // fitAll is stable; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Follow the newest tasked agent into its zone.
  const lastFollowedRef = useRef(0);
  useEffect(() => {
    if (!followRef.current) return;
    let bestName = "";
    let bestAt = 0;
    for (const [name, value] of Array.from(states.entries())) {
      if (value.status === "idle") continue;
      if (value.at > bestAt) {
        bestAt = value.at;
        bestName = name;
      }
    }
    if (!bestName || bestAt <= lastFollowedRef.current) return;
    lastFollowedRef.current = bestAt;
    const entry = byName.get(bestName);
    if (entry) focusRoom(entry.room.id);
  }, [states, byName, focusRoom]);

  // --- pointer -----------------------------------------------------------

  const toWorld = useCallback((clientX: number, clientY: number) => {
    const el = wrapRef.current;
    if (!el) return { x: 0, y: 0 };
    const rect = el.getBoundingClientRect();
    const v = viewRef.current;
    const dpr = dprRef.current;
    return {
      x: ((clientX - rect.left) * dpr - v.ox) / v.scale,
      y: ((clientY - rect.top) * dpr - v.oy) / v.scale,
    };
  }, []);

  const hitTest = useCallback(
    (wx: number, wy: number) => {
      for (const entry of placed) {
        const box = pickBox(entry);
        if (wx >= box.x && wx <= box.x + box.w && wy >= box.y && wy <= box.y + box.h) {
          return entry;
        }
      }
      return null;
    },
    [placed]
  );

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    let dragging = false;
    let moved = 0;
    let lastX = 0;
    let lastY = 0;
    let pointerId = -1;

    const onDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      dragging = true;
      moved = 0;
      lastX = event.clientX;
      lastY = event.clientY;
      pointerId = event.pointerId;
      el.setPointerCapture(pointerId);
    };

    const onMove = (event: PointerEvent) => {
      if (dragging) {
        const dx = event.clientX - lastX;
        const dy = event.clientY - lastY;
        moved += Math.abs(dx) + Math.abs(dy);
        lastX = event.clientX;
        lastY = event.clientY;
        const v = viewRef.current;
        const dpr = dprRef.current;
        setViewBoth({
          scale: v.scale,
          ox: v.ox + dx * dpr,
          oy: v.oy + dy * dpr,
        });
        return;
      }
      const world = toWorld(event.clientX, event.clientY);
      const hit = hitTest(world.x, world.y);
      const name = hit ? hit.agent.name : null;
      if (name !== hoveredRef.current) {
        hoveredRef.current = name;
        setHovered(name);
        el.style.cursor = name ? "pointer" : "grab";
      }
    };

    const onUp = (event: PointerEvent) => {
      if (!dragging) return;
      dragging = false;
      if (pointerId >= 0 && el.hasPointerCapture(pointerId)) el.releasePointerCapture(pointerId);
      pointerId = -1;
      if (moved > 5) return; // a drag, not a click
      const world = toWorld(event.clientX, event.clientY);
      const hit = hitTest(world.x, world.y);
      onSelect(hit ? hit.agent.name : "");
    };

    const onLeave = () => {
      if (hoveredRef.current !== null) {
        hoveredRef.current = null;
        setHovered(null);
      }
    };

    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const v = viewRef.current;
      const step = event.deltaY > 0 ? -1 : 1;
      const scale = clamp(v.scale + step, fitScaleRef.current, MAX_SCALE);
      if (scale === v.scale) return;
      const rect = el.getBoundingClientRect();
      const dpr = dprRef.current;
      const cx = (event.clientX - rect.left) * dpr;
      const cy = (event.clientY - rect.top) * dpr;
      const wx = (cx - v.ox) / v.scale;
      const wy = (cy - v.oy) / v.scale;
      setViewBoth({ scale, ox: cx - wx * scale, oy: cy - wy * scale });
    };

    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
    el.addEventListener("pointerleave", onLeave);
    el.addEventListener("wheel", onWheel, { passive: false });
    el.style.cursor = "grab";

    return () => {
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerup", onUp);
      el.removeEventListener("pointercancel", onUp);
      el.removeEventListener("pointerleave", onLeave);
      el.removeEventListener("wheel", onWheel);
    };
  }, [hitTest, onSelect, setViewBoth, toWorld]);

  // --- lifecycle ---------------------------------------------------------

  const statesRef = useRef(states);
  statesRef.current = states;
  const placedRef = useRef(placed);
  placedRef.current = placed;
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const walkInsRef = useRef(walkIns);
  walkInsRef.current = walkIns;
  const lifeRef = useRef(new Map<string, Life>());

  // --- render loop -------------------------------------------------------

  useEffect(() => {
    let raf = 0;

    const draw = (time: number) => {
      raf = requestAnimationFrame(draw);

      const canvas = canvasRef.current;
      const plan = planRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !plan || !ctx) return;

      const v = viewRef.current;
      const clock = Date.now();
      const layout = layoutRef.current;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.imageSmoothingEnabled = false;
      // The page backdrop IS the walkway honey — the floor reads full-bleed
      // with no letterbox (D16.2).
      ctx.fillStyle = "#DBA768";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const dpr = dprRef.current;
      const dot = Math.max(16, Math.round(26 * dpr));
      const grain = Math.max(2, Math.round(dpr));
      ctx.fillStyle = "#D2A05F";
      for (let gx = dot / 2; gx < canvas.width; gx += dot) {
        for (let gy = dot / 2; gy < canvas.height; gy += dot) {
          ctx.fillRect(gx, gy, grain, grain);
        }
      }

      ctx.setTransform(v.scale, 0, 0, v.scale, v.ox, v.oy);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(plan, 0, 0);

      // --- ambient life (D18.4) -----------------------------------------
      const amb = layout?.ambient;
      if (!reducedMotion && amb) {
        // lamp pools in the library
        for (const lamp of amb.lamps) {
          ctx.globalAlpha = 0.14 + Math.sin(time / 900 + lamp.x) * 0.04;
          ctx.fillStyle = "#F4D488";
          ctx.fillRect(lamp.x - 14, lamp.y + 4, 28, 12);
          ctx.fillRect(lamp.x - 10, lamp.y, 20, 18);
          ctx.fillRect(lamp.x - 6, lamp.y - 4, 12, 24);
          ctx.globalAlpha = 1;
        }
        // dust motes drifting through the light
        ctx.fillStyle = "#FFF6DC";
        for (let i = 0; i < 12; i++) {
          const bx = amb.dust.x + ((i * 67) % amb.dust.w);
          const by = amb.dust.y + ((i * 31) % amb.dust.h);
          const dx = Math.sin(time / 1700 + i) * 6;
          const dy = Math.cos(time / 2300 + i * 1.7) * 4;
          ctx.globalAlpha = 0.22 + (i % 3) * 0.06;
          ctx.fillRect(Math.round(bx + dx), Math.round(by + dy), 1, 1);
        }
        ctx.globalAlpha = 1;
        // coffee steam
        for (const [ai, anchor] of amb.steam.entries()) {
          for (let k = 0; k < 3; k++) {
            const prog = (time / 1500 + k / 3 + ai * 0.2) % 1;
            const sx = anchor.x + Math.sin(prog * 6 + k) * 2.5;
            const sy = anchor.y - prog * 13;
            ctx.globalAlpha = (1 - prog) * 0.45;
            ctx.fillStyle = k % 2 ? "#FFF6DC" : "#E8CFA0";
            ctx.fillRect(Math.round(sx), Math.round(sy), prog > 0.6 ? 1 : 2, 2);
          }
        }
        ctx.globalAlpha = 1;
        // amber LED flicker on the server racks
        for (const [ri, rack] of amb.leds.entries()) {
          const idx = Math.floor(time / 700 + ri * 3) % 12;
          ctx.fillStyle = "#FFD98E";
          ctx.fillRect(rack.x + (idx % 4) * 3, rack.y + Math.floor(idx / 4) * 4, 2, 1);
        }
        // CRT scanline shimmer
        const sy = amb.crt.y + ((time / 300) % amb.crt.h);
        ctx.globalAlpha = 0.25;
        ctx.fillStyle = "#FFF6DC";
        ctx.fillRect(amb.crt.x + 1, Math.round(sy), amb.crt.w, 1);
        ctx.globalAlpha = 1;
        // the office cat patrols the bottom walkway
        const cycle = (time / 1000) % 26;
        const d = cycle < 13 ? cycle / 13 : 2 - cycle / 13;
        const catX = 30 + d * (layout.bw - 70);
        const dir = cycle < 13 ? 1 : -1;
        const catY = amb.catY + Math.round(Math.sin(time / 160) * 0.8);
        if (dir > 0) px(ctx, CAT, Math.round(catX), catY);
        else pxFlipX(ctx, CAT, Math.round(catX), catY);
      }

      // --- agents --------------------------------------------------------
      const life = lifeRef.current;

      for (const entry of placedRef.current) {
        const agentView = statesRef.current.get(entry.agent.name);
        const status = agentView?.status ?? "idle";
        const at = agentView?.at ?? 0;
        const working = status === "working";
        const stuck = status === "stuck";
        const leaving = !working && !stuck;
        const accent = accentOf(entry.agent.department);

        // Monitors sit on every desk; only the living ones light up.
        if (entry.room.desks) {
          const screen = working
            ? STATUS_SCREEN.working
            : stuck
              ? STATUS_SCREEN.stuck
              : STATUS_SCREEN.off;
          const glow =
            working && !reducedMotion
              ? mix(screen, "#FFE9AE", 0.18 + Math.sin(time / 180) * 0.12)
              : screen;
          monitorPalette["$"] = glow;
          px(ctx, MONITOR, entry.x + MON_DX, entry.y + MON_DY, monitorPalette);
        }

        if (status === "idle" && clock - at >= LEAVE_MS) {
          life.delete(entry.agent.name);
          continue;
        }
        if (!agentView) continue;

        let record = life.get(entry.agent.name);
        if (!record) {
          const mode: Life["mode"] = walkInsRef.current.has(entry.agent.name)
            ? "walk"
            : "materialize";
          record = { mode, t0: clock };
          if (mode === "walk" && layout) {
            const path = walkPath(layout.lobbySpawn, { x: entry.x, y: entry.y }, entry.room.row, layout);
            const { segs, total } = measurePath(path);
            record.path = path;
            record.segs = segs;
            record.total = total;
          }
          life.set(entry.agent.name, record);
        }

        let cx = entry.x;
        let cy = entry.y;
        let alpha = 1;
        let pose = POSE_IDLE;
        let walking = false;

        if (record.mode === "walk" && record.path && record.segs && record.total) {
          const dur = clamp(record.total / WALK_SPEED, 2500, 8000);
          const prog = reducedMotion ? 1 : clamp((clock - record.t0) / dur, 0, 1);
          const pt = pointAt(record.path, record.segs, prog * record.total);
          cx = Math.round(pt.x);
          cy = Math.round(pt.y);
          walking = prog < 1;
          if (walking) {
            pose = !reducedMotion && Math.floor(time / 160) % 2 === 0 ? POSE_WALK : POSE_IDLE;
          } else if (working && !reducedMotion && Math.floor(time / 170) % 2 === 0) {
            pose = POSE_TYPING;
          }
        } else {
          // materialize: sparkle + fade in
          const spawnProg = reducedMotion ? 1 : clamp((clock - record.t0) / SPAWN_MS, 0, 1);
          alpha = spawnProg;
          cy -= Math.round((1 - spawnProg) * 6);
          if (!reducedMotion && spawnProg < 1) {
            sparkle(ctx, cx + CHAR_W / 2, cy + CHAR_H / 2, spawnProg, accent);
          }
          if (working && !reducedMotion && Math.floor(time / 170) % 2 === 0) pose = POSE_TYPING;
        }

        // leaving: stretch up + fade, with a parting puff
        if (leaving) {
          const leaveProg = clamp((clock - at) / LEAVE_MS, 0, 1);
          alpha *= 1 - leaveProg;
          cy -= Math.round(leaveProg * 8);
          if (!reducedMotion) {
            const puffProg = clamp((clock - at) / PUFF_MS, 0, 1);
            if (puffProg < 1) puff(ctx, cx + CHAR_W / 2, cy + CHAR_H, puffProg, shade(accent, 1.3));
          }
        }

        const phase = entry.x * 0.7 + entry.y * 0.3;
        const bob = reducedMotion
          ? 0
          : walking
            ? Math.round(Math.sin(time / 90 + phase) * 1)
            : working
              ? Math.round(Math.sin(time / 150 + phase) * 0.6)
              : Math.round(Math.sin(time / 620 + phase) * 0.6);

        ctx.globalAlpha = clamp(alpha, 0, 1);

        if (!leaving && (working || stuck)) {
          const ringColor = working ? accent : "#D95F43";
          const ringAlpha = reducedMotion ? 0.5 : 0.35 + Math.sin(time / 260) * 0.2;
          ctx.globalAlpha = clamp(ringAlpha, 0, 1) * alpha;
          halo(ctx, cx + CHAR_W / 2, cy + CHAR_H - 1, 10, 4, ringColor);
          ctx.globalAlpha = clamp(alpha, 0, 1);
        }

        if (!leaving) shadowBlob(ctx, cx, cy + CHAR_H - 1, CHAR_W);
        px(ctx, pose, cx, cy + bob, paletteFor(accent));

        if (stuck) {
          px(ctx, ALERT, cx + CHAR_W - 2, cy + bob - 9);
        }

        ctx.globalAlpha = 1;

        if (selectedRef.current === entry.agent.name || hoveredRef.current === entry.agent.name) {
          const box = pickBox(entry);
          const color = selectedRef.current === entry.agent.name ? "#C96F4A" : "#4A3527";
          bracket(ctx, box.x, box.y, box.w, box.h, color);
        }
      }

      ctx.setTransform(1, 0, 0, 1, 0, 0);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [accentOf, reducedMotion, layout]);

  // Clean lifecycle records for agents the roster no longer knows.
  useEffect(() => {
    const known = new Set(placed.map((entry) => entry.agent.name));
    for (const name of Array.from(lifeRef.current.keys())) {
      if (!known.has(name)) lifeRef.current.delete(name);
    }
  }, [placed]);

  // --- DOM overlay (crisp text over the pixel canvas) --------------------

  const dpr = dprRef.current || 1;
  const screenOf = (wx: number, wy: number) => ({
    left: (view.ox + wx * view.scale) / dpr,
    top: (view.oy + wy * view.scale) / dpr,
  });

  const showPlates = view.scale / dpr >= 3;

  // D18.5: up to three clouds, most-recent first; the selected agent always
  // keeps the mic while visible.
  const cloudNames = useMemo(() => {
    const candidates: { name: string; at: number }[] = [];
    for (const [name, value] of Array.from(states.entries())) {
      if (!value.text || value.status === "idle") continue;
      candidates.push({ name, at: value.at });
    }
    candidates.sort((a, b) => {
      const aSel = a.name === selected ? 1 : 0;
      const bSel = b.name === selected ? 1 : 0;
      return bSel - aSel || b.at - a.at;
    });
    return new Set(candidates.slice(0, MAX_CLOUDS).map((c) => c.name));
  }, [states, selected]);

  return (
    <div ref={wrapRef} className="office-stage absolute inset-0">
      <canvas ref={canvasRef} className="office-canvas" />

      <div className="office-overlay">
        {layout
          ? ROOMS.map((room) => {
              const rect = roomRect(room, layout);
              const pos = screenOf(rect.x + 6, rect.y - 1);
              const dept = departments.find((d) => d.id === room.id);
              return (
                <button
                  key={room.id}
                  type="button"
                  className="room-plate"
                  style={
                    { ...pos, "--plate-accent": dept?.color ?? "#A08762" } as CSSProperties
                  }
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={() => focusRoom(room.id)}
                  title={`Focus ${dept?.label ?? room.id}`}
                >
                  {dept?.label ?? room.id}
                </button>
              );
            })
          : null}

        {placed.map((entry) => {
          const agentView = states.get(entry.agent.name);
          const status = agentView?.status ?? "idle";
          const at = agentView?.at ?? 0;
          const clock = now;
          const visible = status !== "idle" || clock - at < LEAVE_MS;
          if (!visible) return null;

          const isSelected = selected === entry.agent.name;
          const isHovered = hovered === entry.agent.name;
          const showPlate = isSelected || isHovered || showPlates || status !== "idle";
          const bubbleFresh = clock - at < BUBBLE_LINGER_MS;
          const showBubble =
            cloudNames.has(entry.agent.name) &&
            Boolean(agentView?.text) &&
            (status !== "idle" || bubbleFresh);

          const labelPos = screenOf(
            entry.x + CHAR_W / 2,
            entry.y + (entry.room.desks ? 27 : 19)
          );
          // Agents sitting near a zone's top edge push their bubble down instead.
          const roomTop = layout ? roomRect(entry.room, layout).y : 0;
          const bubbleBelow = entry.y - roomTop < 34;
          const bubblePos = screenOf(
            entry.x + CHAR_W / 2,
            bubbleBelow ? entry.y + CHAR_H + 14 : entry.y - 4
          );

          return (
            <span key={entry.agent.name}>
              {showPlate ? (
                <span
                  className={`desk-label${isSelected ? " desk-label-selected" : ""}`}
                  style={labelPos}
                >
                  {shortName(entry.agent.name)}
                </span>
              ) : null}

              {showBubble && agentView?.text ? (
                <span
                  className={`pixel-bubble${bubbleBelow ? " pixel-bubble-below" : ""}`}
                  style={bubblePos}
                >
                  {agentView.sim ? <span className="sim-tag">SIM</span> : null}
                  {agentView.text}
                </span>
              ) : null}
            </span>
          );
        })}
      </div>

      <div className="office-controls">
        <button
          type="button"
          onClick={() => {
            const v = viewRef.current;
            zoomAtCentre(v, -1, sizeRef.current, fitScaleRef.current, setViewBoth);
          }}
          aria-label="Zoom out"
        >
          −
        </button>
        <span className="office-zoom num">{view.scale}×</span>
        <button
          type="button"
          onClick={() => {
            const v = viewRef.current;
            zoomAtCentre(v, 1, sizeRef.current, fitScaleRef.current, setViewBoth);
          }}
          aria-label="Zoom in"
        >
          +
        </button>
        <button type="button" onClick={fitAll} aria-label="Fit whole floor">
          Fit
        </button>
        <button
          type="button"
          className={follow ? "is-on" : undefined}
          onClick={() => setFollow((value) => !value)}
          title="Pan to whichever agent was just tasked"
        >
          Follow
        </button>
      </div>
    </div>
  );
}

function zoomAtCentre(
  v: View,
  step: number,
  size: { w: number; h: number },
  minScale: number,
  apply: (next: View) => void
) {
  const scale = clamp(v.scale + step, minScale, MAX_SCALE);
  if (scale === v.scale) return;
  // Keep the canvas centre anchored while zooming.
  const cx = size.w / 2;
  const cy = size.h / 2;
  const wx = (cx - v.ox) / v.scale;
  const wy = (cy - v.oy) / v.scale;
  apply({ scale, ox: cx - wx * scale, oy: cy - wy * scale });
}

function bracket(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  color: string
) {
  const arm = 5;
  fill(ctx, x, y, arm, 1, color);
  fill(ctx, x, y, 1, arm, color);
  fill(ctx, x + w - arm, y, arm, 1, color);
  fill(ctx, x + w - 1, y, 1, arm, color);
  fill(ctx, x, y + h - arm, 1, arm, color);
  fill(ctx, x, y + h - 1, arm, 1, color);
  fill(ctx, x + w - 1, y + h - arm, 1, arm, color);
  fill(ctx, x + w - arm, y + h - 1, arm, 1, color);
}

const charPalettes = new Map<string, Palette>();

/** Recolour the character sprite from the department accent; cached per colour. */
function paletteFor(accent: string): Palette {
  let hit = charPalettes.get(accent);
  if (!hit) {
    hit = charPalette(shade(accent, 0.78), "#4A3527");
    charPalettes.set(accent, hit);
  }
  return hit;
}

// One mutable palette for the monitor: only the screen key changes per frame,
// so this avoids allocating an object per agent per frame.
const monitorPalette: Palette = { ...PALETTE };
