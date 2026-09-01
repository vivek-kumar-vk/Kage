"use client";

import { RingNode, type GlyphName } from "./RingNode";

/** The agent ring - a full circle of ~30 nodes around the centre core,
    exactly as in the reference image. The whole track spins once every
    90s (pure ambient motion, ties to nothing) and every node
    counter-spins at the same rate so its glyph and cadence tag stay
    upright. Each node is anchored with
      rotate(angle) translate(radius) rotate(-angle) translate(-50%,-50%)
    so it sits dead-centre on the circular track and never drifts. */

type Node = { glyph: GlyphName; cadence?: string; variant?: "default" | "active" | "info" };

// 30 decorative nodes. The glyph set and cadence tags echo the image's
// mix of bolts, mail, players, docs and dashboards; one node (index 22,
// on the right of the ring) is the enlarged amber "info" node.
const NODES: Node[] = [
  { glyph: "mail", cadence: "1d" },
  { glyph: "bolt", cadence: "1d" },
  { glyph: "bolt", cadence: "1d" },
  { glyph: "play", cadence: "1d" },
  { glyph: "bolt", cadence: "1d" },
  { glyph: "chart", cadence: "14d" },
  { glyph: "target", cadence: "14d" },
  { glyph: "bolt", cadence: "1d" },
  { glyph: "terminal", cadence: "1d" },
  { glyph: "doc", cadence: "3d" },
  { glyph: "gear", cadence: "7d" },
  { glyph: "node", cadence: "1d" },
  { glyph: "grid", cadence: "1d" },
  { glyph: "doc", cadence: "1d" },
  { glyph: "doc", cadence: "1d" },
  { glyph: "brain", cadence: "3d" },
  { glyph: "doc", cadence: "1d" },
  { glyph: "chart", cadence: "7d" },
  { glyph: "grid", cadence: "1d" },
  { glyph: "eye", cadence: "1d" },
  { glyph: "play", cadence: "1d" },
  { glyph: "mail", cadence: "1d" },
  { glyph: "info", variant: "info" },
  { glyph: "target", cadence: "14d", variant: "active" },
  { glyph: "gear", cadence: "7d" },
  { glyph: "chart", cadence: "14d" },
  { glyph: "bolt", cadence: "1d" },
  { glyph: "play", cadence: "1d" },
  { glyph: "mail", cadence: "1d" },
  { glyph: "node", cadence: "3d" },
];

export function AgentRing({ radius }: { radius: number }) {
  const count = NODES.length;

  return (
    <div
      aria-hidden="true"
      className="ring-track absolute left-1/2 top-1/2"
      style={{ width: 0, height: 0 }}
    >
      {NODES.map((node, i) => {
        const angle = (360 / count) * i;
        return (
          <div
            key={i}
            className="absolute"
            style={{
              transform: `rotate(${angle}deg) translate(${radius}px) rotate(${-angle}deg) translate(-50%, -50%)`,
            }}
          >
            <div className="ring-node-upright">
              <RingNode glyph={node.glyph} cadence={node.cadence} variant={node.variant} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
