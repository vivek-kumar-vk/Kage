"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import AgentCard from "../../components/AgentCard";
import BoardRoom from "../../components/BoardRoom";
import IdeaDetail from "../../components/IdeaDetail";
import Navigator from "../../components/Navigator";
import RunsStub from "../../components/RunsStub";
import { useResource, type IdeasResponse, type Selection, type Workspace } from "../../lib/api";

function StatePanel({
  title,
  children,
  onRetry,
}: {
  title: string;
  children: ReactNode;
  onRetry?: () => void;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <section className="deck-panel w-full max-w-xl p-6">
        <p className="section-label">Status</p>
        <h1 className="mt-2 text-lg font-semibold text-deck-text">{title}</h1>
        <div className="mt-3 text-sm text-deck-dim">{children}</div>

        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 border border-deck-line px-3 py-2 text-sm text-deck-text hover:border-deck-copper"
          >
            Retry
          </button>
        ) : null}
      </section>
    </main>
  );
}

function PanePanel({
  title,
  children,
  onRetry,
}: {
  title: string;
  children: ReactNode;
  onRetry?: () => void;
}) {
  return (
    <section className="deck-panel flex h-full min-h-0 flex-col gap-3 p-4">
      <p className="section-label">Context</p>
      <h2 className="text-base font-semibold text-deck-text">{title}</h2>
      <div className="text-sm text-deck-dim">{children}</div>

      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="w-fit border border-deck-line px-3 py-2 text-sm text-deck-text hover:border-deck-copper"
        >
          Retry
        </button>
      ) : null}
    </section>
  );
}

function CenterPlaceholder({ title, copy }: { title: string; copy: string }) {
  return (
    <section className="deck-panel flex h-full min-h-0 flex-col gap-3 p-4">
      <p className="section-label">Open room</p>
      <h2 className="text-lg font-semibold text-deck-text">{title}</h2>
      <p className="text-sm text-deck-dim">{copy}</p>
    </section>
  );
}

export default function HomePage() {
  const workspace = useResource<Workspace>("/api/agents/workspace");
  const board = useResource<IdeasResponse>("/api/agents/ideas");

  const [selection, setSelection] = useState<Selection>({ kind: "room", id: "board" });
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);
  const [navigatorOpen, setNavigatorOpen] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      if (navigatorOpen) {
        setNavigatorOpen(false);
        return;
      }

      if (contextOpen) {
        setContextOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigatorOpen, contextOpen]);

  function handleSelect(next: Selection) {
    setSelection(next);
    setSelectedIdeaId(null);
    setNavigatorOpen(false);
    setContextOpen(next.kind === "agent");
  }

  function handleSelectIdea(ideaId: string | null) {
    setSelectedIdeaId(ideaId);
    setContextOpen(ideaId !== null);
  }

  function closeIdeaDetail() {
    setSelectedIdeaId(null);
    setContextOpen(false);
  }

  if (workspace.loading) {
    return <StatePanel title="Loading">Loading workspace...</StatePanel>;
  }

  if (workspace.error) {
    return (
      <StatePanel title="Error" onRetry={workspace.reload}>
        {workspace.error}
      </StatePanel>
    );
  }

  const workspaceData = workspace.data;

  if (!workspaceData || (workspaceData.rooms.length === 0 && workspaceData.agents.length === 0)) {
    return (
      <StatePanel title="Empty" onRetry={workspace.reload}>
        No rooms or agents are available yet.
      </StatePanel>
    );
  }

  const selectedIdea = board.data?.ideas.find((idea) => idea.id === selectedIdeaId) ?? null;

  const selectedAgent =
    selection.kind === "agent"
      ? workspaceData.agents.find((agent) => agent.name === selection.id) ?? null
      : null;

  let center: ReactNode;
  let right: ReactNode;

  if (selection.kind === "room" && selection.id === "board") {
    center = (
      <BoardRoom
        ideas={board.data?.ideas ?? []}
        loading={board.loading}
        error={board.error}
        reload={board.reload}
        selectedIdeaId={selectedIdeaId}
        onSelectIdea={handleSelectIdea}
      />
    );

    if (selectedIdea) {
      right = <IdeaDetail idea={selectedIdea} onClose={closeIdeaDetail} onReload={board.reload} />;
    } else if (selectedIdeaId && board.loading) {
      right = <PanePanel title="Loading">Loading idea...</PanePanel>;
    } else if (selectedIdeaId && board.error) {
      right = (
        <PanePanel title="Error" onRetry={board.reload}>
          {board.error}
        </PanePanel>
      );
    } else if (selectedIdeaId) {
      right = (
        <PanePanel title="Not found" onRetry={board.reload}>
          The selected idea is no longer on the board.
        </PanePanel>
      );
    } else {
      right = <PanePanel title="Board context">Select a card to see its detail and comments.</PanePanel>;
    }
  } else if (selection.kind === "room" && selection.id === "runs") {
    center = <RunsStub />;
    right = <PanePanel title="Runs context">No context is available for Runs yet.</PanePanel>;
  } else if (selection.kind === "agent") {
    if (selectedAgent) {
      center = (
        <CenterPlaceholder
          title={selectedAgent.name}
          copy="Agent rooms land in V2. The right pane shows the agent card."
        />
      );
      right = <AgentCard agent={selectedAgent} />;
    } else {
      center = <CenterPlaceholder title="Agent room" copy="Agent rooms land in V2." />;
      right = (
        <PanePanel title="Agent not found" onRetry={workspace.reload}>
          The selected agent is not in the workspace roster.
        </PanePanel>
      );
    }
  } else {
    center = <CenterPlaceholder title="Room" copy="This room is not available yet." />;
    right = <PanePanel title="Context">Select a room or agent.</PanePanel>;
  }

  return (
    <div className="flex min-h-screen flex-col">
      {navigatorOpen ? (
        <div
          className="fixed inset-0 z-30 bg-[rgba(0,0,0,0.55)] min-[561px]:hidden"
          onClick={() => setNavigatorOpen(false)}
          aria-hidden="true"
        />
      ) : null}

      {contextOpen ? (
        <div
          className="fixed inset-0 z-30 bg-[rgba(0,0,0,0.55)] min-[821px]:hidden"
          onClick={() => setContextOpen(false)}
          aria-hidden="true"
        />
      ) : null}

      <header className="flex items-center justify-between gap-2 border-b border-deck-line bg-deck-panel px-3 py-2 min-[821px]:hidden">
        <button
          type="button"
          onClick={() => setNavigatorOpen((value) => !value)}
          className="hidden max-[560px]:inline-flex border border-deck-line px-2 py-1 text-xs text-deck-text hover:border-deck-copper"
        >
          Navigator
        </button>

        <span className="deck-wordmark text-sm">[AGENT DECK]</span>

        <button
          type="button"
          onClick={() => setContextOpen((value) => !value)}
          className="inline-flex border border-deck-line px-2 py-1 text-xs text-deck-text hover:border-deck-copper"
        >
          Context
        </button>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[260px_minmax(0,1fr)_320px] gap-3 p-3 max-[1100px]:grid-cols-[240px_minmax(0,1fr)_280px] max-[820px]:grid-cols-[220px_minmax(0,1fr)] max-[560px]:grid-cols-1">
        <div
          className={`min-h-0 overflow-auto max-[560px]:fixed max-[560px]:inset-x-0 max-[560px]:top-0 max-[560px]:z-40 max-[560px]:max-h-[75vh] max-[560px]:overflow-auto max-[560px]:border-b max-[560px]:border-deck-line max-[560px]:bg-deck-bg max-[560px]:p-3 ${
            navigatorOpen ? "" : "max-[560px]:hidden"
          }`}
        >
          <Navigator workspace={workspaceData} selected={selection} onSelect={handleSelect} />
        </div>

        <section className="min-h-0 overflow-auto">{center}</section>

        <aside
          className={`min-h-0 overflow-auto max-[820px]:fixed max-[820px]:right-0 max-[820px]:top-0 max-[820px]:z-40 max-[820px]:h-full max-[820px]:w-[320px] max-[820px]:max-w-[90vw] max-[820px]:overflow-auto max-[820px]:border-l max-[820px]:border-deck-line max-[820px]:bg-deck-bg max-[820px]:p-3 ${
            contextOpen ? "" : "max-[820px]:hidden"
          }`}
        >
          {right}
        </aside>
      </main>

      <a href="/" className="office-pill">
        ⌂ Pixel Office
      </a>
    </div>
  );
}
