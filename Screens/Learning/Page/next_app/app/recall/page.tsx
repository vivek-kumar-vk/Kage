"use client";

import { useState } from "react";
import { post, useResource } from "@/lib/api";

type Card = {
  review_id: number | null; card_id: number; front: string; parts: (string | null)[];
  tag: string; tether: string | null; ease: number; due: string | null;
};
type RecallData = {
  due_count: number; current: Card | null; queue: number; done_today: number;
  forecast: { day: string; due: number }[];
  accuracy: number | null; ease_avg: number | null;
  leeches: { front: string; ease: number; review_id: number }[];
  studio: Card[];
};

const GRADES = [
  { key: "again", label: "Again", next: "TODAY", cls: "danger" },
  { key: "hard", label: "Hard", next: "+1 DAY", cls: "" },
  { key: "good", label: "Good", next: "+3 DAYS", cls: "" },
  { key: "easy", label: "Easy", next: "+7 DAYS", cls: "" },
];

// His 5-part recall format (Master Context): (1) elevator answer,
// (2) likely follow-up, (3) trap follow-up, (4) real-world example,
// (5) resume connection.
const PART_LABELS = ["ELEVATOR", "FOLLOW-UP", "TRAP", "REAL WORLD", "RESUME"];

export default function RecallPage() {
  const { data, error, loading, refetch } = useResource<RecallData>("/api/learning/recall");
  const [revealed, setRevealed] = useState(0);
  const [grading, setGrading] = useState(false);

  if (loading) return <div className="state-loading">shuffling the queue…</div>;
  if (error) return <div className="state-error">{error}</div>;
  if (!data) return null;

  const card = data.current;
  const maxForecast = Math.max(1, ...data.forecast.map((f) => f.due));

  async function grade(g: string) {
    if (!card?.review_id) return;
    setGrading(true);
    try {
      await post(`/api/learning/review/${card.review_id}/grade`, { grade: g });
      setRevealed(0);
      refetch();
    } finally {
      setGrading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <div className="page-head">
        <div>
          <div className="kicker">Active recall · retrieval beats re-reading</div>
          <h1 className="display">Recall</h1>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 34 }}>
            {data.forecast.map((f) => (
              <div key={f.day} title={`${f.day}: ${f.due} due`} style={{
                width: 13, borderRadius: "3px 3px 0 0",
                height: `${20 + 80 * (f.due / maxForecast)}%`,
                background: f.due > 0 ? "var(--ember)" : "#241f19",
                opacity: f.due > 0 ? 0.85 : 1,
              }} />
            ))}
          </div>
          <div className="mono-micro">next<br />7 days<br />load</div>
          {data.studio.length > 0 && <span className="chip violet">card studio · {data.studio.length} waiting</span>}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 270px", gap: 20, flex: 1, alignItems: "start" }}>
        <section className="panel raised" style={{
          display: "flex", flexDirection: "column", padding: "34px 44px",
          background: "linear-gradient(160deg, #1b1712, #141110 70%)",
          minHeight: 480,
        }}>
          {card ? (
            <>
              <div style={{ display: "flex", gap: 8 }}>
                <span className="chip ghost">{card.tether || "card"}</span>
                <span className="chip ghost">
                  {data.done_today + 1} of {data.due_count + data.done_today}
                </span>
                {card.ease < 2 && <span className="chip amber">leech · ease {card.ease}</span>}
              </div>
              <div style={{
                fontFamily: "var(--font-fraunces), serif", fontWeight: 420,
                fontSize: 32, lineHeight: 1.3, margin: "22px 0 8px", maxWidth: 720,
              }}>
                {card.front}
              </div>
              <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                {card.parts.map((part, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, alignItems: "baseline", fontSize: 14 }}>
                    <span style={{
                      fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--faint)",
                      width: 86, flex: "none", letterSpacing: "0.12em",
                    }}>{PART_LABELS[i] ?? `PART ${i + 1}`}</span>
                    {i < revealed ? (
                      <span style={{ color: "var(--dim)" }}>{part}</span>
                    ) : (
                      <span style={{ color: "var(--faint)", fontSize: 12.5, cursor: "pointer" }}
                        onClick={() => setRevealed(i + 1)}>
                        reveal next →
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <div style={{
                marginTop: "auto", display: "flex", gap: 10, paddingTop: 24,
              }}>
                {GRADES.map((g) => (
                  <button key={g.key} disabled={grading}
                    onClick={() => grade(g.key)}
                    className={g.key === "good" ? "btn primary" : "btn quiet"}
                    style={{ flex: 1, flexDirection: "column", gap: 2, padding: "11px 0" }}>
                    <span style={{ fontSize: 13.5 }}>{g.label}</span>
                    <span className="mono-micro" style={{ fontSize: 9 }}>{g.next}</span>
                  </button>
                ))}
              </div>
              {revealed < card.parts.length && (
                <div style={{ color: "var(--faint)", fontSize: 11.5, marginTop: 10 }}>
                  say it out loud before revealing — that struggle is the learning
                </div>
              )}
            </>
          ) : (
            <div style={{ margin: "auto", textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-fraunces), serif", fontSize: 28, marginBottom: 8 }}>
                Queue clear.
              </div>
              <div style={{ color: "var(--dim)", fontSize: 13.5 }}>
                {data.due_count === 0
                  ? "Nothing is due. Next cards arrive as rooms get finished."
                  : "All caught up."}
              </div>
            </div>
          )}
        </section>

        <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="panel" style={{ padding: "15px 17px" }}>
            <div className="panel-label">Today&apos;s sweep</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: 10, fontSize: 12.5, color: "var(--dim)" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>due</span><b style={{ color: "var(--bone)" }}>{data.due_count} cards</b></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>done today</span><b style={{ color: "var(--bone)" }}>{data.done_today}</b></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>accuracy (30d)</span><b style={{ color: "var(--bone)" }}>{data.accuracy !== null ? `${data.accuracy}%` : "—"}</b></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>avg ease</span><b style={{ color: "var(--bone)" }}>{data.ease_avg ?? "—"}</b></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>leeches</span>
                <b style={{ color: data.leeches.length ? "var(--amber)" : "var(--bone)" }}>
                  {data.leeches.length}
                </b></div>
            </div>
          </div>

          <div className="panel" style={{ padding: "15px 17px" }}>
            <div className="panel-head" style={{ padding: 0 }}>
              <div className="panel-label">Card studio</div>
              {data.studio.length > 0 && <span className="chip jade">{data.studio.length} new</span>}
            </div>
            {data.studio.length === 0 && (
              <div style={{ color: "var(--faint)", fontSize: 12, padding: "10px 0" }}>
                nothing waiting — cards appear as quizmaster mints them
              </div>
            )}
            {data.studio.map((c) => (
              <div key={c.card_id} style={{ borderTop: "1px solid var(--hairline)", padding: "11px 0" }}>
                <div style={{ color: "var(--bone)", fontSize: 12.5, fontWeight: 500 }}>{c.front}</div>
                <div style={{ color: "var(--faint)", fontSize: 11, marginTop: 2 }}>
                  {c.parts.filter(Boolean).length} parts · waiting for your accept
                </div>
                <div style={{ display: "flex", gap: 6, marginTop: 7 }}>
                  <span className="chip jade clickable" onClick={async () => {
                    await post(`/api/learning/studio/${c.card_id}/accept`);
                    refetch();
                  }}>accept</span>
                  <span className="chip clickable" onClick={async () => {
                    await post(`/api/learning/studio/${c.card_id}/discard`);
                    refetch();
                  }}>discard</span>
                </div>
              </div>
            ))}
            <div style={{ display: "flex", gap: 9, marginTop: 10, fontSize: 11.5, color: "var(--dim)", alignItems: "flex-start" }}>
              <span className="track-dot violet" style={{ width: 6, height: 6, marginTop: 5 }} />
              <span>quizmaster drafts cards from rooms you finished — nothing enters your queue until you accept it.</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
