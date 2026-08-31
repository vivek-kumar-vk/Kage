import * as THREE from "three";

// Pixel characters drawn from code-defined color matrices — no sprite packs,
// no external assets. New agents get a recolored character automatically (D12).

export type Pose = "idle" | "typing" | "stuck";

const INK = "#17130f";
const SKIN = "#e8b48c";
const ACCENT = "#FF7A00";

const POSES: Record<Pose, string[]> = {
  idle: [
    "....kkkk....",
    "...khhhhk...",
    "..khhhhhhk..",
    "..khsssshk..",
    "..ksesessk..",
    "..kssssssk..",
    "...kssssk...",
    "..kcccccck..",
    ".ksccccccsk.",
    ".ksccccccsk.",
    "..kccaccck..",
    "..kddddddk..",
    "...kd..dk...",
    "...kk..kk...",
  ],
  typing: [
    "....kkkk....",
    "...khhhhk...",
    "..khhhhhhk..",
    "..khsssshk..",
    "..ksesessk..",
    "..kssssssk..",
    "...kssssk...",
    "..kcccccck..",
    "..kcccccck..",
    "..kcsccsck..",
    "..kccaccck..",
    "..kddddddk..",
    "...kd..dk...",
    "...kk..kk...",
  ],
  stuck: [
    "....kkkk....",
    "...khhhhk...",
    "..khhhhhhk..",
    "..khsssshk..",
    "..ksesessk..",
    ".skssssssks.",
    ".skssssssks.",
    ".skccccccks.",
    "..kcccccck..",
    "..kcccccck..",
    "..kccaccck..",
    "..kddddddk..",
    "...kd..dk...",
    "...kk..kk...",
  ],
};

function shade(hex: string, factor: number): string {
  const n = hex.replace("#", "");
  const r = Math.round(parseInt(n.slice(0, 2), 16) * factor);
  const g = Math.round(parseInt(n.slice(2, 4), 16) * factor);
  const b = Math.round(parseInt(n.slice(4, 6), 16) * factor);
  return `rgb(${r}, ${g}, ${b})`;
}

const characterCache = new Map<string, THREE.CanvasTexture>();

export function buildCharacterTexture(pose: Pose, deptColor: string): THREE.CanvasTexture {
  const key = `${pose}|${deptColor}`;
  const hit = characterCache.get(key);
  if (hit) return hit;

  const palette: Record<string, string> = {
    k: INK,
    s: SKIN,
    e: INK,
    a: ACCENT,
    h: shade(deptColor, 0.45),
    c: deptColor,
    d: shade(deptColor, 0.6),
  };

  const canvas = document.createElement("canvas");
  canvas.width = 12;
  canvas.height = 14;
  const ctx = canvas.getContext("2d");

  if (ctx) {
    POSES[pose].forEach((row, y) => {
      [...row].forEach((ch, x) => {
        const color = palette[ch];
        if (!color) return;
        ctx.fillStyle = color;
        ctx.fillRect(x, y, 1, 1);
      });
    });
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.colorSpace = THREE.SRGBColorSpace;

  characterCache.set(key, texture);
  return texture;
}

let floorTexture: THREE.CanvasTexture | null = null;

export function buildFloorTexture(): THREE.CanvasTexture {
  if (floorTexture) return floorTexture;

  const canvas = document.createElement("canvas");
  canvas.width = 96;
  canvas.height = 96;
  const ctx = canvas.getContext("2d");

  if (ctx) {
    ctx.fillStyle = "#121110";
    ctx.fillRect(0, 0, 96, 96);
    ctx.fillStyle = "#1c1917";
    for (let i = 0; i < 96; i += 8) {
      ctx.fillRect(i, 0, 1, 96);
      ctx.fillRect(0, i, 96, 1);
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(9, 4);
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.colorSpace = THREE.SRGBColorSpace;

  floorTexture = texture;
  return texture;
}
