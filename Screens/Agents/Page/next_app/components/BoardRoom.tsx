"use client";

import { Fragment, useRef, useState } from "react";
import type { DragEvent, FormEvent } from "react";
import IdeaCard from "./IdeaCard";
import {
  useSubmit,
  type CreateIdeaInput,
  type Idea,
  type IdeaEnvelope,
  type IdeaStatus,
  type MoveIdeaInput,
} from "../lib/api";

const COLUMNS: { status: IdeaStatus; label: string }[] = [
  { status: "ideas", label: "Ideas" },
  { status: "todo", label: "To Do" },
  { status: "in_progress", label: "In Progress" },
  { status: "done", label: "Done" },
];

function compareIdeas(a: Idea, b: Idea): number {
  const left = a.order_index;
  const right = b.order_index;

  if (left !== null && right !== null && left !== right) {
    return left - right;
  }

  if (left !== null && right === null) {
    return -1;
  }

  if (left === null && right !== null) {
    return 1;
  }

  return a.key.localeCompare(b.key, undefined, { numeric: true });
}

function numericOrder(idea: Idea, fallback: number): number {
  if (typeof idea.order_index === "number" && Number.isFinite(idea.order_index)) {
    return idea.order_index;
  }

  return fallback;
}

function orderForDrop(target: Idea[], index: number): number {
  if (target.length === 0) {
    return 1;
  }

  if (index <= 0) {
    const first = numericOrder(target[0], 1);
    return first - 1;
  }

  if (index >= target.length) {
    const last = numericOrder(target[target.length - 1], target.length);
    return last + 1;
  }

  const prev = numericOrder(target[index - 1], index - 1);
  const next = numericOrder(target[index], index + 1);

  if (next <= prev) {
    return prev + 0.5;
  }

  return (prev + next) / 2;
}

export default function BoardRoom({
  ideas,
  loading,
  error,
  reload,
  selectedIdeaId,
  onSelectIdea,
}: {
  ideas: Idea[];
  loading: boolean;
  error: string | null;
  reload: () => void;
  selectedIdeaId: string | null;
  onSelectIdea: (ideaId: string | null) => void;
}) {
  const [newTitle, setNewTitle] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [dragIdeaId, setDragIdeaId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<{ status: IdeaStatus; index: number } | null>(null);
  const justDragged = useRef(false);

  const create = useSubmit<CreateIdeaInput, IdeaEnvelope>("/api/agents/ideas", "POST");
  const move = useSubmit<MoveIdeaInput, IdeaEnvelope>("", "PATCH");

  const grouped = COLUMNS.map((column) => ({
    ...column,
    items: ideas.filter((idea) => idea.status === column.status).sort(compareIdeas),
  }));

  if (loading && ideas.length === 0) {
    return (
      <section className="deck-panel flex h-full items-center justify-center p-6">
        <p className="text-sm text-deck-dim">Loading board...</p>
      </section>
    );
  }

  if (error && ideas.length === 0) {
    return (
      <section className="deck-panel flex h-full flex-col gap-3 p-6">
        <p className="section-label">Board</p>
        <p className="text-sm text-deck-alert">{error}</p>
        <button
          type="button"
          onClick={reload}
          className="w-fit border border-deck-line px-3 py-2 text-sm text-deck-text hover:border-deck-copper"
        >
          Retry
        </button>
      </section>
    );
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const title = newTitle.trim();
    if (!title || create.loading) {
      return;
    }

    setActionError(null);
    setNotice(null);

    const result = await create.submit({ title, source: "user" });

    if (result.error) {
      setActionError(result.error);
      return;
    }

    if (!result.data?.ok) {
      setActionError(result.data?.problem ?? "Could not create the idea.");
      return;
    }

    setNewTitle("");

    if (result.data.duplicate) {
      setNotice("That exact idea already exists. Showing the existing card.");
    } else if (result.data.duplicate_warning) {
      setNotice(
        `Possible duplicate of ${result.data.duplicate_warning.key}: ${result.data.duplicate_warning.title}`
      );
    }

    reload();
  }

  async function moveIdea(id: string, status: IdeaStatus, orderIndex: number) {
    setActionError(null);
    setNotice(null);

    const result = await move.submit(
      { status, order_index: orderIndex },
      `/api/agents/ideas/${id}/status`
    );

    if (result.error) {
      setActionError(result.error);
      return;
    }

    if (!result.data?.ok) {
      setActionError(result.data?.problem ?? "Could not move the idea.");
      return;
    }

    reload();
  }

  function handleCardClick(id: string) {
    if (justDragged.current) {
      return;
    }

    onSelectIdea(id === selectedIdeaId ? null : id);
  }

  function handleDragStart(event: DragEvent<HTMLDivElement>, idea: Idea) {
    justDragged.current = false;
    setDragIdeaId(idea.id);
    setDropTarget(null);

    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", idea.id);
  }

  function handleDragEnd() {
    justDragged.current = true;

    window.setTimeout(() => {
      justDragged.current = false;
    }, 200);

    setDragIdeaId(null);
    setDropTarget(null);
  }

  function handleColumnDragOver(event: DragEvent<HTMLDivElement>, status: IdeaStatus) {
    if (!dragIdeaId) {
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = "move";

    const length = grouped.find((column) => column.status === status)?.items.length ?? 0;

    setDropTarget((previous) => {
      if (previous && previous.status === status && previous.index === length) {
        return previous;
      }

      return { status, index: length };
    });
  }

  function handleCardDragOver(
    event: DragEvent<HTMLDivElement>,
    status: IdeaStatus,
    index: number,
    idea: Idea
  ) {
    if (!dragIdeaId || idea.id === dragIdeaId) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "move";

    const rect = event.currentTarget.getBoundingClientRect();
    const before = event.clientY < rect.top + rect.height / 2;

    setDropTarget({
      status,
      index: index + (before ? 0 : 1),
    });
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, status: IdeaStatus) {
    event.preventDefault();

    const id = dragIdeaId;
    if (!id) {
      return;
    }

    const displayed = grouped.find((column) => column.status === status)?.items ?? [];
    const withoutDragged = displayed.filter((idea) => idea.id !== id);

    let index = dropTarget && dropTarget.status === status ? dropTarget.index : displayed.length;

    const originalIndex = displayed.findIndex((idea) => idea.id === id);
    if (originalIndex !== -1 && originalIndex < index) {
      index -= 1;
    }

    if (index < 0) {
      index = 0;
    }

    if (index > withoutDragged.length) {
      index = withoutDragged.length;
    }

    const orderIndex = orderForDrop(withoutDragged, index);

    setDropTarget(null);
    setDragIdeaId(null);

    void moveIdea(id, status, orderIndex);
  }

  return (
    <section className="deck-panel flex h-full min-h-0 flex-col gap-3 p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="section-label">Room</p>
          <h2 className="text-lg font-semibold text-deck-text">Board</h2>
        </div>

        <p className="num text-xs text-deck-dim">
          {ideas.length} idea{ideas.length === 1 ? "" : "s"}
        </p>
      </header>

      <form onSubmit={handleCreate} className="flex gap-2">
        <input
          value={newTitle}
          onChange={(event) => setNewTitle(event.target.value)}
          placeholder="Capture an idea"
          aria-label="New idea title"
          className="min-w-0 flex-1 border border-deck-line bg-deck-raised px-3 py-2 text-sm text-deck-text placeholder:text-deck-dim focus:border-deck-copper focus:outline-none"
        />

        <button
          type="submit"
          disabled={create.loading || newTitle.trim().length === 0}
          className="border border-deck-line px-3 py-2 text-sm text-deck-text enabled:hover:border-deck-copper disabled:opacity-50"
        >
          {create.loading ? "Saving..." : "Add"}
        </button>
      </form>

      {error ? (
        <p className="text-sm text-deck-alert">
          {error}{" "}
          <button type="button" onClick={reload} className="underline">
            Retry
          </button>
        </p>
      ) : null}

      {actionError ? <p className="text-sm text-deck-alert">{actionError}</p> : null}
      {notice ? <p className="text-sm text-deck-slate">{notice}</p> : null}
      {loading && ideas.length > 0 ? <p className="text-xs text-deck-dim">Refreshing...</p> : null}
      {ideas.length === 0 && !loading && !error ? (
        <p className="text-sm text-deck-dim">No ideas captured yet.</p>
      ) : null}

      <div className="grid min-h-0 flex-1 grid-cols-4 gap-3 max-[1100px]:grid-cols-2 max-[560px]:grid-cols-1">
        {grouped.map((column) => {
          const isDropColumn = dropTarget?.status === column.status;

          return (
            <div
              key={column.status}
              onDragOver={(event) => handleColumnDragOver(event, column.status)}
              onDrop={(event) => handleDrop(event, column.status)}
              className={`flex min-h-[180px] flex-col rounded border bg-deck-panel ${
                isDropColumn ? "border-deck-copper" : "border-deck-line"
              }`}
            >
              <header className="flex items-center justify-between border-b border-deck-line px-3 py-2">
                <p className="section-label">{column.label}</p>
                <p className="num text-xs text-deck-dim">{column.items.length}</p>
              </header>

              <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-auto p-2">
                {column.items.length === 0 ? (
                  <p className="text-xs text-deck-dim">No ideas in this column.</p>
                ) : null}

                {column.items.map((idea, index) => (
                  <Fragment key={idea.id}>
                    {isDropColumn && dropTarget?.index === index ? (
                      <div className="h-0.5 shrink-0 bg-deck-copper" aria-hidden="true" />
                    ) : null}

                    <IdeaCard
                      idea={idea}
                      selected={idea.id === selectedIdeaId}
                      onSelect={() => handleCardClick(idea.id)}
                      onDragStart={(event) => handleDragStart(event, idea)}
                      onDragEnd={handleDragEnd}
                      onDragOver={(event) => handleCardDragOver(event, column.status, index, idea)}
                    />
                  </Fragment>
                ))}

                {isDropColumn && dropTarget?.index === column.items.length ? (
                  <div className="h-0.5 shrink-0 bg-deck-copper" aria-hidden="true" />
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
