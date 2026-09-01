"use client";

import * as THREE from "three";
import { shade } from "./pixelArt";

type FurnitureProps = {
  color: string;
  scale?: number | [number, number, number];
};

type RugProps = FurnitureProps & {
  texture?: THREE.Texture;
};

const C_DARK = "#17130f";
const C_MID = "#2a2420";
const C_LIGHT = "#1c1815";

function applyScale(scale?: number | [number, number, number]): [number, number, number] {
  if (!scale) return [1, 1, 1];
  if (typeof scale === "number") return [scale, scale, scale];
  return scale;
}

export function Rack({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 1.2, 0]}>
        <boxGeometry args={[1.2, 2.4, 0.8]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
      <mesh position={[0, 1.2, 0.41]}>
        <boxGeometry args={[0.8, 2.0, 0.02]} />
        <meshBasicMaterial color={shade(color, 0.6)} />
      </mesh>
    </group>
  );
}

export function CableTray({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 2.8, 0]}>
        <boxGeometry args={[3, 0.1, 0.4]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      <mesh position={[0, 2.7, 0]}>
        <boxGeometry args={[2.8, 0.05, 0.2]} />
        <meshBasicMaterial color={shade(color, 0.4)} />
      </mesh>
    </group>
  );
}

export function MonitorBench({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.7, 0]}>
        <boxGeometry args={[4, 0.1, 1.2]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      <mesh position={[-1.8, 0.35, 0]}>
        <boxGeometry args={[0.1, 0.7, 1.0]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
      <mesh position={[1.8, 0.35, 0]}>
        <boxGeometry args={[0.1, 0.7, 1.0]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
      {[-1.2, 0, 1.2].map((x, i) => (
        <mesh key={i} position={[x, 1.1, -0.3]}>
          <boxGeometry args={[0.9, 0.6, 0.05]} />
          <meshBasicMaterial color={i === 1 ? color : shade(color, 0.7)} />
        </mesh>
      ))}
    </group>
  );
}

export function LedgerCabinet({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.8, 0]}>
        <boxGeometry args={[0.8, 1.6, 0.6]} />
        <meshBasicMaterial color={C_LIGHT} />
      </mesh>
      {[0.2, 0.6, 1.0, 1.4].map((y, i) => (
        <mesh key={i} position={[0, y, 0.31]}>
          <boxGeometry args={[0.7, 0.3, 0.02]} />
          <meshBasicMaterial color={shade(color, 0.5)} />
        </mesh>
      ))}
    </group>
  );
}

export function Safe({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.5, 0]}>
        <boxGeometry args={[1.0, 1.0, 1.0]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
      <mesh position={[0, 0.5, 0.51]}>
        <boxGeometry args={[0.8, 0.8, 0.02]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      <mesh position={[0.2, 0.5, 0.53]}>
        <boxGeometry args={[0.15, 0.15, 0.02]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

export function Bookshelf({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 1.2, 0]}>
        <boxGeometry args={[1.6, 2.4, 0.5]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      {[0.4, 1.0, 1.6].map((y, i) => (
        <mesh key={i} position={[0, y, 0.1]}>
          <boxGeometry args={[1.4, 0.4, 0.3]} />
          <meshBasicMaterial color={i % 2 === 0 ? shade(color, 0.6) : shade(color, 0.8)} />
        </mesh>
      ))}
    </group>
  );
}

export function ReadingTable({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.75, 0]}>
        <boxGeometry args={[3.5, 0.1, 1.4]} />
        <meshBasicMaterial color={C_LIGHT} />
      </mesh>
      {[[-1.5, -0.5], [1.5, -0.5], [-1.5, 0.5], [1.5, 0.5]].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.35, z]}>
          <boxGeometry args={[0.15, 0.7, 0.15]} />
          <meshBasicMaterial color={C_DARK} />
        </mesh>
      ))}
    </group>
  );
}

export function DeskLamp({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[0.3, 0.1, 0.3]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
      <mesh position={[0, 0.3, 0]}>
        <boxGeometry args={[0.05, 0.5, 0.05]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      <mesh position={[0, 0.55, 0]}>
        <boxGeometry args={[0.4, 0.2, 0.3]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

export function PlanningTable({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.8, 0]}>
        <boxGeometry args={[4.5, 0.15, 2.5]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      {[[-2, -1], [2, -1], [-2, 1], [2, 1]].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.4, z]}>
          <boxGeometry args={[0.2, 0.8, 0.2]} />
          <meshBasicMaterial color={C_DARK} />
        </mesh>
      ))}
      <mesh position={[0, 0.88, 0]}>
        <boxGeometry args={[2.5, 0.01, 1.5]} />
        <meshBasicMaterial color={shade(color, 0.3)} />
      </mesh>
    </group>
  );
}

export function PinBoard({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 1.4, 0]}>
        <boxGeometry args={[2.5, 1.6, 0.1]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
      <mesh position={[0, 1.4, 0.06]}>
        <boxGeometry args={[2.3, 1.4, 0.02]} />
        <meshBasicMaterial color={shade(color, 0.4)} />
      </mesh>
      {[-0.6, 0.2, 0.8].map((x, i) => (
        <mesh key={i} position={[x, 1.6, 0.08]}>
          <boxGeometry args={[0.1, 0.1, 0.02]} />
          <meshBasicMaterial color={color} />
        </mesh>
      ))}
    </group>
  );
}

export function Stool({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.4, 0]}>
        <boxGeometry args={[0.5, 0.1, 0.5]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0, 0.2, 0]}>
        <boxGeometry args={[0.1, 0.4, 0.1]} />
        <meshBasicMaterial color={C_DARK} />
      </mesh>
    </group>
  );
}

export function Sofa({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.3, 0]}>
        <boxGeometry args={[2.2, 0.4, 1.0]} />
        <meshBasicMaterial color={shade(color, 0.8)} />
      </mesh>
      <mesh position={[0, 0.7, -0.4]}>
        <boxGeometry args={[2.2, 0.6, 0.2]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[-1.0, 0.5, 0]}>
        <boxGeometry args={[0.2, 0.4, 1.0]} />
        <meshBasicMaterial color={shade(color, 0.6)} />
      </mesh>
      <mesh position={[1.0, 0.5, 0]}>
        <boxGeometry args={[0.2, 0.4, 1.0]} />
        <meshBasicMaterial color={shade(color, 0.6)} />
      </mesh>
    </group>
  );
}

export function LowTable({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.3, 0]}>
        <boxGeometry args={[1.4, 0.1, 0.8]} />
        <meshBasicMaterial color={C_LIGHT} />
      </mesh>
      {[[-0.6, -0.3], [0.6, -0.3], [-0.6, 0.3], [0.6, 0.3]].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.15, z]}>
          <boxGeometry args={[0.1, 0.3, 0.1]} />
          <meshBasicMaterial color={C_DARK} />
        </mesh>
      ))}
    </group>
  );
}

export function Plant({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.2, 0]}>
        <boxGeometry args={[0.5, 0.4, 0.5]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      <mesh position={[0, 0.7, 0]}>
        <boxGeometry args={[0.8, 0.8, 0.8]} />
        <meshBasicMaterial color={shade(color, 0.9)} />
      </mesh>
      <mesh position={[0.2, 1.0, 0.2]}>
        <boxGeometry args={[0.4, 0.4, 0.4]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

export function ReceptionDesk({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.6, 0]}>
        <boxGeometry args={[4.0, 1.2, 0.8]} />
        <meshBasicMaterial color={C_MID} />
      </mesh>
      <mesh position={[0, 1.21, 0]}>
        <boxGeometry args={[4.0, 0.05, 0.8]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0, 0.6, 0.41]}>
        <boxGeometry args={[3.8, 1.0, 0.02]} />
        <meshBasicMaterial color={C_LIGHT} />
      </mesh>
    </group>
  );
}

export function Bench({ color, scale }: FurnitureProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh position={[0, 0.4, 0]}>
        <boxGeometry args={[2.5, 0.15, 0.6]} />
        <meshBasicMaterial color={C_LIGHT} />
      </mesh>
      {[-1.0, 1.0].map((x, i) => (
        <mesh key={i} position={[x, 0.2, 0]}>
          <boxGeometry args={[0.15, 0.4, 0.5]} />
          <meshBasicMaterial color={C_DARK} />
        </mesh>
      ))}
    </group>
  );
}

export function FlatRug({ color, scale, texture }: RugProps) {
  const s = applyScale(scale);
  return (
    <group scale={s}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[4, 3]} />
        {texture ? (
          <meshBasicMaterial map={texture} />
        ) : (
          <meshBasicMaterial color={shade(color, 0.3)} />
        )}
      </mesh>
    </group>
  );
}