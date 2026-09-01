"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  useSubmit,
  type AddCommentInput,
  type Idea,
  type IdeaEnvelope,
  type IdeaPriority,
} from "../lib/api";

const priorityClasses: Record<IdeaPriority, string> = {
  low: "border border-deck-line text-deck-dim",
  medium: "border border-deck-slate text-deck-slate",
  high: "border border-deck-copper text-deck-copper",
  critical: "border border-deck-alert text-deck-alert",
};

export default function IdeaDetail({
  idea,
  onClose,
  onReload,
}: {
  idea: Idea;
  onClose: () => void;
  onReload: () => void;
}) {
  const [text, setText] = useState("");
  const { submit, loading, error } = useSubmit<AddCommentInput, IdeaEnvelope>(
    `/api/agents/ideas/${idea.id}/comments`,
    "POST"
  );

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = text.trim();
    if (!trimmed || loading) {
      return;
    }

    const result = await submit({ text: trimmed, author: "user" });

    if (!result.error) {
      setText("");
      onReload();
    }
  }

  return (
    <section
      role="dialog"
      aria-label={`Idea detail for ${idea.key}`}
      className="deck-panel flex h-full min-h-0 flex-col gap-3 p-4"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="section-label">Idea detail</p>
          <p className="num mt-1 font-mono text-xs text-deck-dim">{idea.key}</p>
          <h2 className="mt-1 text-base font-semibold text-deck-text">{idea.title}</h2>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="border border-deck-line px-2 py-1 text-xs text-deck-dim hover:border-deck-copper hover:text-deck-text"
        >
          Close
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-auto">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`px-1.5 py-0.5 uppercase tracking-wide ${priorityClasses[idea.priority]}`}>
            {idea.priority}
          </span>
          <span className="border border-deck-line px-1.5 py-0.5 text-deck-dim">{idea.status}</span>
          <span className="border border-deck-line px-1.5 py-0.5 text-deck-dim">
            {idea.source === "ai" ? "AI" : "User"}
          </span>
        </div>

        {idea.note ? <p className="mt-3 text-sm text-deck-dim">{idea.note}</p> : null}

        <dl className="mt-3 grid grid-cols-[80px_1fr] gap-y-1 text-xs text-deck-dim">
          <dt>Area</dt>
          <dd>{idea.area || "—"}</dd>

          <dt>Added</dt>
          <dd className="num font-mono">{idea.added_at ?? "—"}</dd>

          <dt>Updated</dt>
          <dd className="num font-mono">{idea.updated_at ?? "—"}</dd>
        </dl>

        <div className="mt-4">
          <p className="section-label">Comments</p>

          {idea.comments.length === 0 ? (
            <p className="mt-2 text-sm text-deck-dim">No comments yet.</p>
          ) : (
            <div className="mt-2 flex flex-col gap-2">
              {idea.comments.map((comment) => (
                <article key={comment.id} className="border border-deck-line bg-deck-raised p-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className={comment.author === "ai" ? "text-deck-slate" : "text-deck-copper"}>
                      {comment.author === "ai" ? "AI" : "User"}
                    </span>
                    <span className="num font-mono text-deck-dim">{comment.created_at ?? ""}</span>
                  </div>

                  <p className="mt-1 text-sm text-deck-text">{comment.text}</p>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label className="section-label" htmlFor="idea-comment">
          Add comment
        </label>

        <textarea
          id="idea-comment"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={3}
          placeholder="Write a comment"
          className="w-full resize-none border border-deck-line bg-deck-raised px-3 py-2 text-sm text-deck-text placeholder:text-deck-dim focus:border-deck-copper focus:outline-none"
        />

        <button
          type="submit"
          disabled={loading || text.trim().length === 0}
          className="w-fit border border-deck-line px-3 py-2 text-sm text-deck-text enabled:hover:border-deck-copper disabled:opacity-50"
        >
          {loading ? "Posting..." : "Post comment"}
        </button>

        {error ? <p className="text-sm text-deck-alert">{error}</p> : null}
      </form>
    </section>
  );
}
