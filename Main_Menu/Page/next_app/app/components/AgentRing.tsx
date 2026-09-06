"use client";

import { useState } from "react";
import { useAgentRoster, type AgentNode } from "../lib/agents";

/** The agent ring - one real node per agent, read live from the Agent
    Deck (2026-09-06, replaces the decorative 30-glyph placeholder ring).

    Two circles: main-tier agents (plus the head) on the inner ring, each
    a little bigger with its model id printed just below it inside the
    ring; sub-agents on the outer ring as small circles. A node glows
    amber while its agent has unread messages; hovering shows the agent
    name; clicking lands in that agent's Agent Deck chat.

    The ring is deliberately static (no spin): hover and click are real
    controls now, and a moving target is hostile to both. */

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

export function AgentRing({ radius }: { radius: number }) {
  const { data, loading } = useAgentRoster();
  const agents = data?.state === "ok" ? data.agents : [];
  const deckUrl = data?.deck_url ?? "/workspace";

  // Main-tier + head agents take the inner circle; subs the outer one.
  const inners = agents.filter((a) => a.tier === "main" || a.tier === "head");
  const subs = agents.filter((a) => a.tier !== "main" && a.tier !== "head");

  const innerRadius = Math.round(radius * 0.55);
  const outerRadius = Math.round(radius * 0.95);

  return (
    <div className="absolute left-1/2 top-1/2" style={{ width: 0, height: 0 }}>
      {inners.map((agent, i) => {
        const angle = inners.length > 0 ? (360 / inners.length) * i : 0;
        return (
          <div
            key={agent.name}
            className="absolute"
            style={{
              transform: `rotate(${angle}deg) translate(${innerRadius}px) rotate(${-angle}deg) translate(-50%, -50%)`,
            }}
          >
            <AgentNodeCircle
              agent={agent}
              deckUrl={deckUrl}
              size={agent.tier === "main" ? 52 : 46}
              showModel
            />
          </div>
        );
      })}
      {subs.map((agent, i) => {
        const angle = subs.length > 0 ? (360 / subs.length) * i : 0;
        return (
          <div
            key={agent.name}
            className="absolute"
            style={{
              transform: `rotate(${angle}deg) translate(${outerRadius}px) rotate(${-angle}deg) translate(-50%, -50%)`,
            }}
          >
            <AgentNodeCircle agent={agent} deckUrl={deckUrl} size={32} showModel={false} />
          </div>
        );
      })}
      {!loading && agents.length === 0 ? (
        <span
          className="num absolute whitespace-nowrap text-[9px] tracking-wide"
          style={{
            color: INK_DIM,
            top: outerRadius + 26,
            transform: "translateX(-50%)",
          }}
        >
          {data?.state === "agents offline" ? "AGENT DECK OFFLINE" : ""}
        </span>
      ) : null}
    </div>
  );
}
