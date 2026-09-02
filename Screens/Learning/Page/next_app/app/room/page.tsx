"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { post, useResource } from "@/lib/api";

type Checkpoint = {
  id: number; kind: string; question: string; options: string[];
  answer_idx: number | null; model_answer: string | null;
  answered: boolean; last_correct: number | null; last_self_grade: string | null;
};
type Step = {
  id: number; position: number; title: string; minutes: number; status: string;
  explain: string | null; realworld: string | null;
  lab: { objective: string | null; env: string | null; link: string | null;
         checklist: string[]; proof: string | null };
  checkpoints: Checkpoint[];
};
type RoomData = {
  id: number; name: string; short: string; module: string; track: string;
  track_id: number; color: string; status: string; feynman: string | null;
  mastery: number; level: string; steps: Step[];
  notes: { id: number; body: string; step_id: number | null; created_at: string }[];
  next_room_id: number | null;
};

function chime() {
  try {
    const ctx = new AudioContext();
    const notes = [523.25, 659.25, 783.99];
    notes.forEach((f, i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.frequency.value = f;
      o.type = "sine";
      g.gain.setValueAtTime(0.0001, ctx.currentTime + i * 0.18);
      g.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + i * 0.18 + 0.03);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + i * 0.18 + 0.9);
      o.connect(g).connect(ctx.destination);
      o.start(ctx.currentTime + i * 0.18);
      o.stop(ctx.currentTime + i * 0.18 + 1);
    });
  } catch { /* audio unavailable — silence is honest */ }
}

function SessionChip({ sessionId, minutes, onLogged }: {
  sessionId: number; minutes: number; onLogged: () => void;
}) {
  const [left, setLeft] = useState(minutes * 60);
  const [elapsed, setElapsed] = useState(0);
  const [logging, setLogging] = useState(false);
  const chimed = useRef(false);

  useEffect(() => {
    const t = setInterval(() => {
      setLeft((s) => Math.max(0, s - 1));
      setElapsed((s) => s + 1);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (left === 0 && !chimed.current) {
      chimed.current = true;
      chime();
    }
  }, [left]);

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  const done = left === 0;

  return (
    <div style={{
      position: "fixed", right: 24, bottom: 24, zIndex: 50,
      display: "flex", alignItems: "center", gap: 14,
      background: "var(--raised)", border: `1px solid ${done ? "var(--ember-line)" : "var(--hairline-2)"}`,
      borderRadius: 14, padding: "12px 18px",
      boxShadow: "0 18px 50px -18px rgba(0,0,0,.8)",
    }}>
      <span className="track-dot ember" style={{ width: 7, height: 7 }} />
      <div>
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: 20, letterSpacing: "0.08em",
          color: done ? "var(--ember)" : "var(--bone)",
        }}>{mm}:{ss}</div>
        <div className="mono-micro" style={{ fontSize: 8.5 }}>
          {done ? "session complete — log it" : "focus session"}
        </div>
      </div>
      <button className="btn primary small" disabled={logging}
        onClick={async () => {
          setLogging(true);
          try {
            await post(`/api/learning/session/${sessionId}/finish`, {
              actual_minutes: Math.max(1, Math.round(elapsed / 60)),
            });
            onLogged();
          } finally {
            setLogging(false);
          }
        }}>
        {done ? "log session" : "finish early"}
      </button>
    </div>
  );
}

function Beat({ label, chipClass, children, extra }: {
  label: string; chipClass: string; children: React.ReactNode; extra?: React.ReactNode;
}) {
  return (
    <section className="panel" style={{ padding: "16px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <span className={`chip ${chipClass}`}>{label}</span>
        {extra}
      </div>
      {children}
    </section>
  );
}

function CheckpointView({ ck, onDone }: { ck: Checkpoint; onDone: () => void }) {
  const [choice, setChoice] = useState<number | null>(null);
  const [result, setResult] = useState<{ correct: boolean } | null>(null);
  const [free, setFree] = useState("");
  const [model, setModel] = useState<string | null>(null);
  const [selfGraded, setSelfGraded] = useState(false);

  if (ck.kind === "mcq") {
    return (
      <div style={{
        border: "1px solid var(--hairline)", borderRadius: 10,
        padding: "12px 14px", fontSize: 13,
      }}>
        <div style={{ color: "var(--bone)", fontWeight: 500, marginBottom: 9 }}>{ck.question}</div>
        {ck.options.map((opt, i) => {
          const picked = choice === i;
          const right = result && i === ck.answer_idx!;
          const wrongPick = result && picked && !result.correct;
          return (
            <div key={i}
              onClick={() => !result && setChoice(i)}
              style={{
                display: "flex", gap: 8, padding: "5px 8px", borderRadius: 7,
                cursor: result ? "default" : "pointer",
                color: right ? "var(--jade)" : wrongPick ? "#e88a82" : picked ? "var(--bone)" : "var(--dim)",
                background: picked ? "var(--ember-dim)" : undefined,
              }}>
              <span>{right ? "✓" : wrongPick ? "✗" : picked ? "◉" : "○"}</span>
              <span>{opt}</span>
            </div>
          );
        })}
        {!result ? (
          <button className="btn quiet small" style={{ marginTop: 8 }}
            disabled={choice === null}
            onClick={async () => {
              const res = await post<{ correct: boolean }>(
                `/api/learning/checkpoint/${ck.id}/attempt`, { answer: String(choice) });
              setResult(res);
              onDone();
            }}>
            check answer
          </button>
        ) : (
          <div style={{ marginTop: 8, fontSize: 12, color: result.correct ? "var(--jade)" : "#e88a82" }}>
            {result.correct ? "correct — that's the retrieval win" : "not quite — the right one is marked; it'll come back in Recall"}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={{ color: "var(--bone)", fontWeight: 500, marginBottom: 8, fontSize: 13 }}>
        {ck.question}
      </div>
      <textarea style={{ width: "100%", height: 74, resize: "none", fontSize: 12.5 }}
        placeholder="answer in your own words…"
        value={free} onChange={(e) => setFree(e.target.value)} />
      {!model ? (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
          <button className="btn quiet small" disabled={!free.trim()}
            onClick={() => setModel(ck.model_answer ?? "")}>
            compare with model answer
          </button>
          <span style={{ color: "var(--faint)", fontSize: 11 }}>
            honesty beats hints — say it before you peek
          </span>
        </div>
      ) : (
        <div style={{
          borderLeft: "2px solid var(--ember)", padding: "2px 0 2px 12px",
          margin: "8px 0", color: "var(--dim)", fontSize: 12.5,
        }}>{model}</div>
      )}
      {model && !selfGraded && (
        <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
          <button className="btn small jade" style={{ border: "1px solid rgba(63,217,164,.35)", color: "var(--jade)" }}
            onClick={async () => {
              await post(`/api/learning/checkpoint/${ck.id}/attempt`,
                { answer: free, self_grade: "matched" });
              setSelfGraded(true); onDone();
            }}>I had it</button>
          <button className="btn quiet small"
            onClick={async () => {
              await post(`/api/learning/checkpoint/${ck.id}/attempt`,
                { answer: free, self_grade: "off" });
              setSelfGraded(true); onDone();
            }}>missed parts</button>
        </div>
      )}
      {selfGraded && (
        <div style={{ marginTop: 6, fontSize: 12, color: "var(--jade)" }}>
          logged — Quizmaster reads these weekly
        </div>
      )}
    </div>
  );
}

function RoomInner() {
  const params = useSearchParams();
  const id = Number(params.get("id"));
  const focus = params.get("focus") === "1";
  const sessionId = params.get("session");
  const sessionMinutes = Number(params.get("minutes") ?? 25);
  const { data, error, loading, refetch } = useResource<RoomData>(
    id ? `/api/learning/room/${id}` : null,
  );
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [proof, setProof] = useState("");
  const [checklist, setChecklist] = useState<Record<number, boolean>>({});
  const [note, setNote] = useState("");
  const [feynman, setFeynman] = useState<string | null>(null);

  useEffect(() => {
    if (focus) {
      document.body.classList.add("focus-mode");
      return () => document.body.classList.remove("focus-mode");
    }
  }, [focus]);

  useEffect(() => {
    if (data && activeStep === null) {
      const current = data.steps.find((s) => s.status === "current")
        ?? data.steps.find((s) => s.status === "todo")
        ?? data.steps[0];
      setActiveStep(current?.id ?? null);
      setFeynman(data.feynman);
    }
  }, [data, activeStep]);

  if (loading) return <div className="state-loading">opening room…</div>;
  if (error) return <div className="state-error">{error}</div>;
  if (!data) return null;

  const step = data.steps.find((s) => s.id === activeStep) ?? data.steps[0];
  const doneCount = data.steps.filter((s) => s.status === "done").length;
  const allChecked = step?.lab.checklist.every((_, i) => checklist[i]) ?? false;

  async function markDone() {
    if (!step) return;
    await post(`/api/learning/step/${step.id}/status`, { status: "done" });
    refetch();
  }

  return (
    <div>
      <div style={{
        display: "flex", alignItems: "flex-end", justifyContent: "space-between",
        marginBottom: 20, gap: 24,
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 9, color: "var(--faint)", fontSize: 12.5 }}>
            <a href="/path" style={{ color: "var(--faint)", textDecoration: "none" }}>Path</a>
            <span style={{ color: "#3a332a" }}>/</span>
            <span className={`track-dot ${data.color}`} style={{ width: 7, height: 7 }} />
            <span>{data.track}</span>
            <span style={{ color: "#3a332a" }}>/</span>
            <span>{data.module}</span>
            <span style={{ color: "#3a332a" }}>/</span>
            <b style={{ color: "var(--bone)", fontFamily: "var(--font-fraunces), serif", fontSize: 15 }}>
              {data.short}
            </b>
          </div>
          <div className="mono-micro" style={{ marginTop: 10 }}>
            STEP-BY-STEP · EXPLAIN → REAL WORLD → LAB → CHECKPOINT · {doneCount}/{data.steps.length} DONE · MASTERY {data.mastery}% ({data.level})
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {data.next_room_id && (
            <a href={`/room?id=${data.next_room_id}${focus ? "&focus=1" : ""}`}
              className="chip ghost clickable">next room →</a>
          )}
          <a href="/path" className="chip ghost clickable">back to path</a>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "236px 1fr 250px", gap: 20, alignItems: "start" }}>
        {/* step rail */}
        <nav className="panel" style={{ padding: "14px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
          <div className="panel-label" style={{ padding: "6px 8px 8px" }}>
            Steps · {data.steps.reduce((a, s) => a + s.minutes, 0)} min
          </div>
          {data.steps.map((s) => (
            <div key={s.id} onClick={() => setActiveStep(s.id)}
              style={{
                display: "flex", gap: 10, padding: "9px 10px", borderRadius: 9,
                cursor: "pointer",
                background: s.id === step?.id ? "var(--ember-dim)" : undefined,
              }}>
              <span style={{
                width: 19, height: 19, borderRadius: "50%", flex: "none",
                display: "grid", placeItems: "center",
                fontFamily: "var(--font-mono)", fontSize: 10, marginTop: 1,
                border: `1.5px solid ${s.status === "done" ? "rgba(63,217,164,.4)" : s.id === step?.id ? "var(--ember)" : "var(--hairline-2)"}`,
                color: s.status === "done" ? "var(--jade)" : s.id === step?.id ? "var(--ember)" : "var(--faint)",
                background: s.status === "done" ? "var(--jade-dim)" : undefined,
              }}>
                {s.status === "done" ? "✓" : s.position + 1}
              </span>
              <div>
                <div style={{
                  fontSize: 12.5,
                  color: s.status !== "todo" || s.id === step?.id ? "var(--bone)" : "var(--dim)",
                  fontWeight: s.id === step?.id ? 500 : 400,
                }}>{s.title}</div>
                <div style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 1 }}>
                  {s.minutes} min{s.status === "done" ? " · done" : s.status === "current" ? " · you are here" : ""}
                </div>
              </div>
            </div>
          ))}
        </nav>

        {/* beats */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          {step && (
            <>
              <Beat label={step.status === "done" ? "✓ explained" : "beat 1 · explain"}
                chipClass={step.status === "done" ? "jade" : ""}>
                <p style={{ color: "var(--dim)", fontSize: 13.5 }}>{step.explain}</p>
              </Beat>

              <Beat label="beat 2 · real world" chipClass="ember">
                <p style={{ color: "var(--bone)", fontSize: 14 }}>{step.realworld}</p>
              </Beat>

              <Beat label="beat 3 · lab" chipClass=""
                extra={<span className="chip">{step.lab.env ?? "your environment"}</span>}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 230px", gap: 16 }}>
                  <div>
                    <p style={{ color: "var(--dim)", fontSize: 13, marginBottom: 8 }}>{step.lab.objective}</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
                      {step.lab.checklist.map((item, i) => (
                        <label key={i} style={{
                          display: "flex", gap: 8, cursor: "pointer",
                          color: checklist[i] ? "var(--bone)" : "var(--dim)",
                        }}>
                          <input type="checkbox" checked={!!checklist[i]}
                            onChange={() => setChecklist((c) => ({ ...c, [i]: !c[i] }))}
                            style={{ accentColor: "var(--ember)" }} />
                          <span>{item}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div style={{
                      background: "var(--bg)", border: "1px solid var(--hairline-2)",
                      borderRadius: 10, padding: "10px 12px",
                      fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--faint)",
                    }}>
                      <b style={{
                        color: "var(--ember)", display: "block", marginBottom: 5,
                        letterSpacing: "0.1em", fontSize: 9.5,
                      }}>PROOF — PASTE &amp; IT&apos;S CHECKED</b>
                      <input style={{ width: "100%", fontFamily: "inherit", fontSize: 11 }}
                        placeholder="paste the command / output"
                        defaultValue={step.lab.proof ?? ""}
                        onChange={(e) => setProof(e.target.value)} />
                    </div>
                    {proof && proof !== (step.lab.proof ?? "") && (
                      <button className="btn quiet small" style={{ marginTop: 8 }}
                        onClick={async () => {
                          await post(`/api/learning/step/${step.id}/proof`, { text: proof });
                          refetch();
                        }}>save proof</button>
                    )}
                  </div>
                </div>
              </Beat>

              <Beat label="beat 4 · checkpoint" chipClass=""
                extra={<span className="chip ghost">skip is allowed — honestly tracked</span>}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                  {step.checkpoints.map((ck) => (
                    <CheckpointView key={ck.id} ck={ck} onDone={refetch} />
                  ))}
                </div>
              </Beat>

              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                {step.status !== "done" ? (
                  <button className="btn primary small" onClick={markDone}>
                    mark step done →
                  </button>
                ) : (
                  <span className="chip jade">step done</span>
                )}
                {step.lab.checklist.length > 0 && !allChecked && step.status !== "done" && (
                  <span style={{ color: "var(--faint)", fontSize: 11.5 }}>
                    checklist unfinished — done is allowed, Insights remembers
                  </span>
                )}
              </div>
            </>
          )}
        </div>

        {/* side */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="panel" style={{ padding: "14px 16px" }}>
            <div className="panel-label">Notes on this room</div>
            {data.notes.length === 0 && (
              <div style={{ color: "var(--faint)", fontSize: 12, padding: "8px 0" }}>
                nothing yet — capture the one-liners that stick
              </div>
            )}
            {data.notes.map((n) => (
              <div key={n.id} style={{
                fontSize: 12.5, color: "var(--dim)", padding: "8px 0",
                borderTop: "1px solid var(--hairline)",
              }}>
                <b style={{ color: "var(--bone)", fontWeight: 500, display: "block", fontSize: 12.5 }}>
                  {n.body}
                </b>
              </div>
            ))}
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <input style={{ flex: 1, fontSize: 12 }} placeholder="capture a note…"
                value={note} onChange={(e) => setNote(e.target.value)}
                onKeyDown={async (e) => {
                  if (e.key === "Enter" && note.trim()) {
                    await post(`/api/learning/room/${id}/note`, { body: note.trim() });
                    setNote(""); refetch();
                  }
                }} />
            </div>
          </div>

          <div className="panel" style={{ padding: "14px 16px" }}>
            <div className="panel-label">Feynman check</div>
            <div style={{ color: "var(--faint)", fontSize: 11, margin: "6px 0" }}>
              Explain this room in your own words. If you can&apos;t, you found the gap.
            </div>
            <textarea style={{ width: "100%", height: 84, resize: "none", fontSize: 12.5 }}
              placeholder={`${data.short} is…`}
              value={feynman ?? ""}
              onChange={(e) => setFeynman(e.target.value)} />
            <button className="btn quiet small" style={{ marginTop: 8 }}
              disabled={(feynman ?? "") === (data.feynman ?? "") || !feynman?.trim()}
              onClick={async () => {
                await post(`/api/learning/room/${id}/feynman`, { text: feynman });
                refetch();
              }}>save</button>
          </div>

          {sessionId && (
            <div className="panel raised" style={{ padding: "12px 16px" }}>
              <div className="panel-label" style={{ color: "var(--violet)" }}>tutor</div>
              <div style={{ color: "var(--dim)", fontSize: 12, marginTop: 6 }}>
                Stuck? The hint ladder is armed: nudge → hint → new angle → worked
                example. Live wiring lands with the crew build — for now, write the
                question in a note and come back.
              </div>
            </div>
          )}
        </div>
      </div>

      {sessionId && (
        <SessionChip sessionId={Number(sessionId)} minutes={sessionMinutes}
          onLogged={() => {
            window.location.href = `/room?id=${id}`;
          }} />
      )}
    </div>
  );
}

export default function RoomPage() {
  return (
    <Suspense fallback={<div className="state-loading">opening room…</div>}>
      <RoomInner />
    </Suspense>
  );
}
