"use client";

import { useState } from "react";
import { useAgentRoster, type AgentNode } from "../lib/agents";

/** The agent ring - one real node per agent, read live from the Agent
    Deck (2026-09-06, replaces the decorative 30-glyph placeholder ring).

    One line for everybody (owner's call 2026-09-06): main-tier agents
    (plus the head) and sub-agents all sit centred ON the drawn circle,
    mains a little bigger with their model id printed just below the node.
    Mains are slotted at even intervals among the subs so the big nodes
    never bunch up. The live particle core still fills the centre
    (CenterCore renders it behind this ring).

    The whole track turns slowly - `.ring-track` in globals.css, 90 s per
    revolution - and each node counter-turns (`.ring-node-upright`) so its
    glyph and label stay upright; both animations stop under
    prefers-reduced-motion. A node glows amber while its agent has unread
    messages; hovering shows the agent name; clicking lands in that agent's
    Agent Deck chat. */

const AMBER = "#ff7a00";
const INK_DIM = "#6b7079";

function initialsOf(name: string) {
  const clean = name.replace(/_Agent$/i, "").replace(/_/g, " ").trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return clean.slice(0, 2).toUpperCase();
}

function AgentNodeCircle({
  agent,
  deckUrl,
  size,
  showModel,
}: {
  agent: AgentNode;
  deckUrl: string;
  size: number;
  showModel: boolean;
}) {
  const [hover, setHover] = useState(false);
  const isMain = agent.tier === "main" || agent.tier === "head";
  const glow = agent.unread > 0;

  return (
    <div
      className="relative flex flex-col items-center gap-1"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <a
        href={`${deckUrl}?agent=${encodeURIComponent(agent.name)}`}
        title={`${agent.name}${agent.unread > 0 ? ` — ${agent.unread} unread` : ""}`}
        aria-label={`${agent.name}${agent.unread > 0 ? `, ${agent.unread} unread` : ""}`}
        className="flex items-center justify-center rounded-full border transition-shadow"
        style={{
          width: size,
          height: size,
          borderColor: isMain ? AMBER : "#333333",
          background: "#141212",
          boxShadow: glow
            ? `0 0 ${isMain ? 20 : 12}px rgba(255,122,0,0.65), inset 0 0 6px rgba(255,122,0,0.25)`
            : isMain
              ? "0 0 8px rgba(255,122,0,0.2)"
              : "inset 0 0 10px rgba(255,255,255,0.03)",
          fontSize: Math.round(size * 0.28),
          letterSpacing: "0.02em",
          color: isMain ? AMBER : "#c7ccd4",
        }}
      >
        {initialsOf(agent.name)}
      </a>
      {showModel ? (
        <span
          className="num text-[7px] leading-none tracking-wide"
          style={{ color: INK_DIM, maxWidth: 84, overflow: "hidden" }}
        >
          {agent.model ?? "main"}
        </span>
      ) : null}
      {hover ? (
        <span
          className="pointer-events-none absolute whitespace-nowrap rounded border px-2 py-1 text-[10px]"
          style={{
            background: "#141212",
            borderColor: "#333333",
            color: "#ffffff",
            zIndex: 40,
            transform: "translateY(-120%)",
          }}
        >
          {agent.name}
          {agent.unread > 0 ? ` · ${agent.unread} unread` : ""}
        </span>
      ) : null}
    </div>
  );
}

/** One node on the track. The positioner's rotate/translate/rotate-back
    puts the node on its circle upright; the counter-spin wrapper cancels
    the track's own rotation so the label never tilts. */
function RingNode({
  agent,
  angle,
  radius,
  deckUrl,
  size,
  showModel,
}: {
  agent: AgentNode;
  angle: number;
  radius: number;
  deckUrl: string;
  size: number;
  showModel: boolean;
}) {
  return (
    <div
      className="absolute"
      style={{
        transform: `rotate(${angle}deg) translate(${radius}px) rotate(${-angle}deg) translate(-50%, -50%)`,
      }}
    >
      <div className="ring-node-upright">
        <AgentNodeCircle agent={agent} deckUrl={deckUrl} size={size} showModel={showModel} />
      </div>
    </div>
  );
}

export function AgentRing({ radius }: { radius: number }) {
  const { data, loading } = useAgentRoster();
  const agents = data?.state === "ok" ? data.agents : [];
  const deckUrl = data?.deck_url ?? "/workspace";

  // One line for everybody. Mains (plus the head) are slotted at even
  // intervals among the subs - the +0.5 offset never collides because
  // mains are far fewer than half the roster - so the big nodes stay
  // spread around the circle.
  const mains = agents.filter((a) => a.tier === "main" || a.tier === "head");
  const subs = agents.filter((a) => a.tier !== "main" && a.tier !== "head");

  const total = mains.length + subs.length;
  const mainSlots = new Set(
    mains.map((_, i) => Math.round(((i + 0.5) * total) / Math.max(mains.length, 1)) % total),
  );
  const ordered: AgentNode[] = [];
  let nextMain = 0;
  let nextSub = 0;
  for (let slot = 0; slot < total; slot++) {
    if (mainSlots.has(slot) && nextMain < mains.length) ordered.push(mains[nextMain++]);
    else if (nextSub < subs.length) ordered.push(subs[nextSub++]);
    else if (nextMain < mains.length) ordered.push(mains[nextMain++]);
  }

  // Node centres ride the drawn circle itself.
  const ringRadius = Math.round(radius * 0.98);

  return (
    <div className="absolute left-1/2 top-1/2" style={{ width: 0, height: 0 }}>
      {/* the track: everything aboard spins together, around the centre
          point this zero-size div sits on */}
      <div className="ring-track absolute inset-0" style={{ transformOrigin: "0 0" }}>
        {ordered.map((agent, i) => (
          <RingNode
            key={agent.name}
            agent={agent}
            angle={total > 0 ? (360 / total) * i : 0}
            radius={ringRadius}
            deckUrl={deckUrl}
            size={agent.tier === "main" || agent.tier === "head" ? 44 : 28}
            showModel={agent.tier === "main" || agent.tier === "head"}
          />
        ))}
      </div>
      {!loading && agents.length === 0 ? (
        <span
          className="num absolute whitespace-nowrap text-[9px] tracking-wide"
          style={{
            color: INK_DIM,
            top: ringRadius + 34,
            transform: "translateX(-50%)",
          }}
        >
          {data?.state === "agents offline" ? "AGENT DECK OFFLINE" : ""}
        </span>
      ) : null}
    </div>
  );
}
