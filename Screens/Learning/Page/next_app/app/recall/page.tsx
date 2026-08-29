"use client";

import TopNav from "@/components/TopNav";
import RecallCard from "@/components/RecallCard";
import { useResource, useSubmit } from "@/lib/api";
import { useEffect, useState } from "react";

interface Card {
  review_id: number;
  id: number;
  front: string;
  parts: string[];
  tag: string;
  tether?: string | null;
}

interface RecallResponse {
  counts: {
    today: number;
    pending: number;
    all: number;
  };
  queues: {
    today: Card[];
    pending: Card[];
    all: Card[];
  };
}

type Grade = "again" | "hard" | "good" | "easy";

export default function RecallPage() {
  const { data, error, loading } = useResource<RecallResponse>("/api/learning/recall");

  const [recall, setRecall] = useState<RecallResponse | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setRecall(data);
    }
  }, [data]);

  const currentCard =
    recall && recall.queues.today.length > 0
      ? recall.queues.today[0]
      : recall && recall.queues.pending.length > 0
        ? recall.queues.pending[0]
        : null;

  const gradePath = currentCard
    ? `/api/learning/reviews/${currentCard.review_id}/grade`
    : "/api/learning/ask";

  const { submit, submitting } = useSubmit<{ state: string }>(gradePath, "POST");

  useEffect(() => {
    setRevealed(false);
  }, [currentCard?.review_id]);

  async function refresh() {
    try {
      const res = await fetch("/api/learning/recall");
      const json = (await res.json()) as RecallResponse;

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      setRecall(json);
      setRefreshError(null);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err));
    }
  }

  async function grade(gradeValue: Grade) {
    if (!currentCard || submitting) {
      return;
    }

    const result = await submit({ grade: gradeValue });

    if (result.error) {
      setActionError(result.error);
      return;
    }

    setActionError(null);
    setRevealed(false);
    await refresh();
  }

  if (loading) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-dim animate-pulse motion-reduce:animate-none">
            Loading recall...
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-red border border-term-red rounded p-4">
            Error: {error}
          </div>
        </main>
      </div>
    );
  }

  if (!recall) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-dim border border-term-border rounded p-4">
            No recall data available.
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <TopNav />

      <main className="p-6 max-w-5xl mx-auto space-y-6">
        <h1 className="text-term-green text-2xl">&gt; RECALL</h1>

        <section className="grid md:grid-cols-3 gap-4">
          <div className="border border-term-border rounded p-4">
            <div className="text-term-dim text-sm mb-2">Due today</div>
            <div className="text-3xl text-term-green">{recall.counts.today}</div>
          </div>

          <div className="border border-term-border rounded p-4">
            <div className="text-term-dim text-sm mb-2">Pending</div>
            <div className="text-3xl text-term-amber">{recall.counts.pending}</div>
          </div>

          <div className="border border-term-border rounded p-4">
            <div className="text-term-dim text-sm mb-2">All</div>
            <div className="text-3xl text-term-cyan">{recall.counts.all}</div>
          </div>
        </section>

        {actionError ? (
          <div className="text-term-red border border-term-red rounded p-4">
            Error: {actionError}
          </div>
        ) : null}

        {refreshError ? (
          <div className="text-term-amber border border-term-amber rounded p-4">
            Refresh warning: {refreshError}
          </div>
        ) : null}

        {currentCard ? (
          <section className="border border-term-border rounded p-4 space-y-4">
            <RecallCard
              front={currentCard.front}
              parts={revealed ? currentCard.parts : []}
              tag={currentCard.tag}
              tether={currentCard.tether}
            />

            {!revealed ? (
              <button
                onClick={() => setRevealed(true)}
                className="border border-term-cyan text-term-cyan rounded px-4 py-2 hover:bg-term-cyan hover:text-black motion-reduce:transition-none"
              >
                Reveal
              </button>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <button
                  onClick={() => grade("again")}
                  disabled={submitting}
                  className="border border-term-red text-term-red rounded px-4 py-2 hover:bg-term-red hover:text-black motion-reduce:transition-none disabled:opacity-50"
                >
                  Again
                </button>

                <button
                  onClick={() => grade("hard")}
                  disabled={submitting}
                  className="border border-term-amber text-term-amber rounded px-4 py-2 hover:bg-term-amber hover:text-black motion-reduce:transition-none disabled:opacity-50"
                >
                  Hard
                </button>

                <button
                  onClick={() => grade("good")}
                  disabled={submitting}
                  className="border border-term-green text-term-green rounded px-4 py-2 hover:bg-term-green hover:text-black motion-reduce:transition-none disabled:opacity-50"
                >
                  Good
                </button>

                <button
                  onClick={() => grade("easy")}
                  disabled={submitting}
                  className="border border-term-cyan text-term-cyan rounded px-4 py-2 hover:bg-term-cyan hover:text-black motion-reduce:transition-none disabled:opacity-50"
                >
                  Easy
                </button>
              </div>
            )}
          </section>
        ) : (
          <section className="border border-term-border rounded p-4">
            <div className="text-term-dim">No cards due right now</div>
          </section>
        )}
      </main>
    </div>
  );
}
