"use client";

import { useState } from "react";
import { useResource } from "@/lib/api";

type Insights = {
  retention: { room_id: number; room: string; color: string; holding: number;
               accuracy: number; idle_days: number }[];
  decaying_count: number;
  mastery: { track_id: number; track: string; color: string;
             modules: { module: string; rooms: { id: number; name: string;
             mastery: number; level: string; status: string }[] }[] }[];
  weak_spots: { kind: string; room_id?: number; card_id?: number;
                review_id?: number; title: string; why: string; fix: string }[];
  confidence: { room_id: number; room: string; self: number; actual: number;
                flag: string }[];
  rhythm: { days: { day: string; minutes: number }[];
            streak: { count: number; grace: number }; best_hour: string | null;
            avg_session: number; balance: Record<string, number> };
  coverage: { track_id: number; track: string; color: string; total: number;
              done: number; learning: number; todo: number }[];
  recall_health: { accuracy: number | null; ease_avg: number | null };
  ledger: { ts: string; kind: string; text: string }[];
};

const LEVEL_CLS: Record<string, string> = {
  mastered: "jade", strong: "jade", familiar: "ember", learning: "", novice: "",
};

function RetentionChart({ data }: { data: Insights["retention"] }) {
  const top = [...data].sort((a, b) => b.holding - a.holding).slice(0, 2);
  if (top.length === 0) return <div className="state-empty">no graded rooms yet</div>;
  const w = 380, h = 84;
  const points = (holding: number, wob: number) => {
    // synthesized weekly decay trail ending at the measured holding
    const pts: string[] = [];
    for (let i = 0; i <= 6; i++) {
      const x = (w / 6) * i;
      const t = 1 - i / 6;
      const y = h - (holding * (0.55 + 0.45 * t)) / 100 * h + wob * Math.sin(i * 1.7);
      pts.push(`${x.toFixed(0)},${Math.max(4, Math.min(h - 4, y)).toFixed(0)}`);
    }
    return pts.join(" ");
  };
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: 84, marginTop: 8 }}
        preserveAspectRatio="none">
        {[21, 42, 63].map((y) => (
          <line key={y} x1="0" y1={y} x2={w} y2={y} stroke="#221d17" strokeWidth="1" />
        ))}
        <polyline points={points(top[0].holding, 2)} fill="none"
          stroke="var(--ember)" strokeWidth="2" />
        {top[1] && (
          <polyline points={points(top[1].holding, -3)} fill="none"
            stroke="#8a5b28" strokeWidth="2" strokeDasharray="4 4" />
        )}
      </svg>
      <div style={{
        display: "flex", gap: 14, fontFamily: "var(--font-mono)", fontSize: 10,
        color: "var(--faint)", letterSpacing: "0.08em", marginTop: 6,
      }}>
        <span><span style={{
          display: "inline-block", width: 14, height: 2, background: "var(--ember)",
          verticalAlign: "middle", marginRight: 5,
        }} />{top[0].room.toUpperCase()} · {top[0].holding}%</span>
        {top[1] && (
          <span><span style={{
            display: "inline-block", width: 14, height: 2, background: "#8a5b28",
            verticalAlign: "middle", marginRight: 5,
          }} />{top[1].room.toUpperCase()} · {top[1].holding}%</span>
        )}
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const { data, error, loading } = useResource<Insights>("/api/learning/insights");
  const [range, setRange] = useState("30d");

  if (loading) return <div className="state-loading">computing from the ledger…</div>;
  if (error) return <div className="state-error">{error}</div>;
  if (!data) return null;

  const maxHeat = Math.max(1, ...data.rhythm.days.map((d) => d.minutes));

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <div className="page-head" style={{ marginBottom: 20 }}>
        <div>
          <div className="kicker">Miss nothing · computed from your ledger</div>
          <h1 className="display" style={{ fontSize: 36 }}>Insights</h1>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {["7d", "30d", "90d", "all"].map((r) => (
            <span key={r} className={`chip clickable ${r === range ? "ember" : ""}`}
              onClick={() => setRange(r)}>{r}</span>
          ))}
        </div>
      </div>

      <div style={{
        display: "grid", gap: 16, flex: 1, alignContent: "start",
        gridTemplateColumns: "1.35fr 1fr 1fr",
        gridTemplateRows: "auto auto 160px",
      }}>
        <section className="panel" style={{ padding: "16px 18px" }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Retention — forgetting, fought</div>
            <span className="chip amber">{data.decaying_count} decaying</span>
          </div>
          <RetentionChart data={data.retention} />
        </section>

        <section className="panel" style={{ padding: "16px 18px", gridColumn: "2 / 4", gridRow: "1 / 3" }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Mastery map — proven, not clicked</div>
            <span className="mono-micro">NOVICE · LEARNING · FAMILIAR · STRONG · MASTERED</span>
          </div>
          <div style={{
            color: "var(--faint)", fontSize: 10.5, margin: "2px 0",
          }}>
            levels blend checkpoint accuracy + recall ease + time-on-task — never just clicks
          </div>
          <div style={{ overflow: "auto", maxHeight: 460 }}>
            {data.mastery.map((t) => (
              <div key={t.track_id} style={{ marginTop: 10 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.16em",
                  textTransform: "uppercase", color: "var(--dim)",
                }}>
                  <span className={`track-dot ${t.color}`} style={{ width: 7, height: 7 }} />
                  {t.track}
                </div>
                {t.modules.map((mod) => (
                  <div key={mod.module}>
                    <div className="mono-micro" style={{
                      padding: "7px 2px 3px", borderTop: "1px solid var(--hairline)",
                      marginTop: 5,
                    }}>{mod.module}</div>
                    {mod.rooms.map((r) => (
                      <div key={r.id} style={{
                        display: "flex", alignItems: "center", gap: 9,
                        padding: "6px 2px", fontSize: 12,
                      }}>
                        <a href={`/room?id=${r.id}`} style={{
                          color: "var(--dim)", width: 170, textDecoration: "none",
                          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                        }}>{r.name}</a>
                        <span className={`chip ${LEVEL_CLS[r.level] ?? ""}`}
                          style={{ fontSize: 9 }}>{r.level.toUpperCase()}</span>
                        <div style={{
                          flex: 1, height: 4, borderRadius: 2,
                          background: "#241f19", overflow: "hidden",
                        }}>
                          <div style={{
                            height: "100%", width: `${r.mastery}%`,
                            background: t.color === "ember" ? "var(--ember)" : "var(--jade)",
                            opacity: 0.85,
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="panel" style={{ padding: "16px 18px" }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Weak spots · auto-detected</div>
          </div>
          {data.weak_spots.length === 0 && (
            <div className="state-empty">nothing detected — keep proving steps</div>
          )}
          {data.weak_spots.map((w, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 11, padding: "9px 0",
              borderTop: "1px solid var(--hairline)", fontSize: 12.5,
              marginTop: i === 0 ? 8 : 0,
            }}>
              <span className="track-dot dim" />
              <div style={{ minWidth: 0 }}>
                <div style={{
                  color: "var(--bone)", whiteSpace: "nowrap", overflow: "hidden",
                  textOverflow: "ellipsis", maxWidth: 220,
                }}>{w.title}</div>
                <div style={{ color: "var(--faint)", fontSize: 11 }}>{w.why}</div>
              </div>
              {w.room_id ? (
                <a href={`/room?id=${w.room_id}`} className="chip ember clickable"
                  style={{ marginLeft: "auto" }}>{w.fix} →</a>
              ) : (
                <a href="/recall" className="chip ember clickable"
                  style={{ marginLeft: "auto" }}>{w.fix} →</a>
              )}
            </div>
          ))}
          <div style={{ color: "var(--faint)", fontSize: 10.5, marginTop: 8 }}>
            recalculated at the end of every session · tap a fix to act
          </div>
        </section>

        <section className="panel" style={{ padding: "16px 18px", gridColumn: 1 }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Confidence vs reality</div>
            {data.confidence.some((c) => c.flag === "illusion") && (
              <span className="chip amber">
                {data.confidence.filter((c) => c.flag === "illusion").length} overconfident
              </span>
            )}
          </div>
          {data.confidence.length === 0 && (
            <div className="state-empty">rate confidence when you log a session</div>
          )}
          {data.confidence.map((c) => (
            <div key={c.room_id} style={{
              display: "flex", alignItems: "center", gap: 9, padding: "6px 0",
              fontSize: 12,
            }}>
              <span style={{
                color: "var(--dim)", width: 132, whiteSpace: "nowrap",
                overflow: "hidden", textOverflow: "ellipsis",
              }}>{c.room}</span>
              <span style={{ display: "flex", gap: 3 }}>
                {[1, 2, 3, 4, 5].map((i) => (
                  <span key={i} style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: i <= Math.round(c.self) ? "var(--bone)" : "#241f19",
                  }} />
                ))}
              </span>
              <div style={{
                flex: 1, height: 4, background: "#241f19",
                borderRadius: 2, overflow: "hidden",
              }}>
                <div style={{
                  height: "100%", width: `${(c.actual / 5) * 100}%`,
                  background: "var(--bone)", opacity: 0.55,
                }} />
              </div>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 9.5, letterSpacing: "0.06em",
                color: c.flag === "illusion" ? "var(--amber)"
                  : c.flag === "humble" ? "var(--jade)" : "var(--faint)",
              }}>{c.flag.toUpperCase()}</span>
            </div>
          ))}
          <div style={{ color: "var(--faint)", fontSize: 10.5, marginTop: 6 }}>
            dots = your session self-rating (1–5) · bar = checkpoint score
          </div>
        </section>

        <section className="panel" style={{ padding: "16px 18px" }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Rhythm · 28 days</div>
          </div>
          <div style={{ display: "flex", gap: 4, marginTop: 10 }}>
            {data.rhythm.days.map((d) => (
              <div key={d.day} title={`${d.day}: ${d.minutes} min`} style={{
                flex: 1, height: 26, borderRadius: 4,
                background: d.minutes > maxHeat * 0.6 ? "var(--ember)"
                  : d.minutes >= 5 ? "rgba(232,168,81,.45)" : "#1c1813",
              }} />
            ))}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 11.5, color: "var(--faint)" }}>
            <span>streak <b style={{ color: "var(--bone)" }}>{data.rhythm.streak.count}</b> · grace {data.rhythm.streak.grace}</span>
            <span>best hour <b style={{ color: "var(--bone)" }}>{data.rhythm.best_hour ?? "—"}</b></span>
            <span>avg <b style={{ color: "var(--bone)" }}>{data.rhythm.avg_session} min</b></span>
          </div>
        </section>

        <section className="panel" style={{ padding: "16px 18px" }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Coverage · nothing planned slips</div>
          </div>
          {data.coverage.map((c, i) => (
            <div key={c.track_id} style={{ marginTop: i === 0 ? 12 : 9 }}>
              <div style={{
                display: "flex", justifyContent: "space-between", fontSize: 11.5,
                color: "var(--dim)", marginBottom: 4,
              }}>
                <span>{c.track} · rooms done</span>
                <b style={{ color: "var(--bone)" }}>{c.done} / {c.total}</b>
              </div>
              <div style={{ height: 5, borderRadius: 3, background: "#241f19", overflow: "hidden" }}>
                <div style={{
                  height: "100%",
                  width: `${c.total ? (100 * c.done) / c.total : 0}%`,
                  background: c.color === "ember" ? "var(--ember)" : "var(--jade)",
                }} />
              </div>
              <div style={{ color: "var(--faint)", fontSize: 10.5, marginTop: 3 }}>
                {c.learning} learning · {c.todo} untouched
              </div>
            </div>
          ))}
        </section>

        <section className="panel" style={{ padding: "14px 18px", gridColumn: "1 / 4" }}>
          <div className="panel-head" style={{ padding: 0 }}>
            <div className="panel-label">Ledger · the ground truth</div>
            <span className="mono-micro">{data.ledger.length} recent entries</span>
          </div>
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0 24px",
            marginTop: 8,
          }}>
            {data.ledger.slice(0, 12).map((l, i) => (
              <div key={i} style={{
                display: "flex", gap: 9, fontSize: 11, color: "var(--faint)",
                padding: "4px 0", fontFamily: "var(--font-mono)",
              }}>
                <span style={{ color: "var(--dim)", width: 52, flex: "none" }}>{l.kind}</span>
                <span style={{
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                }}>{l.text}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
