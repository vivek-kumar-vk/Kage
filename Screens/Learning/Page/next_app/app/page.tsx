"use client";

import TopNav from "@/components/TopNav";
import StatsBar from "@/components/StatsBar";
import { useResource } from "@/lib/api";

interface TodayResponse {
  streak: {
    days: number;
    last_studied: string | null;
  };
  week: {
    minutes: number;
    target_minutes: number;
  };
  today_plan: {
    track_a: string;
    track_b: string;
    capture: string;
  };
  recent_activity: Array<{
    date: string;
    minutes: number;
    topic: string;
    notes: string | null;
  }>;
  due_cards: number;
}

export default function TodayPage() {
  const { data, error, loading } = useResource<TodayResponse>("/api/learning/today");

  if (loading) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-dim animate-pulse motion-reduce:animate-none">
            Loading today...
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

  if (!data) {
    return (
      <div className="min-h-screen">
        <TopNav />
        <main className="p-6 max-w-5xl mx-auto">
          <div className="text-term-dim border border-term-border rounded p-4">
            No data available.
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <TopNav />

      <main className="p-6 max-w-5xl mx-auto space-y-6">
        <h1 className="text-term-green text-2xl">&gt; TODAY</h1>

        <section className="grid md:grid-cols-3 gap-4">
          <div className="border border-term-border rounded p-4">
            <div className="text-term-dim text-sm mb-2">Streak</div>
            <div className="text-3xl text-term-green">{data.streak.days}</div>
            <div className="text-term-dim text-xs mt-2">
              Last studied: {data.streak.last_studied ?? "Never"}
            </div>
          </div>

          <div className="border border-term-border rounded p-4">
            <div className="text-term-dim text-sm mb-3">Week minutes</div>
            <StatsBar
              label="minutes"
              value={data.week.minutes}
              target={data.week.target_minutes}
            />
          </div>

          <div className="border border-term-border rounded p-4">
            <div className="text-term-dim text-sm mb-2">Due cards</div>
            <div className="text-3xl text-term-cyan">{data.due_cards}</div>
          </div>
        </section>

        <section className="border border-term-border rounded p-4">
          <h2 className="text-term-cyan mb-3">&gt; TODAY&apos;S PLAN</h2>

          <div className="grid md:grid-cols-3 gap-3 text-sm">
            <div className="border border-term-border rounded p-3">
              <div className="text-term-dim text-xs mb-1">Track A</div>
              <div className="text-term-fg">{data.today_plan.track_a || "No plan set"}</div>
            </div>

            <div className="border border-term-border rounded p-3">
              <div className="text-term-dim text-xs mb-1">Track B</div>
              <div className="text-term-fg">{data.today_plan.track_b || "No plan set"}</div>
            </div>

            <div className="border border-term-border rounded p-3">
              <div className="text-term-dim text-xs mb-1">Capture</div>
              <div className="text-term-fg">{data.today_plan.capture}</div>
            </div>
          </div>
        </section>

        <section className="border border-term-border rounded p-4">
          <h2 className="text-term-cyan mb-3">&gt; RECENT ACTIVITY</h2>

          {data.recent_activity.length === 0 ? (
            <div className="text-term-dim">No sessions logged yet</div>
          ) : (
            <div className="space-y-2">
              {data.recent_activity.map((item, index) => (
                <div
                  key={index}
                  className="border border-term-border rounded p-3 flex items-center justify-between gap-4"
                >
                  <div>
                    <div className="text-term-fg">{item.topic}</div>
                    <div className="text-term-dim text-xs">{item.date}</div>
                    {item.notes ? (
                      <div className="text-term-dim text-xs mt-1">{item.notes}</div>
                    ) : null}
                  </div>

                  <div className="text-term-green">{item.minutes}m</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
