"use client";

import TopNav from "@/components/TopNav";
import TrackRow from "@/components/TrackRow";
import { useResource, useSubmit } from "@/lib/api";
import { useEffect, useState } from "react";

type TrackKey = "A" | "B";

interface Topic {
  id: number;
  name: string;
  stack_area: string;
  status: string;
  track: TrackKey;
  position: number;
  progress: number;
  target_date: string | null;
  source_doc: string | null;
  group: string | null;
}

interface PlanResponse {
  state: string;
  tracks: {
    A: Topic[];
    B: Topic[];
  };
  week: {
    week_start: string;
    focus_a: string;
    focus_b: string;
    note: string;
  } | null;
}

interface NewTopic {
  name: string;
  stack_area: "core" | "drip" | "capture";
  track: TrackKey;
  target_date: string | null;
  group: string | null;
}

export default function PlanPage() {
  const { data, error, loading } = useResource<PlanResponse>("/api/learning/plan");

  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [form, setForm] = useState<NewTopic>({
    name: "",
    stack_area: "core",
    track: "A",
    target_date: null,
    group: null,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const { submit, submitting } = useSubmit<Topic>("/api/learning/topics", "POST");

  useEffect(() => {
    if (data) {
      setPlan(data);
    }
  }, [data]);

  if (loading) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-dim animate-pulse motion-reduce:animate-none">
            Loading plan...
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

  if (!plan) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-dim border border-term-border rounded p-4">
            No plan data available.
          </div>
        </main>
      </div>
    );
  }

  async function addTopic() {
    if (!form.name.trim() || submitting) {
      return;
    }

    const result = await submit(form);

    if (result.error) {
      setFormError(result.error);
      return;
    }

    setFormError(null);

    if (result.data) {
      const created = result.data;

      setPlan((prev) => {
        if (!prev) {
          return prev;
        }

        const nextTracks = { ...prev.tracks };
        nextTracks[created.track] = [...nextTracks[created.track], created];

        return {
          ...prev,
          tracks: nextTracks,
        };
      });
    }

    setForm({
      name: "",
      stack_area: "core",
      track: "A",
      target_date: null,
      group: null,
    });
  }

  function renderTrack(track: TrackKey) {
    if (!plan) return null;
    const topics = plan.tracks[track];

    return (
      <section className="border border-term-border rounded p-4">
        <h2 className="text-term-cyan mb-3">&gt; TRACK {track}</h2>

        {topics.length === 0 ? (
          <div className="text-term-dim">No topics in this track yet</div>
        ) : (
          <div className="space-y-2">
            {topics.map((topic) => (
              <TrackRow
                key={topic.id}
                name={topic.name}
                status={topic.status}
                progress={topic.progress}
              />
            ))}
          </div>
        )}
      </section>
    );
  }

  return (
    <div className="min-h-screen">
      <TopNav />

      <main className="p-6 max-w-5xl mx-auto space-y-6">
        <h1 className="text-term-green text-2xl">&gt; PLAN</h1>

        {plan.week ? (
          <section className="border border-term-border rounded p-4">
            <h2 className="text-term-cyan mb-3">&gt; WEEK</h2>

            <div className="grid md:grid-cols-3 gap-3 text-sm">
              <div className="border border-term-border rounded p-3">
                <div className="text-term-dim text-xs mb-1">Week start</div>
                <div className="text-term-fg">{plan.week.week_start}</div>
              </div>

              <div className="border border-term-border rounded p-3">
                <div className="text-term-dim text-xs mb-1">Focus A</div>
                <div className="text-term-fg">{plan.week.focus_a}</div>
              </div>

              <div className="border border-term-border rounded p-3">
                <div className="text-term-dim text-xs mb-1">Focus B</div>
                <div className="text-term-fg">{plan.week.focus_b}</div>
              </div>
            </div>

            {plan.week.note ? (
              <div className="text-term-dim text-sm mt-3">{plan.week.note}</div>
            ) : null}
          </section>
        ) : null}

        <section className="border border-term-border rounded p-4">
          <h2 className="text-term-cyan mb-3">&gt; ADD TOPIC</h2>

          <div className="grid md:grid-cols-4 gap-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Topic name"
              className="bg-term-bg border border-term-border rounded px-3 py-2 text-term-fg"
            />

            <select
              value={form.stack_area}
              onChange={(e) =>
                setForm({ ...form, stack_area: e.target.value as NewTopic["stack_area"] })
              }
              className="bg-term-bg border border-term-border rounded px-3 py-2 text-term-fg"
            >
              <option value="core">core</option>
              <option value="drip">drip</option>
              <option value="capture">capture</option>
            </select>

            <select
              value={form.track}
              onChange={(e) => setForm({ ...form, track: e.target.value as TrackKey })}
              className="bg-term-bg border border-term-border rounded px-3 py-2 text-term-fg"
            >
              <option value="A">Track A</option>
              <option value="B">Track B</option>
            </select>

            <button
              onClick={addTopic}
              disabled={submitting}
              className="border border-term-green text-term-green rounded px-3 py-2 hover:bg-term-green hover:text-black motion-reduce:transition-none disabled:opacity-50"
            >
              {submitting ? "Adding..." : "Add"}
            </button>
          </div>

          {formError ? (
            <div className="text-term-red text-sm mt-3">Error: {formError}</div>
          ) : null}
        </section>

        {renderTrack("A")}
        {renderTrack("B")}
      </main>
    </div>
  );
}
