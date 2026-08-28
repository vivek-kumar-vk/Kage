"use client";

import { motion } from "framer-motion";
import { AgentGlyphNode } from "./AgentGlyphNode";
import type { AgentEntry } from "./useAgentFleetActivity";

const RING_SPIN_SECONDS = 90;

/** The fleet, ringed around the centre core - one glyph node per agent
    returned by /api/main_menu/agents/fleet, spaced evenly (360deg /
    count) so the ring re-spaces itself automatically as agents are
    added, never a fixed layout. The ring itself spins continuously and
    always (pure ambient motion, ties to nothing) while each node
    counter-rotates against that spin so its glyph stays upright - a
    node's own glow/pulse is a separate signal, driven by
    useAgentFleetActivity's real trace-event matching, never the spin. */
export function AgentRing({
  agents,
  pulsing,
  radius = 190,
  onSelect,
}: {
  agents: AgentEntry[] | null;
  pulsing: Record<string, boolean>;
  radius?: number;
  onSelect?: (name: string) => void;
}) {
  const list = agents ?? [];
  const count = Math.max(list.length, 1);

  return (
    <motion.div
      aria-hidden={list.length === 0}
      className="absolute left-1/2 top-1/2"
      style={{ width: 0, height: 0 }}
      animate={{ rotate: 360 }}
      transition={{ duration: RING_SPIN_SECONDS, repeat: Infinity, ease: "linear" }}
    >
      {list.map((a, i) => {
        const angle = (360 / count) * i;
        return (
          <div
            key={a.name}
            className="absolute"
            style={{
              transform: `rotate(${angle}deg) translate(${radius}px) rotate(${-angle}deg) translate(-50%, -50%)`,
            }}
          >
            {/* Counter-spin against the parent's continuous rotation so
                the glyph and label stay upright for the viewer. */}
            <motion.div
              title={`${a.name} - ${a.what_i_am_for}`}
              className="flex flex-col items-center gap-1"
              animate={{ rotate: -360 }}
              transition={{ duration: RING_SPIN_SECONDS, repeat: Infinity, ease: "linear" }}
            >
              <button
                type="button"
                aria-label={`open ${a.name}'s files`}
                onClick={() => onSelect?.(a.name)}
                className="cursor-pointer rounded-full"
              >
                <AgentGlyphNode name={a.name} active={!!pulsing[a.name]} />
              </button>
              <span
                className="num max-w-[64px] truncate text-center text-[8px] tracking-wide"
                style={{ color: pulsing[a.name] ? "var(--agentic-amber, #ff7a00)" : "#8B9099" }}
              >
                {a.name.replace(/_Agent$/i, "")}
              </span>
            </motion.div>
          </div>
        );
      })}
    </motion.div>
  );
}
