"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import BoardRoom from "../../components/BoardRoom";
import IdeaDetail from "../../components/IdeaDetail";
import RunsStub from "../../components/RunsStub";
import DeckRail, { type DeckSelection } from "../../components/deck/DeckRail";
import AgentChat from "../../components/deck/AgentChat";
import ProfilePanel from "../../components/deck/ProfilePanel";
import {
  deriveAgentStates,
  useLiveEvents,
  useWorkspace,
} from "../../lib/office";
import { useResource, type IdeasResponse } from "../../lib/api";

export default function DeckPage() {
  const workspace = useWorkspace();
  const { events, status } = useLiveEvents();
  const states = useMemo(() => deriveAgentStates(events), [events]);
  const board = useResource<IdeasResponse>("/api/agents/ideas");

  const [selection, setSelection] = useState<DeckSelection>({ kind: "room", id: "board" });
  const [profileName, setProfileName] = useState<string | null>(null);
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (profileName) {
        setProfileName(null);
        return;
      }
      if (selectedIdeaId) setSelectedIdeaId(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [profileName, selectedIdeaId]);

  const departments = workspace.data?.departments ?? [];
  const agents = workspace.data?.agents ?? [];
  const selectedAgent =
    selection.kind === "agent" ? agents.find((a) => a.name === selection.id) ?? null : null;
  const profileAgent = profileName ? agents.find((a) => a.name === profileName) ?? null : null;
  const accentOf = (name: string) =>
    departments.find((d) => d.id === agents.find((a) => a.name === name)?.department)?.color ??
    "#A08762";

  const latest = events.length > 0 ? events[events.length - 1] : null;
  const liveDot =
    status === "live"
      ? "status-dot status-dot-running"
      : status === "offline"
        ? "status-dot"
        : "status-dot status-dot-idle";
  const liveDotStyle =
    status === "offline" ? { background: "var(--deck-alert)" } : undefined;

  const selectedIdea = board.data?.ideas.find((idea) => idea.id === selectedIdeaId) ?? null;

  let center: ReactNode;
  if (selection.kind === "agent") {
    center = selectedAgent ? (
      <AgentChat agent={selectedAgent} accent={accentOf(selectedAgent.name)} states={states} />
    ) : (
      <CenterNote title="Agent not found" copy="The roster may have changed — reload." />
    );
  } else if (selection.id === "board") {
    center = (
      <BoardRoom
        ideas={board.data?.ideas ?? []}
        loading={board.loading}
        error={board.error}
        reload={board.reload}
        selectedIdeaId={selectedIdeaId}
        onSelectIdea={setSelectedIdeaId}
      />
    );
  } else if (selection.id === "runs") {
    center = <RunsStub />;
  } else {
    center = <CenterNote title="Room" copy="This room is not available yet." />;
  }

  let right: ReactNode = null;
  if (profileAgent) {
    right = (
      <ProfilePanel
        agent={profileAgent}
        departments={departments}
        states={states}
        onClose={() => setProfileName(null)}
      />
    );
  } else if (selection.kind === "room" && selection.id === "board") {
    if (selectedIdea) {
      right = (
        <IdeaDetail
          idea={selectedIdea}
          onClose={() => setSelectedIdeaId(null)}
          onReload={board.reload}
        />
      );
    } else {
      right = <ContextNote copy="Select a card to see its detail and comments." />;
    }
  } else {
    right = <ContextNote copy="Pick an agent — their profile opens here." />;
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between gap-3 border-b-2 border-deck-line bg-deck-panel px-4 py-2">
        <div className="flex items-center gap-4">
          <span className="deck-wordmark text-sm">RUBRIC / AGENTS</span>
          <nav className="px-tabs" aria-label="Surfaces">
            <a href="/" className="px-tab">
              PIX-AGENTS
            </a>
            <span className="px-tab px-tab-active" aria-current="page">
              AGENT DECK
            </span>
          </nav>
        </div>

        <div className="flex min-w-0 items-center gap-3">
          {latest ? (
            <span className={`event-line${latest.sim ? " event-line-sim" : ""}`}>
              {latest.sim ? "SIM · " : ""}
              {latest.agent_name ? `${latest.agent_name} — ` : ""}
              {latest.text || latest.type}
            </span>
          ) : null}
          <span className="flex items-center gap-2 text-xs text-deck-dim">
            <span className={liveDot} style={liveDotStyle} />
            {status}
          </span>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[240px_minmax(0,1fr)_320px] max-[1000px]:grid-cols-[220px_minmax(0,1fr)_280px] max-[760px]:grid-cols-[200px_minmax(0,1fr)]">
        <aside className="deck-rail min-h-0 max-[760px]:hidden">
          <DeckRail
            departments={departments}
            agents={agents}
            states={states}
            selection={selection}
            onSelectAgent={(name) => {
              setSelection({ kind: "agent", id: name });
              setProfileName(name);
            }}
            onSelectRoom={(id) => {
              setSelection({ kind: "room", id });
              setProfileName(null);
              setSelectedIdeaId(null);
            }}
          />
        </aside>

        <section className="min-h-0 overflow-hidden bg-deck-bg">{center}</section>

        <aside className="profile-drawer min-h-0 overflow-hidden">{right}</aside>
      </main>
    </div>
  );
}

function CenterNote({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="px-panel max-w-md p-5">
        <p className="section-label">Center</p>
        <h2 className="mt-1 font-display text-lg">{title}</h2>
        <p className="mt-2 text-sm text-deck-dim">{copy}</p>
      </div>
    </div>
  );
}

function ContextNote({ copy }: { copy: string }) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="px-panel max-w-xs p-4 text-sm text-deck-dim">{copy}</div>
    </div>
  );
}
