"use client";

interface RoadmapNodeProps {
  label: string;
  active?: boolean;
}

export default function RoadmapNode({ label, active = false }: RoadmapNodeProps) {
  return (
    <span
      className={[
        "inline-block border rounded px-2 py-1 text-xs",
        active ? "border-term-green text-term-green" : "border-term-border text-term-dim",
      ].join(" ")}
    >
      {label}
    </span>
  );
}
