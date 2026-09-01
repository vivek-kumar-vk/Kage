"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/** Evenly spread n points on a sphere shell with the golden-angle
    (Fibonacci) method, then pull each one in by a random amount so the
    cloud reads as a soft burst rather than a hard shell - matching the
    reference image's dense multicolour core. */
function fibonacciCloud(count: number): Float32Array {
  const positions = new Float32Array(count * 3);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const r = Math.sqrt(Math.max(1 - y * y, 0));
    const theta = golden * i;
    // 0.35..1.0 of the radius - a filled burst, not a hollow shell.
    const shrink = 0.35 + Math.pow(Math.random(), 0.5) * 0.65;
    positions[i * 3] = Math.cos(theta) * r * shrink;
    positions[i * 3 + 1] = y * shrink;
    positions[i * 3 + 2] = Math.sin(theta) * r * shrink;
  }
  return positions;
}

/** Per-point colour: mostly cool cyan -> violet, with a few warm amber
    and white sparks, so the core glows the way the reference does
    without ever looking like a real gauge (C12 - decorative only). */
const CORE_COLOURS = [
  "#22d3ee", // cyan
  "#38bdf8", // sky
  "#818cf8", // indigo
  "#a78bfa", // violet
  "#c4b5fd", // light violet
  "#f5f5f5", // white spark
  "#ff9b3d", // warm amber spark
];

function colourBuffer(count: number): Float32Array {
  const colours = new Float32Array(count * 3);
  const c = new THREE.Color();
  for (let i = 0; i < count; i++) {
    // Bias hard toward the cool end of the list.
    const pick =
      Math.random() < 0.82
        ? Math.floor(Math.random() * 5)
        : 5 + Math.floor(Math.random() * 2);
    c.set(CORE_COLOURS[pick]);
    colours[i * 3] = c.r;
    colours[i * 3 + 1] = c.g;
    colours[i * 3 + 2] = c.b;
  }
  return colours;
}

function DottedParticleCore() {
  const cloud = useRef<THREE.Points>(null);
  const shell = useRef<THREE.LineSegments>(null);

  const COUNT = 900;
  const positions = useMemo(() => fibonacciCloud(COUNT), []);
  const colours = useMemo(() => colourBuffer(COUNT), []);

  // A faint wireframe icosphere sitting behind the burst - the geodesic
  // shell visible in the reference.
  const shellGeometry = useMemo(
    () => new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.55, 2)),
    [],
  );

  useFrame((_, delta) => {
    if (cloud.current) {
      cloud.current.rotation.y += delta * 0.09;
      cloud.current.rotation.x += delta * 0.035;
    }
    if (shell.current) {
      shell.current.rotation.y -= delta * 0.03;
      shell.current.rotation.z += delta * 0.012;
    }
  });

  return (
    <group>
      <lineSegments ref={shell} geometry={shellGeometry}>
        <lineBasicMaterial
          color="#3a3a3a"
          transparent
          opacity={0.35}
          depthWrite={false}
        />
      </lineSegments>

      <points ref={cloud}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[positions, 3]}
          />
          <bufferAttribute attach="attributes-color" args={[colours, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.035}
          vertexColors
          transparent
          opacity={0.95}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  );
}

/** The glowing centre core, in real 3D (Three.js / @react-three/fiber).
    Purely ambient - it represents nothing and is never wired to data
    (C12). Absolutely positioned so it sits behind the agent ring. */
export function ParticleCore3D() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 flex items-center justify-center"
    >
      <Canvas
        camera={{ position: [0, 0, 4.2], fov: 50 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <DottedParticleCore />
      </Canvas>
    </div>
  );
}
