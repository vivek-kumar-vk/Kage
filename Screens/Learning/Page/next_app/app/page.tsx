"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { fmtDate, post, useResource } from "@/lib/api";

type Today = {
  greeting: { headline: string; agent: string };
  hero: {
    room_id: number; room: string; room_full: string; module: string;
    track: string; color: string; step_id: number; step_title: string;
    step_no: number; minutes: number; mastery: number;
  } | null;
  plan: { kind: string; label: string; meta: string; minutes: number;
          room_id: number | null; color: string | null; first: boolean }[];
  rhythm: { day: string; minutes: number; done: boolean }[];
  streak: { count: number; grace: number };
  due_cards: number;
  weak_spot: { room_id: number; room: string; accuracy: number; misses: number } | null;
  crew_line: string;
  week_minutes: number;
  week_budget: number;
};

const DURATIONS = [15, 25, 45];

export default function TodayPage() {
  const { data, error, loading, refetch } = useResource<Today>("/api/learning/today");
  const router = useRouter();
  const [minutes, setMinutes] = useState(25);
  const [starting, setStarting] = useState(false);

  async function startSession(roomId: number | null) {
    setStarting(true);
    try {
      const res = await post<{ session_id: number }>("/api/learning/session/start", {
        room_id: roomId,
        planned_minutes: minutes,
      });
      if (roomId) {
        router.push(
          `/room?id=${roomId}&focus=1&session=${res.session_id}&minutes=${minutes}`,
        );
      } else {
        router.push("/recall");
      }
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <div className="state-loading">loading today…</div>;
  if (error) return <div className="state-error">{error}</div>;
  if (!data) return null;

  const d = new Date();
  const prime = d.getHours() >= 17 || d.getHours() < 4 ? "evening" :
    d.getHours() >= 12 ? "afternoon" : "morning";

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <div className="page-head">
        <div>
          <div className="kicker">{fmtDate(d.toISOString().slice(0, 10))} · {prime}</div>
          <h1 className="display">
            {data.greeting.headline.split(/(finishing [^.]+|Fresh start: [^.]+)/).map(
              (part, i) =>
                part.startsWith("finishing ") || part.startsWith("Fresh start:") ? (
                  <em key={i}>{part}</em>
                ) : (
                  <span key={i}>{part}</span>
                ),
            )}
          </h1>
          <p className="lede">
            Everything is decided. Start the session — the timer stays visible and
            the rest of the screen steps back.
          </p>
        </div>
        <span className="chip ghost">
          week budget · {data.week_minutes} / {data.week_budget} min
        </span>
      </div>

      {data.hero && (
        <section className="panel raised" style={{
          display: "flex", gap: 36, padding: "30px 34px", alignItems: "center",
          background: "linear-gradient(135deg, #1b1712 0%, #151210 55%)",
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
              <span className="chip ember">
                <span className="track-dot" style={{ width: 7, height: 7 }} />
                {data.hero.track}
              </span>
              <span className="chip">{data.hero.module}</span>
              <span className="chip">{data.hero.room} · step {data.hero.step_no}</span>
            </div>
            <h2 style={{
              fontFamily: "var(--font-fraunces), serif", fontWeight: 420,
              fontSize: 26, lineHeight: 1.25,
            }}>
              {data.hero.step_title}
            </h2>
            <div style={{ marginTop: 10, color: "var(--dim)", fontSize: 13.5 }}>
              ~{data.hero.minutes} min · mastery {data.hero.mastery}%
            </div>
          </div>
          <div style={{
            flex: "none", width: 270, borderLeft: "1px solid var(--hairline)",
            paddingLeft: 32, display: "flex", flexDirection: "column", gap: 12,
          }}>
            <div className="panel-label">Focus session</div>
            <div className="seg">
              {DURATIONS.map((m) => (
                <button key={m} className={m === minutes ? "on" : ""}
                  onClick={() => setMinutes(m)}>
                  {m}
                </button>
              ))}
            </div>
            <button className="btn primary" disabled={starting}
              onClick={() => startSession(data.hero!.room_id)}>
              ▶ {starting ? "starting…" : "Start learning"}
            </button>
            <div className="mono-micro">auto-logs · gentle chime at the end</div>
          </div>
        </section>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 16 }}>
        <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="panel-label">Rhythm · 14 days</div>
          <div style={{ display: "flex", gap: 5 }}>
            {data.rhythm.map((r) => (
              <div key={r.day} title={`${r.day}: ${r.minutes} min`} style={{
                width: 9, height: 22, borderRadius: 3,
                background: r.done ? "var(--ember)" : "#241f19",
                opacity: r.done ? (r.minutes > 30 ? 1 : 0.7) : 1,
              }} />
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 9, color: "var(--dim)", fontSize: 12.5 }}>
            <span className="chip jade">streak {data.streak.count}</span>
            <span>{data.streak.grace} grace day banked</span>
          </div>
        </div>

        <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="panel-label">Due cards</div>
          <div style={{ fontFamily: "var(--font-fraunces), serif", fontSize: 30 }}>
            {data.due_cards}
          </div>
          <div style={{ color: "var(--dim)", fontSize: 12.5 }}>
            ≈{Math.max(2, Math.round(data.due_cards * 0.75))} min sweep after the session
          </div>
        </div>

        {data.weak_spot ? (
          <div className="panel" style={{
            padding: "18px 20px", display: "flex", flexDirection: "column", gap: 8,
            borderColor: "rgba(242,169,59,.28)",
          }}>
            <div className="panel-label" style={{ color: "var(--amber)" }}>Weak spot detected</div>
            <div style={{ fontSize: 15, lineHeight: 1.35 }}>
              {data.weak_spot.room} — checkpoint missed, accuracy {data.weak_spot.accuracy}%
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 9, color: "var(--dim)", fontSize: 12.5 }}>
              <span>fix it before it spreads</span>
              <a href={`/room?id=${data.weak_spot.room_id}`}
                style={{ marginLeft: "auto", color: "var(--amber)", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".08em", textDecoration: "none" }}>
                FIX THIS →
              </a>
            </div>
          </div>
        ) : (
          <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="panel-label">Weak spots</div>
            <div className="state-empty" style={{ padding: 0 }}>nothing detected — keep proving steps</div>
          </div>
        )}
      </div>

      <section className="panel" style={{ marginTop: 16 }}>
        <div className="panel-head">
          <div className="panel-label">Shortlist · picked for you</div>
          <span className="mono-micro">
            {data.plan.reduce((a, p) => a + p.minutes, 0)} min total
          </span>
        </div>
        <div style={{ padding: "6px 0 2px" }}>
          {data.plan.map((p, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 14,
              padding: "14px 20px", borderTop: "1px solid var(--hairline)",
              fontSize: 13.5,
            }}>
              <span className="mono-micro" style={{ width: 18 }}>0{i + 1}</span>
              <span className={`track-dot ${p.color ?? "dim"}`} />
              {p.room_id ? (
                <a href={`/room?id=${p.room_id}`} style={{ color: "var(--bone)", fontWeight: 500, textDecoration: "none" }}>
                  {p.label}
                </a>
              ) : (
                <a href="/recall" style={{ color: "var(--bone)", fontWeight: 500, textDecoration: "none" }}>
                  {p.label}
                </a>
              )}
              <span style={{ marginLeft: "auto", color: "var(--faint)", fontSize: 12, display: "flex", gap: 12 }}>
                <span>{p.meta}</span><span>~{p.minutes} min</span>
                {p.first && <span className="chip ember">up first</span>}
              </span>
            </div>
          ))}
          {data.plan.length === 0 && (
            <div className="state-empty">nothing queued — add rooms in Path</div>
          )}
        </div>
      </section>

      <div style={{
        marginTop: 18, display: "flex", alignItems: "center", gap: 11,
        padding: "13px 18px", border: "1px dashed rgba(167,139,250,.3)",
        borderRadius: 12, background: "var(--violet-dim)", color: "var(--dim)",
        fontSize: 13,
      }}>
        <span className="track-dot violet" style={{ width: 6, height: 6 }} />
        <span className="violet-tag">warden</span>
        <span>{data.crew_line}</span>
      </div>

      {data.due_cards > 0 && (
        <div style={{ marginTop: 14, textAlign: "center" }}>
          <button className="btn quiet" onClick={() => startSession(null)}>
            Or just sweep {data.due_cards} recall cards →
          </button>
        </div>
      )}
    </div>
  );
}
