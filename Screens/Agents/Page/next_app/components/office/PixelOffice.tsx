"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ALERT,
  CHAR_H,
  CHAR_W,
  MONITOR,
  P as PALETTE,
  POSE_IDLE,
  POSE_TYPING,
  charPalette,
  fill,
  halo,
  mix,
  px,
  shade,
  shadowBlob,
  type Palette,
} from "./pixelArt";
import {
  MON_DX,
  MON_DY,
  PLAN_H,
  PLAN_W,
  RH,
  ROOMS,
  ROOM_BY_ID,
  RW,
  WALLH,
  drawPlan,
  roomRect,
  seatWorld,
  type RoomDef,
} from "./roomPlan";
import type { AgentView, OfficeAgent, OfficeDepartment } from "../../lib/office";

const MIN_SCALE = 1;
const MAX_SCALE = 16;
const BUBBLE_LINGER_MS = 8000;
// A sub sits dormant (dark monitor, empty chair) until it is tasked, and stays
// on for a grace period afterwards so a burst of work reads as one presence.
const DORMANT_GRACE_MS = 12000;
const POP_MS = 260;

const STATUS_SCREEN: Record<string, string> = {
  idle: "#2f6a72",
  working: "#7fd7e1",
  stuck: "#e0403a",
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

interface Props {
  agents: OfficeAgent[];
  departments: OfficeDepartment[];
  states: Map<string, AgentView>;
  tab: string;
  selected: string | null;
  onSelect: (name: string) => void;
  now: number;
}

export default function PixelOffice({
  agents,
  departments,
  states,
  tab,
  selected,
  onSelect,
  now,
}: Props) {
  const tabRef = useRef(tab);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const planRef = useRef<HTMLCanvasElement | null>(null);
  const sizeRef = useRef({ w: 0, h: 0 });
  const dprRef = useRef(1);

  const [view, setView] = useState<View>({ scale: 2, ox: 0, oy: 0 });
  const viewRef = useRef(view);
  const setViewBoth = useCallback((next: View) => {
    viewRef.current = next;
    setView(next);
  }, []);

  const [hovered, setHovered] = useState<string | null>(null);
  const hoveredRef = useRef<string | null>(null);
  const [follow, setFollow] = useState(true);
  const followRef = useRef(true);
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
    (roomId: string) => departments.find((d) => d.id === roomId)?.color ?? "#8B9099",
    [departments]
  );

  const { placed, byName } = useMemo(() => {
    const buckets = new Map<string, OfficeAgent[]>();
    for (const room of ROOMS) buckets.set(room.id, []);
    for (const agent of agents) {
      const roomId = buckets.has(agent.department) ? agent.department : "deck";
      buckets.get(roomId)!.push(agent);
    }

    const rank = (a: OfficeAgent) => (a.tier === "head" ? 0 : a.tier === "main" ? 1 : 2);
    const list: Placed[] = [];
    const index = new Map<string, Placed>();

    for (const room of ROOMS) {
      const members = buckets
        .get(room.id)!
        .slice()
        .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));

      members.forEach((agent, i) => {
        const world = seatWorld(room, i);
        const entry: Placed = { agent, room, x: world.x, y: world.y };
        list.push(entry);
        index.set(agent.name, entry);
      });
    }

    return { placed: list, byName: index };
  }, [agents]);

  const occupancy = useMemo(() => {
    const counts = new Map<string, number>();
    for (const entry of placed) counts.set(entry.room.id, (counts.get(entry.room.id) ?? 0) + 1);
    return counts;
  }, [placed]);

  // --- static plan buffer ------------------------------------------------

  useEffect(() => {
    const buffer = document.createElement("canvas");
    buffer.width = PLAN_W;
    buffer.height = PLAN_H;
    const ctx = buffer.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    drawPlan(ctx, accentOf, occupancy);
    planRef.current = buffer;
  }, [accentOf, occupancy]);

  // --- camera ------------------------------------------------------------

  const fitAll = useCallback(() => {
    const { w, h } = sizeRef.current;
    if (!w || !h) return;
    const scale = clamp(Math.floor(Math.min(w / PLAN_W, h / PLAN_H)), MIN_SCALE, MAX_SCALE);
    setViewBoth({
      scale,
      ox: Math.round((w - PLAN_W * scale) / 2),
      oy: Math.round((h - PLAN_H * scale) / 2),
    });
  }, [setViewBoth]);

  const focusRoom = useCallback(
    (roomId: string) => {
      const room = ROOM_BY_ID.get(roomId);
      const { w, h } = sizeRef.current;
      if (!room || !w || !h) return;
      const rect = roomRect(room);
      const scale = clamp(
        Math.floor(Math.min(w / (RW + 24), h / (RH + 24))),
        Math.max(MIN_SCALE, 2),
        MAX_SCALE
      );
      setViewBoth({
        scale,
        ox: Math.round(w / 2 - (rect.x + rect.w / 2) * scale),
        oy: Math.round(h / 2 - (rect.y + rect.h / 2) * scale),
      });
    },
    [setViewBoth]
  );

  // Size + first fit.
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
      // back out by dpr. Scale therefore stays an integer at any zoom level.
      sizeRef.current = { w: canvas.width, h: canvas.height };
    };

    measure();
    fitAll();

    const observer = new ResizeObserver(() => {
      measure();
      if (tabRef.current === "all") fitAll();
      else focusRoom(tabRef.current);
    });
    observer.observe(el);
    return () => observer.disconnect();
    // fitAll/focusRoom are stable; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    tabRef.current = tab;
    if (tab === "all") fitAll();
    else focusRoom(tab);
  }, [tab, fitAll, focusRoom]);

  // Follow the newest tasked agent into its room (D15: SSE drives the camera).
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
    if (entry && tabRef.current === "all") focusRoom(entry.room.id);
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
          ox: Math.round(v.ox + dx * dpr),
          oy: Math.round(v.oy + dy * dpr),
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
      const scale = clamp(v.scale + step, MIN_SCALE, MAX_SCALE);
      if (scale === v.scale) return;
      const rect = el.getBoundingClientRect();
      const dpr = dprRef.current;
      const cx = (event.clientX - rect.left) * dpr;
      const cy = (event.clientY - rect.top) * dpr;
      const wx = (cx - v.ox) / v.scale;
      const wy = (cy - v.oy) / v.scale;
      setViewBoth({ scale, ox: Math.round(cx - wx * scale), oy: Math.round(cy - wy * scale) });
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

  // --- render loop -------------------------------------------------------

  const statesRef = useRef(states);
  statesRef.current = states;
  const placedRef = useRef(placed);
  placedRef.current = placed;
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const awakeSince = useRef(new Map<string, number>());

  useEffect(() => {
    let raf = 0;

    const draw = (time: number) => {
      raf = requestAnimationFrame(draw);

      const canvas = canvasRef.current;
      const plan = planRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !plan || !ctx) return;

      const dpr = dprRef.current;
      const v = viewRef.current;
      const clock = Date.now();

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.fillStyle = "#0E0E0E";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Faint survey grid so the space around the building reads as a plan
      // sheet rather than dead black.
      const step = Math.max(12, Math.round(24 * dpr));
      ctx.fillStyle = "#191614";
      for (let gx = 0; gx < canvas.width; gx += step) {
        for (let gy = 0; gy < canvas.height; gy += step) ctx.fillRect(gx, gy, dpr, dpr);
      }

      ctx.setTransform(v.scale, 0, 0, v.scale, v.ox, v.oy);
      ctx.imageSmoothingEnabled = false;
      // Drop shadow under the building.
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      ctx.fillRect(2, 2, PLAN_W, PLAN_H);
      ctx.drawImage(plan, 0, 0);

      for (const entry of placedRef.current) {
        const agentView = statesRef.current.get(entry.agent.name);
        const status = agentView?.status ?? "idle";
        const at = agentView?.at ?? 0;
        const isSub = entry.agent.tier === "sub";
        const awake = !isSub || status !== "idle" || clock - at < DORMANT_GRACE_MS;

        const accent = accentOf(entry.agent.department);

        if (entry.room.desks) {
          const screen = awake ? STATUS_SCREEN[status] : "#1a2226";
          const glow =
            status === "working" && !reducedMotion
              ? mix(screen, "#ffffff", 0.18 + Math.sin(time / 180) * 0.12)
              : screen;
          monitorPalette["$"] = glow;
          px(ctx, MONITOR, entry.x + MON_DX, entry.y + MON_DY, monitorPalette);
        }

        if (!awake) continue;

        let since = awakeSince.current.get(entry.agent.name);
        if (since === undefined) {
          since = time;
          awakeSince.current.set(entry.agent.name, time);
        }
        const pop = reducedMotion ? 1 : clamp((time - since) / POP_MS, 0, 1);
        const rise = Math.round((1 - pop) * 7);

        const phase = entry.x * 0.7 + entry.y * 0.3;
        const bob = reducedMotion
          ? 0
          : status === "working"
            ? Math.round(Math.sin(time / 150 + phase) * 0.6)
            : Math.round(Math.sin(time / 620 + phase) * 0.6);

        const cy = entry.y - rise + bob;
        const pose =
          status === "working" && !reducedMotion && Math.floor(time / 170) % 2 === 0
            ? POSE_TYPING
            : POSE_IDLE;

        const ringColor =
          status === "working" ? accent : status === "stuck" ? "#e0403a" : shade(accent, 0.55);
        const ringAlpha =
          status === "working"
            ? reducedMotion
              ? 0.55
              : 0.35 + Math.sin(time / 260) * 0.2
            : status === "stuck"
              ? 0.6
              : 0.18;
        ctx.globalAlpha = clamp(ringAlpha, 0, 1) * pop;
        halo(ctx, entry.x + CHAR_W / 2, entry.y + CHAR_H - 1, 10, 4, ringColor);
        ctx.globalAlpha = 1;

        shadowBlob(ctx, entry.x, entry.y + CHAR_H - 1, CHAR_W);
        px(ctx, pose, entry.x, cy, paletteFor(accent));

        if (status === "stuck") {
          px(ctx, ALERT, entry.x + CHAR_W - 2, cy - 9);
        }

        if (selectedRef.current === entry.agent.name || hoveredRef.current === entry.agent.name) {
          const box = pickBox(entry);
          const color = selectedRef.current === entry.agent.name ? "#FF7A00" : "#F4F2EE";
          bracket(ctx, box.x, box.y, box.w, box.h, color);
        }
      }

      // Focused room reads bright; the rest of the plan stays legible but back.
      if (tabRef.current !== "all") {
        ctx.fillStyle = "rgba(10,9,8,0.62)";
        for (const room of ROOMS) {
          if (room.id === tabRef.current) continue;
          const rect = roomRect(room);
          ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
        }
      }

      ctx.setTransform(1, 0, 0, 1, 0, 0);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [accentOf, reducedMotion]);

  // Forget pop timers for agents that went dormant so they pop again next time.
  useEffect(() => {
    for (const entry of placed) {
      const agentView = states.get(entry.agent.name);
      const status = agentView?.status ?? "idle";
      const at = agentView?.at ?? 0;
      const isSub = entry.agent.tier === "sub";
      const awake = !isSub || status !== "idle" || now - at < DORMANT_GRACE_MS;
      if (!awake) awakeSince.current.delete(entry.agent.name);
    }
  }, [placed, states, now]);

  // --- DOM overlay (crisp text over the pixel canvas) --------------------

  const dpr = dprRef.current || 1;
  const screenOf = (wx: number, wy: number) => ({
    left: (view.ox + wx * view.scale) / dpr,
    top: (view.oy + wy * view.scale) / dpr,
  });

  const showPlates = view.scale / dpr >= 3;

  // One bubble at a time. With a busy stream every desk would shout at once, so
  // the stage speaks for whoever you picked, else whoever was just tasked.
  const bubbleFor = useMemo(() => {
    if (selected) return selected;
    if (hovered) return hovered;
    let name = "";
    let at = 0;
    for (const [candidate, value] of Array.from(states.entries())) {
      if (!value.text || value.at <= at) continue;
      at = value.at;
      name = candidate;
    }
    return name;
  }, [selected, hovered, states]);

  return (
    <div ref={wrapRef} className="office-stage absolute inset-0">
      <canvas ref={canvasRef} className="office-canvas" />

      <div className="office-overlay">
        {ROOMS.map((room) => {
          const rect = roomRect(room);
          const pos = screenOf(rect.x + 4, rect.y + 2);
          const dept = departments.find((d) => d.id === room.id);
          const dim = tab !== "all" && tab !== room.id;
          return (
            <span
              key={room.id}
              className={`room-plate${dim ? " room-plate-dim" : ""}`}
              style={{ ...pos, color: dept?.color ?? "#8B9099" }}
            >
              {dept?.label ?? room.id}
            </span>
          );
        })}

        {placed.map((entry) => {
          const agentView = states.get(entry.agent.name);
          const status = agentView?.status ?? "idle";
          const at = agentView?.at ?? 0;
          const isSub = entry.agent.tier === "sub";
          const awake = !isSub || status !== "idle" || now - at < DORMANT_GRACE_MS;
          const isSelected = selected === entry.agent.name;
          const isHovered = hovered === entry.agent.name;
          const dim = tab !== "all" && tab !== entry.room.id;
          if (dim && !isSelected) return null;

          const plate =
            isSelected || isHovered || (awake && (showPlates || status !== "idle"));
          const bubbleFresh = now - at < BUBBLE_LINGER_MS;
          const showBubble =
            bubbleFor === entry.agent.name &&
            Boolean(agentView?.text) &&
            awake &&
            (status !== "idle" || bubbleFresh);

          const labelPos = screenOf(
            entry.x + CHAR_W / 2,
            entry.y + (entry.room.desks ? 27 : 19)
          );
          // Agents sitting near a room's back wall would push their bubble up
          // into the room above, so those speak downwards instead.
          const roomTop = roomRect(entry.room).y;
          const bubbleBelow = entry.y - roomTop < 34;
          const bubblePos = screenOf(
            entry.x + CHAR_W / 2,
            bubbleBelow ? entry.y + CHAR_H + 14 : entry.y - 4
          );

          return (
            <span key={entry.agent.name}>
              {plate ? (
                <span
                  className={`desk-label${isSelected ? " desk-label-selected" : ""}${
                    awake ? "" : " desk-label-dormant"
                  }`}
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
            zoomAtCentre(v, -1, sizeRef.current, setViewBoth);
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
            zoomAtCentre(v, 1, sizeRef.current, setViewBoth);
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
  apply: (next: View) => void
) {
  const scale = clamp(v.scale + step, MIN_SCALE, MAX_SCALE);
  if (scale === v.scale) return;
  const cx = size.w / 2;
  const cy = size.h / 2;
  const wx = (cx - v.ox) / v.scale;
  const wy = (cy - v.oy) / v.scale;
  apply({ scale, ox: Math.round(cx - wx * scale), oy: Math.round(cy - wy * scale) });
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
    hit = charPalette(shade(accent, 0.72), "#3a2a1c");
    charPalettes.set(accent, hit);
  }
  return hit;
}

// One mutable palette for the monitor: only the screen key changes per frame,
// so this avoids allocating an object per agent per frame.
const monitorPalette: Palette = { ...PALETTE };
