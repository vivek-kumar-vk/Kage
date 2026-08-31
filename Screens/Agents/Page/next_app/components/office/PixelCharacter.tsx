"use client";

import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { buildCharacterTexture, type Pose } from "./pixelArt";

const EASE_OUT_BACK = (x: number) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
};

interface Props {
  position: [number, number, number];
  deptColor: string;
  status: "idle" | "working" | "stuck";
  reducedMotion: boolean;
}

export default function PixelCharacter({ position, deptColor, status, reducedMotion }: Props) {
  const pose: Pose = status === "working" ? "typing" : status === "stuck" ? "stuck" : "idle";
  const texture = useMemo(() => buildCharacterTexture(pose, deptColor), [pose, deptColor]);

  const meshRef = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshBasicMaterial>(null);
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);
  const spawnAt = useRef(0);
  const prevStatus = useRef(status);
  const puffRef = useRef<THREE.Group>(null);
  const puffT0 = useRef(-1);

  useEffect(() => {
    if (prevStatus.current !== "working" && status === "working") {
      spawnAt.current = performance.now();
      puffT0.current = performance.now();
    }
    prevStatus.current = status;
  }, [status]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const mesh = meshRef.current;

    if (mesh) {
      let offsetX = 0;
      let offsetY = 0;

      if (!reducedMotion) {
        if (status === "idle") {
          offsetY = Math.sin(t * 1.8 + phase) * 0.04;
        } else if (status === "working") {
          offsetX = Math.sin(t * 22 + phase) * 0.02;
        } else if (status === "stuck") {
          offsetX = Math.sin(t * 30) * 0.015;
        }
      }

      mesh.position.x = offsetX;
      mesh.position.y = offsetY;

      const sinceSpawn = (performance.now() - spawnAt.current) / 1000;
      const scale =
        !reducedMotion && spawnAt.current > 0 && sinceSpawn < 0.35
          ? EASE_OUT_BACK(sinceSpawn / 0.35)
          : 1;
      mesh.scale.setScalar(scale);

      const mat = matRef.current;
      if (mat) {
        const target = status === "idle" ? 0.55 : 1;
        mat.opacity += (target - mat.opacity) * (reducedMotion ? 1 : 0.12);
      }
    }

    const puffs = puffRef.current;
    if (puffs) {
      const p = puffT0.current < 0 ? 2 : (performance.now() - puffT0.current) / 600;
      puffs.visible = p <= 1 && !reducedMotion;

      if (puffs.visible) {
        puffs.children.forEach((child, i) => {
          const angle = (i / 8) * Math.PI * 2;
          child.position.set(
            Math.cos(angle) * 0.9 * p,
            0.25 + p * 1.1 - 1.1 * p * p,
            Math.sin(angle) * 0.5 * p
          );
          child.scale.setScalar(0.14 * (1 - p * 0.5));
          const material = (child as THREE.Mesh).material as THREE.MeshBasicMaterial;
          material.opacity = 1 - p;
        });
      }
    }
  });

  return (
    <group position={position}>
      <mesh ref={meshRef} position={[0, 1.02, 0]}>
        <planeGeometry args={[1.35, 1.575]} />
        <meshBasicMaterial
          ref={matRef}
          map={texture}
          transparent
          opacity={0.55}
          alphaTest={0.01}
        />
      </mesh>
      <group ref={puffRef} position={[0, 0.4, -0.4]} visible={false}>
        {Array.from({ length: 8 }).map((_, i) => (
          <mesh key={i}>
            <planeGeometry args={[1, 1]} />
            <meshBasicMaterial color={deptColor} transparent opacity={0.8} depthWrite={false} />
          </mesh>
        ))}
      </group>
    </group>
  );
}
