"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import PixelCharacter from "./PixelCharacter";
import { buildFloorTexture } from "./pixelArt";
import type { AgentView, OfficeAgent, OfficeDepartment } from "../../lib/office";

// One fixed pixel stage — "stage, not sim" (D12). Desks are laid out from the
// roster; characters animate strictly from SSE events.

const ZONE_STEP = 9.2;
const ZONE_W = 8.6;
const ZONE_BACK_Z = -5.6;
const ZONE_FRONT_Z = 7.6;
const MAIN_Z = -4.4;
const SUB_ROWS_Z = [-1.7, 1.0, 3.7, 6.4];
const COLS_X = [-2.75, 0, 2.75];
const LOBBY_Z = -10.4;

const BUBBLE_LINGER_MS = 8000;
// A sub sits dormant (faint desk, no character) until it is tasked; it stays
// "awake" for a short grace period after going idle so a burst of work reads as
// one continuous presence rather than a flicker.
const DORMANT_GRACE_MS = 12000;

const STATUS_COLOR: Record<string, string> = {
  idle: "#3a3532",
  working: "#FF7A00",
  stuck: "#E33B2E",
};

function shortName(name: string) {
  return name.replace(/_Agent$/, "");
}

function CameraRig() {
  const camera = useThree((state) => state.camera);

  useEffect(() => {
    camera.lookAt(0, 0.6, 0.5);
  }, [camera]);

  return null;
}

function Floor({ texture }: { texture: THREE.Texture }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -1.4]}>
      <planeGeometry args={[50, 20]} />
      <meshBasicMaterial map={texture} />
    </mesh>
  );
}

function ZoneFrame({
  color,
  x,
  zBack,
  zFront,
  width,
  label,
}: {
  color: string;
  x: number;
  zBack: number;
  zFront: number;
  width: number;
  label: string;
}) {
  const three = useMemo(() => new THREE.Color(color), [color]);

  const border = useMemo(() => {
    const half = width / 2 - 0.3;
    const points = [
      new THREE.Vector3(-half, 0.02, zBack - 0.3),
      new THREE.Vector3(half, 0.02, zBack - 0.3),
      new THREE.Vector3(half, 0.02, zFront + 0.3),
      new THREE.Vector3(-half, 0.02, zFront + 0.3),
    ];
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [width, zBack, zFront]);

  return (
    <group position={[x, 0, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, (zBack + zFront) / 2]}>
        <planeGeometry args={[width - 0.6, zFront - zBack + 0.6]} />
        <meshBasicMaterial color={three} transparent opacity={0.05} />
      </mesh>
      <lineLoop geometry={border}>
        <lineBasicMaterial color={three} transparent opacity={0.4} />
      </lineLoop>
      <Html position={[0, 0.1, zBack - 1.0]} center>
        <span className="zone-tag" style={{ color }}>
          {label}
        </span>
      </Html>
    </group>
  );
}

function DeskUnit({
  agent,
  deptColor,
  view,
  selected,
  onSelect,
  now,
  x,
  z,
  reducedMotion,
}: {
  agent: OfficeAgent;
  deptColor: string;
  view: AgentView | undefined;
  selected: boolean;
  onSelect: (name: string) => void;
  now: number;
  x: number;
  z: number;
  reducedMotion: boolean;
}) {
  const ringMat = useRef<THREE.MeshBasicMaterial>(null);
  const status = view?.status ?? "idle";
  const bubbleFresh = view ? now - (view.at || 0) < BUBBLE_LINGER_MS : false;
  const showBubble = Boolean(view?.text) && (status !== "idle" || bubbleFresh);

  // Subs are dormant until tasked. Head + mains are always staffed.
  const awake =
    agent.tier !== "sub" ||
    status !== "idle" ||
    (view ? now - (view.at || 0) < DORMANT_GRACE_MS : false);

  useFrame((state) => {
    const mat = ringMat.current;
    if (!mat) return;

    if (status === "working" ) {
      mat.opacity = 0.35 + Math.sin(state.clock.elapsedTime * 3.2) * 0.18;
    } else if (status === "stuck") {
      mat.opacity = 0.45;
    } else {
      mat.opacity = 0.14;
    }
  });

  if (!awake) {
    return (
      <group
        position={[x, 0, z]}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(agent.name);
        }}
        onPointerOver={() => {
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "auto";
        }}
      >
        <mesh position={[0, 0.12, 0.35]}>
          <boxGeometry args={[1.7, 0.22, 0.8]} />
          <meshBasicMaterial color="#151210" transparent opacity={0.5} />
        </mesh>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0.35]}>
          <ringGeometry args={[1.15, 1.32, 24]} />
          <meshBasicMaterial color={deptColor} transparent opacity={0.06} />
        </mesh>
        <Html position={[0, 0.05, 1.3]} center>
          <span className="desk-label desk-label-dormant">{shortName(agent.name)}</span>
        </Html>
      </group>
    );
  }

  return (
    <group
      position={[x, 0, z]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(agent.name);
      }}
      onPointerOver={() => {
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "auto";
      }}
    >
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0.35]}>
        <ringGeometry args={[1.15, 1.38, 28]} />
        <meshBasicMaterial
          ref={ringMat}
          color={status === "idle" ? deptColor : STATUS_COLOR[status]}
          transparent
          opacity={0.14}
        />
      </mesh>

      <mesh position={[0, 0.16, 0.35]}>
        <boxGeometry args={[1.7, 0.32, 0.85]} />
        <meshBasicMaterial color="#1c1815" />
      </mesh>
      <mesh position={[0, 0.4, 0.35]}>
        <boxGeometry args={[2.1, 0.14, 1.15]} />
        <meshBasicMaterial color="#2a2420" />
      </mesh>
      <mesh position={[0, 0.78, 0.12]}>
        <boxGeometry args={[1.0, 0.62, 0.07]} />
        <meshBasicMaterial color="#17130f" />
      </mesh>
      <mesh position={[0, 0.78, 0.17]}>
        <planeGeometry args={[0.88, 0.5]} />
        <meshBasicMaterial color={STATUS_COLOR[status]} />
      </mesh>

      <PixelCharacter
        position={[0, 0, -0.72]}
        deptColor={deptColor}
        status={status}
        reducedMotion={reducedMotion}
      />

      <Html position={[0, 0.05, 1.35]} center>
        <span className={`desk-label${selected ? " desk-label-selected" : ""}`}>
          {shortName(agent.name)}
        </span>
      </Html>

      {showBubble && view?.text ? (
        <Html position={[0, 2.45, -0.5]} center>
          <div className="pixel-bubble">
            {view.sim ? <span className="sim-tag">SIM</span> : null}
            {view.text}
          </div>
        </Html>
      ) : null}
    </group>
  );
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

export default function OfficeStage({
  agents,
  departments,
  states,
  tab,
  selected,
  onSelect,
  now,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(26);
  const [reducedMotion] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  const floorTex = useMemo(() => buildFloorTexture(), []);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    const update = () => setZoom(Math.max(14, Math.min(40, el.clientWidth / 52)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const deptColor = useMemo(() => {
    const map = new Map<string, string>();
    for (const dept of departments) map.set(dept.id, dept.color);
    return (id: string) => map.get(id) ?? "#8B9099";
  }, [departments]);

  const { positions: layout, deptX } = useMemo(() => {
    const positions = new Map<string, { x: number; z: number; dept: string }>();
    const deptIds = departments.filter((d) => d.id !== "lobby").map((d) => d.id);


    for (const agent of agents) {
      if (agent.department === "lobby" || agent.tier === "head") {
        positions.set(agent.name, { x: 0, z: LOBBY_Z, dept: "lobby" });
      }
    }

    deptIds.forEach((id, index) => {
      const zx = (index - (deptIds.length - 1) / 2) * ZONE_STEP;
      const members = agents.filter((a) => a.department === id);
      const mains = members.filter((a) => a.tier === "main");
      const subs = members.filter((a) => a.tier !== "main");

      mains.forEach((agent, i) => {
        positions.set(agent.name, {
          x: zx + (i - (mains.length - 1) / 2) * 2.6,
          z: MAIN_Z,
          dept: id,
        });
      });

      subs.forEach((agent, i) => {
        const row = Math.min(Math.floor(i / 3), SUB_ROWS_Z.length - 1);
        positions.set(agent.name, {
          x: zx + COLS_X[i % 3],
          z: SUB_ROWS_Z[row],
          dept: id,
        });
      });
    });

    const deptX = new Map<string, number>();
    deptIds.forEach((id, index) => {
      deptX.set(id, (index - (deptIds.length - 1) / 2) * ZONE_STEP);
    });

    return { positions, deptX };
  }, [agents, departments]);

  const visible = (dept: string) => tab === "all" || tab === dept;

  const deskAgents = useMemo(
    () => agents.filter((agent) => layout.has(agent.name)),
    [agents, layout]
  );

  return (
    <div ref={wrapRef} className="absolute inset-0">
      <Canvas
        orthographic
        dpr={[1, 2]}
        camera={{ position: [0, 15, 21], zoom, near: -200, far: 500 }}
        onPointerMissed={() => onSelect("")}
      >
        <color attach="background" args={["#0E0E0E"]} />
        <CameraRig />
        <Floor texture={floorTex} />

        {visible("lobby") ? (
          <ZoneFrame
            color={deptColor("lobby")}
            x={0}
            zBack={LOBBY_Z - 1.2}
            zFront={LOBBY_Z + 1.2}
            width={46}
            label="Lobby · Orchestrator"
          />
        ) : null}

        {departments
          .filter((d) => d.id !== "lobby" && visible(d.id))
          .map((dept) => {
            const zx = (deptX.get(dept.id) ?? 0);
            return (
              <ZoneFrame
                key={dept.id}
                color={dept.color}
                x={zx}
                zBack={ZONE_BACK_Z}
                zFront={ZONE_FRONT_Z}
                width={ZONE_W}
                label={dept.label}
              />
            );
          })}

        {deskAgents.map((agent) => {
          const pos = layout.get(agent.name)!;
          if (!visible(pos.dept)) return null;
          return (
            <DeskUnit
              key={agent.name}
              agent={agent}
              deptColor={deptColor(agent.department)}
              view={states.get(agent.name)}
              selected={selected === agent.name}
              onSelect={onSelect}
              now={now}
              x={pos.x}
              z={pos.z}
              reducedMotion={reducedMotion}
            />
          );
        })}
      </Canvas>
    </div>
  );
}
