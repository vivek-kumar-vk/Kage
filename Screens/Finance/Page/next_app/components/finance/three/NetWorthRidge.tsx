"use client";
// Net-worth history as a glowing gold 3D terrain strip (the "3D ridge").
// Draws itself in on load, then breathes; drag to tilt; the 12-month projection
// continues as a dashed pulsing tail and a pulsing ring marks today.
// Falls back to the mockup's static gold SVG (same real data) when WebGL is
// missing or the user prefers reduced motion.
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { Line as DreiLine, Html } from "@react-three/drei";
import * as THREE from "three";
import { inr } from "@/lib/format";

export interface RidgeProps {
  trend: number[]; // actual net-worth points (solid)
  /** Same length as `trend` — a date per point, for the hover readout. */
  trendLabels?: string[];
  projection: number[]; // 12-month projected points (dashed tail)
  /** Same length as `projection` — a month per point, for the hover readout. */
  projectionLabels?: string[];
  /** Benchmark, already rebased onto net worth's own units and aligned
   * point-for-point with `trend` (same length; null = no snapshot that
   * month — a gap, never interpolated). Omitted or too short => no line. */
  benchmark?: (number | null)[];
}

/** Which renderer actually drew — the card labels itself from this. */
export type RidgeMode = "three" | "svg";

const W = 10; // scene width
const H = 2.6; // scene height

function normalize(values: number[]): { x: number; y: number }[] {
  const all = values.filter((v) => Number.isFinite(v));
  if (all.length < 2) return [];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || 1;
  return values.map((v, i) => ({
    x: (i / (values.length - 1)) * W,
    y: ((Number.isFinite(v) ? v : min) - min) / range * H,
  }));
}

/** Trend and its benchmark overlay, mapped through ONE shared min/max so
 * neither line is independently rescaled to fill the box — two series
 * scaled apart from each other would look like they track regardless of
 * what the numbers say (D28, AGENTS.md). `x` uses trend's own spacing
 * (trend.length - 1), since the benchmark is aligned point-for-point with
 * it, not appended after it in time. */
function normalizeWithBenchmark(
  trend: number[],
  benchmark: (number | null)[] | undefined
): { solid: { x: number; y: number }[]; benchmarkPoints: ({ x: number; y: number } | null)[] } {
  const finiteTrend = trend.filter((v) => Number.isFinite(v));
  const finiteBenchmark = (benchmark ?? []).filter(
    (v): v is number => v !== null && Number.isFinite(v)
  );

  if (finiteTrend.length < 2) return { solid: [], benchmarkPoints: [] };
  if (finiteBenchmark.length === 0 || !benchmark) {
    return { solid: normalize(trend), benchmarkPoints: [] };
  }

  const all = [...finiteTrend, ...finiteBenchmark];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || 1;
  const xOf = (i: number) => (i / (trend.length - 1)) * W;
  const yOf = (v: number) => ((v - min) / range) * H;

  const solid = trend.map((v, i) => ({
    x: xOf(i),
    y: yOf(Number.isFinite(v) ? v : min),
  }));
  const benchmarkPoints = benchmark.map((v, i) =>
    v === null || !Number.isFinite(v) ? null : { x: xOf(i), y: yOf(v) }
  );
  return { solid, benchmarkPoints };
}

/** Split a point-per-index array (with gaps) into contiguous runs — a
 * missing month breaks the line rather than being interpolated across. */
function runsOf(points: ({ x: number; y: number } | null)[]): { x: number; y: number }[][] {
  const runs: { x: number; y: number }[][] = [];
  let current: { x: number; y: number }[] = [];
  for (const p of points) {
    if (p) {
      current.push(p);
    } else if (current.length) {
      runs.push(current);
      current = [];
    }
  }
  if (current.length) runs.push(current);
  return runs.filter((run) => run.length >= 2);
}

interface RidgePoint {
  x: number;
  y: number;
  value: number;
  label?: string;
}

/** Nearest-point readout on hover — no drag, no tilt, just a value. */
function useHoverReadout(points: RidgePoint[]) {
  const [hovered, setHovered] = useState<RidgePoint | null>(null);

  const handlers = {
    onPointerMove: (e: ThreeEvent<PointerEvent>) => {
      if (points.length === 0) return;
      let nearest = points[0];
      let best = Math.abs(points[0].x - e.point.x);
      for (const p of points) {
        const d = Math.abs(p.x - e.point.x);
        if (d < best) {
          best = d;
          nearest = p;
        }
      }
      setHovered(nearest);
    },
    onPointerLeave: () => setHovered(null),
  };

  return { hovered, handlers };
}

function formatMonthLabel(label: string): string {
  // "YYYY-MM" (projection) or a full date (trend) — both parse fine here.
  const d = new Date(label.length <= 7 ? `${label}-01` : label);
  if (Number.isNaN(d.getTime())) return label;
  return d.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

function RidgeScene({
  trend,
  trendLabels,
  projection,
  projectionLabels,
  benchmark,
  onFirstFrame,
}: RidgeProps & { onFirstFrame: () => void }) {
  const { solid, benchmarkPoints } = useMemo(
    () => normalizeWithBenchmark(trend, benchmark),
    [trend, benchmark]
  );
  const benchmarkRuns = useMemo(() => runsOf(benchmarkPoints), [benchmarkPoints]);
  const full = useMemo(
    () => normalize([...trend, ...projection.map((v, i) => (i === 0 && trend.length ? trend[trend.length - 1] : v))]),
    [trend, projection],
  );
  const tail = projection.length && solid.length
    ? full.slice(Math.max(solid.length - 1, 0))
    : [];

  const groupRef = useRef<THREE.Group>(null);
  const tailRef = useRef<THREE.Group>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const fillRef = useRef<THREE.Mesh>(null);
  const progress = useRef(0);
  const drawn = useRef(false);
  const settled = useRef(false);

  // Same points the lines are drawn from, carrying the real value + date for
  // the hover readout — tail's first point duplicates the last solid point
  // (line continuity), so it's labelled from trend, not projection.
  const hoverPoints = useMemo((): RidgePoint[] => {
    const solidPoints = solid.map((p, i) => ({
      x: p.x,
      y: p.y,
      value: trend[i],
      label: trendLabels?.[i],
    }));
    const tailPoints = tail.slice(1).map((p, i) => ({
      x: p.x,
      y: p.y,
      value: projection[i],
      label: projectionLabels?.[i],
    }));
    return [...solidPoints, ...tailPoints];
  }, [solid, tail, trend, projection, trendLabels, projectionLabels]);
  const { hovered, handlers } = useHoverReadout(hoverPoints);

  // geometry for the fill surface (triangle strip under the solid line)
  const fillGeometry = useMemo(() => {
    if (solid.length < 2) return null;
    const positions: number[] = [];
    for (let i = 0; i < solid.length - 1; i++) {
      const [x0, y0] = [solid[i].x, solid[i].y];
      const [x1, y1] = [solid[i + 1].x, solid[i + 1].y];
      positions.push(x0, 0, 0, x1, 0, 0, x1, y1, 0);
      positions.push(x0, 0, 0, x1, y1, 0, x0, y0, 0);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    return geo;
  }, [solid]);

  // vertex-colour gradient along the ridge: peri → gold → gold-bright
  const solidColors = useMemo(() => {
    const c0 = new THREE.Color("#8B93FF");
    const c1 = new THREE.Color("#E4C07C");
    const c2 = new THREE.Color("#F5DCA4");
    return solid.map((_, i): [number, number, number] => {
      const t = solid.length > 1 ? i / (solid.length - 1) : 0;
      const c = t < 0.45 ? c0.clone().lerp(c1, t / 0.45) : c1.clone().lerp(c2, (t - 0.45) / 0.55);
      return [c.r, c.g, c.b];
    });
  }, [solid]);

  // hand-built geometry is not reference-counted by r3f — drop it ourselves
  useEffect(() => () => fillGeometry?.dispose(), [fillGeometry]);

  // The panel is a wide, short strip (~7:1) while the ridge is ~4:1, so a fixed
  // camera either crops the span or shrinks it to a thumbnail. Frame the full
  // width from the live aspect, then scale the ridge's height into whatever
  // vertical room that leaves.
  const { camera, size } = useThree();
  const { distance, yScale, centreY } = useMemo(() => {
    const aspect = size.width / Math.max(size.height, 1);
    const half = Math.tan(((camera as THREE.PerspectiveCamera).fov * Math.PI) / 360);
    const d = (W * 1.04) / (2 * half * Math.max(aspect, 0.1));
    const visibleH = 2 * d * half;
    return { distance: d, yScale: (visibleH * 0.62) / H, centreY: visibleH * 0.31 };
  }, [camera, size.width, size.height]);

  useEffect(() => {
    const cam = camera as THREE.PerspectiveCamera;
    cam.position.set(W / 2, centreY, distance);
    cam.lookAt(W / 2, centreY, 0);
    cam.updateProjectionMatrix();
  }, [camera, centreY, distance]);

  useFrame((state) => {
    onFirstFrame();
    const g = groupRef.current;
    if (!g) return;
    // Once the draw-in sweep finishes, the ridge holds its final pose — no
    // idle breathing/pulsing — until the page is reloaded or revisited.
    if (settled.current) return;
    const t = state.clock.elapsedTime;
    // Draw-in: sweep the strip out of the left edge. Driven off the clock, not
    // accumulated delta, so a dropped or throttled frame loop leaves the ridge
    // fully drawn (the JSX default) instead of collapsed to a sliver.
    if (progress.current < 1) {
      // A hidden tab freezes rAF, so a sweep in progress would be left frozen
      // mid-stride: skip straight to drawn rather than show a sliver.
      progress.current = document.hidden ? 1 : Math.min(t / 2.0, 1);
      g.scale.x = 1 - Math.pow(1 - progress.current, 3); // easeOutCubic
      if (progress.current >= 1) drawn.current = true;
    }

    if (tailRef.current) tailRef.current.visible = drawn.current;
    if (ringRef.current) ringRef.current.visible = drawn.current;

    if (drawn.current) {
      // Final static values — set once, then stop touching this frame's refs.
      g.scale.y = 1;
      if (tailRef.current) {
        const mat = (tailRef.current.children[0] as THREE.Line & { material: THREE.LineDashedMaterial })
          ?.material;
        if (mat) mat.opacity = 0.7;
      }
      if (ringRef.current) {
        ringRef.current.scale.set(1, 1, 1);
        (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.5;
      }
      settled.current = true;
    }
  });

  if (solid.length < 2) return null;
  const last = solid[solid.length - 1];

  return (
    <group scale={[1, yScale, 1]}>
      {/* Invisible hit-plane for the hover readout — static, no drag/tilt. */}
      <mesh position={[W / 2, H / 2, 0.02]} {...handlers}>
        <planeGeometry args={[W, H * 1.6]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      {hovered && (
        <Html position={[hovered.x, hovered.y, 0.05]} center style={{ pointerEvents: "none" }}>
          <div
            style={{
              transform: "translateY(-130%)",
              whiteSpace: "nowrap",
              background: "rgba(10,10,14,.92)",
              border: "1px solid rgba(228,192,124,.35)",
              borderRadius: 4,
              padding: "4px 8px",
              fontSize: 11,
              fontFamily: "monospace",
              color: "#F5DCA4",
            }}
          >
            {hovered.label ? `${formatMonthLabel(hovered.label)} · ` : ""}
            {Number.isFinite(hovered.value) ? inr(hovered.value) : "—"}
          </div>
        </Html>
      )}
      <group ref={groupRef}>
        {benchmarkRuns.map((run, i) => (
          <DreiLine
            key={`benchmark-${i}`}
            points={run.map((p) => new THREE.Vector3(p.x, p.y, -0.05))}
            color="#8B93FF"
            lineWidth={1.4}
            transparent
            opacity={0.45}
            depthWrite={false}
          />
        ))}
        {fillGeometry && (
          <mesh ref={fillRef} geometry={fillGeometry}>
            <meshBasicMaterial color="#E4C07C" transparent opacity={0.13} depthWrite={false} />
          </mesh>
        )}
        <DreiLine
          points={solid.map((p) => new THREE.Vector3(p.x, p.y, 0))}
          vertexColors={solidColors}
          lineWidth={2.6}
          transparent
        />
        {tail.length >= 2 && (
          <group ref={tailRef}>
            <DreiLine
              points={tail.map((p) => new THREE.Vector3(p.x, p.y, 0))}
              color="#F5DCA4"
              lineWidth={1.8}
              dashed
              dashSize={0.1}
              gapSize={0.14}
              transparent
              opacity={0.8}
            />
          </group>
        )}
        <mesh ref={ringRef} position={[last.x, last.y, 0]}>
          <ringGeometry args={[0.13, 0.17, 40]} />
          <meshBasicMaterial color="#F5DCA4" transparent opacity={0.5} side={THREE.DoubleSide} />
        </mesh>
      </group>
      <mesh position={[last.x, last.y, 0]}>
        <circleGeometry args={[0.07, 24]} />
        <meshBasicMaterial color="#F5DCA4" />
      </mesh>
    </group>
  );
}

function hasWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

/** Static gold SVG ridge — same data, no motion (mockup port). */
function RidgeFallback({ trend, projection, benchmark }: RidgeProps) {
  const { solidPath, areaPath, tailPath, benchmarkPath, today, viewBox } = useMemo(() => {
    const values = [...trend, ...projection];
    if (values.length < 2) {
      return {
        solidPath: "",
        areaPath: "",
        tailPath: "",
        benchmarkPath: "",
        today: null,
        viewBox: "0 0 1000 150",
      };
    }
    const Wv = 1000;
    const Hv = 150;
    const finiteBenchmark = (benchmark ?? []).filter(
      (v): v is number => v !== null && Number.isFinite(v)
    );
    const scaleValues = finiteBenchmark.length ? [...values, ...finiteBenchmark] : values;
    const min = Math.min(...scaleValues);
    const max = Math.max(...scaleValues);
    const range = max - min || 1;
    const px = (i: number) => (i / (values.length - 1)) * Wv;
    const py = (v: number) => Hv - 6 - ((v - min) / range) * (Hv - 18);
    const pts = values.map((v, i) => [px(i), py(v)] as const);
    const nSolid = Math.max(trend.length, 2);
    const solid = pts.slice(0, nSolid);
    const tail = pts.slice(Math.max(nSolid - 1, 0));
    const toPath = (arr: readonly (readonly [number, number])[]) =>
      arr.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

    // Benchmark is aligned point-for-point with trend, not appended after it
    // — same px() index basis as trend, gaps break the path (new "M").
    let benchmarkPathStr = "";
    if (benchmark && finiteBenchmark.length) {
      let segment = "";
      benchmark.forEach((v, i) => {
        if (v === null || !Number.isFinite(v)) {
          segment = "";
          return;
        }
        const cmd = segment === "" ? "M" : "L";
        benchmarkPathStr += `${cmd}${px(i).toFixed(1)},${py(v).toFixed(1)} `;
        segment = "x";
      });
    }

    return {
      solidPath: toPath(solid),
      areaPath: `${toPath(solid)} L${solid[solid.length - 1][0].toFixed(1)},${Hv} L${solid[0][0].toFixed(1)},${Hv} Z`,
      tailPath: toPath(tail),
      benchmarkPath: benchmarkPathStr.trim(),
      today: solid[solid.length - 1],
      viewBox: `0 0 ${Wv} ${Hv}`,
    };
  }, [trend, projection, benchmark]);

  if (!solidPath) return null;
  return (
    <svg viewBox={viewBox} preserveAspectRatio="none" className="h-full w-full">
      <defs>
        <linearGradient id="au-goldfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#E4C07C" stopOpacity=".38" />
          <stop offset="1" stopColor="#E4C07C" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="au-goldline" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#8B93FF" />
          <stop offset=".45" stopColor="#E4C07C" />
          <stop offset="1" stopColor="#F5DCA4" />
        </linearGradient>
        <filter id="au-glow">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g stroke="rgba(255,255,255,.05)">
        <line x1="0" y1="37" x2="1000" y2="37" />
        <line x1="0" y1="75" x2="1000" y2="75" />
        <line x1="0" y1="113" x2="1000" y2="113" />
      </g>
      {benchmarkPath && (
        <path d={benchmarkPath} fill="none" stroke="#8B93FF" strokeWidth="1" strokeOpacity=".45" />
      )}
      <path d={areaPath} fill="url(#au-goldfill)" />
      <path d={solidPath} fill="none" stroke="url(#au-goldline)" strokeWidth="2.5" filter="url(#au-glow)" />
      {tailPath && (
        <path d={tailPath} fill="none" stroke="#F5DCA4" strokeWidth="2" strokeDasharray="3 6" opacity=".8" />
      )}
      {today && (
        <>
          <circle cx={today[0]} cy={today[1]} r="4.5" fill="#F5DCA4" />
          <circle cx={today[0]} cy={today[1]} r="10" fill="none" stroke="#F5DCA4" strokeOpacity=".35" />
        </>
      )}
    </svg>
  );
}

export default function NetWorthRidge({
  trend,
  trendLabels,
  projection,
  projectionLabels,
  benchmark,
  onMode,
}: RidgeProps & { onMode?: (mode: RidgeMode) => void }) {
  const [mode, setMode] = useState<"pending" | "three" | "svg">("pending");
  const framed = useRef(false);

  useEffect(() => {
    if (mode !== "pending") onMode?.(mode);
  }, [mode, onMode]);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    setMode(!reduced && hasWebGL() ? "three" : "svg");
  }, []);

  // A WebGL context that never paints leaves an empty panel. Give it a beat,
  // then fall back to the SVG — but only while the tab is visible, since a
  // hidden tab simply has rAF paused and will paint when it comes forward.
  useEffect(() => {
    if (mode !== "three") return;
    const id = setTimeout(() => {
      if (!framed.current && !document.hidden) setMode("svg");
    }, 1500);
    return () => clearTimeout(id);
  }, [mode]);

  if (trend.length < 2 && projection.length < 2) return null;
  if (mode !== "three")
    return <RidgeFallback trend={trend} projection={projection} benchmark={benchmark} />;

  return (
    <div className="h-full w-full touch-none" style={{ touchAction: "none" }}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [W / 2, H * 0.5, 8], fov: 40 }}
        gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      >
        <RidgeScene
          trend={trend}
          trendLabels={trendLabels}
          projection={projection}
          projectionLabels={projectionLabels}
          benchmark={benchmark}
          onFirstFrame={() => {
            framed.current = true;
          }}
        />
      </Canvas>
    </div>
  );
}
