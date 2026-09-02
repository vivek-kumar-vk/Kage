"use client";

import { post, useResource } from "@/lib/api";

type Agent = {
  name: string; title: string; duty: string; tasks: string[];
  status: string; last: string | null;
};
type CrewData = {
  agents: Agent[];
  feed: { ts: string; agent: string; text: string; source: string }[];
  proposals: { id: number; agent: string; kind: string; summary: string;
               detail: string | null; status: string }[];
};

export default function CrewPage() {
  const { data, error, loading, refetch } = useResource<CrewData>("/api/learning/crew");

  async function decide(id: number, action: "approved" | "declined") {
    await post(`/api/learning/proposals/${id}/decide`, { action });
    refetch();
  }

  if (loading) return <div className="state-loading">waking the crew…</div>;
  if (error) return <div className="state-error">{error}</div>;
  if (!data) return null;

  const pending = data.proposals.filter((p) => p.status === "pending");
  const past = data.proposals.filter((p) => p.status !== "pending");

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <div className="page-head" style={{ marginBottom: 18 }}>
        <div>
          <div className="kicker">
            They only know what&apos;s in your system — nothing fetched, ever
          </div>
          <h1 className="display" style={{ fontSize: 36 }}>Crew</h1>
        </div>
        <span className="chip jade">
          <span className="track-dot jade" style={{ width: 6, height: 6 }} />
          live wiring lands with the crew build · feed below is sample data
        </span>
      </div>

      <div style={{
        display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12,
        marginBottom: 16,
      }}>
        {data.agents.map((a) => (
          <div key={a.name} className="panel" style={{
            padding: "13px 14px", display: "flex", flexDirection: "column", gap: 7,
          }}>
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 500,
              letterSpacing: "0.12em", color: "var(--bone)", textTransform: "uppercase",
              display: "flex", alignItems: "center", gap: 7,
            }}>
              {a.status === "working" && (
                <span className="track-dot ember" style={{ width: 6, height: 6 }} />
              )}
              {a.title}
            </div>
            <div style={{ color: "var(--faint)", fontSize: 10.5, lineHeight: 1.45 }}>
              {a.duty}
            </div>
            <div style={{ marginTop: 2 }}>
              {a.tasks.map((t, i) => (
                <div key={i} style={{ color: "var(--dim)", fontSize: 10, lineHeight: 1.5 }}>
                  — {t}
                </div>
              ))}
            </div>
            <div style={{
              display: "flex", alignItems: "center", gap: 6,
              fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.1em",
              color: a.status === "working" ? "var(--ember)" : "var(--faint)",
              marginTop: "auto",
            }}>
              {a.status.toUpperCase()}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 18, flex: 1 }}>
        <section className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div className="panel-head">
            <div className="panel-label">Activity · the crew&apos;s recent work</div>
            <span className="chip ghost">sample</span>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "8px 18px 14px" }}>
            {data.feed.map((f, i) => (
              <div key={i} style={{
                display: "flex", gap: 11, padding: "10px 0",
                borderTop: i === 0 ? "none" : "1px solid var(--hairline)",
                fontSize: 12.5, color: "var(--dim)", alignItems: "baseline",
              }}>
                <span style={{
                  fontFamily: "var(--font-mono)", fontSize: 9.5, color: "var(--faint)",
                  width: 36, flex: "none",
                }}>{f.ts.slice(11, 16)}</span>
                <span className="violet-tag" style={{ width: 74, flex: "none" }}>{f.agent}</span>
                <span style={{ minWidth: 0 }}>{f.text}</span>
                {f.source === "sample" && (
                  <span className="chip ghost" style={{
                    marginLeft: "auto", fontSize: 8.5, padding: "1px 6px",
                  }}>SIM</span>
                )}
              </div>
            ))}
          </div>
          <div className="mono-micro" style={{ padding: "0 18px 14px" }}>
            every entry lands in the ledger · insights is computed from it, never hand-entered
          </div>
        </section>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {pending.map((p) => (
            <section key={p.id} className="panel" style={{ padding: "15px 17px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 7 }}>
                <span className="track-dot violet" style={{ width: 6, height: 6 }} />
                <span className="violet-tag">{p.agent} · {p.kind}</span>
                <span className="chip ghost" style={{ marginLeft: "auto" }}>pending</span>
              </div>
              <div style={{ fontSize: 13, color: "var(--dim)", lineHeight: 1.5 }}>
                <b style={{ color: "var(--bone)", fontWeight: 500 }}>{p.summary}</b>
                {p.detail && <><br />{p.detail}</>}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 11 }}>
                <button className="btn primary small" onClick={() => decide(p.id, "approved")}>
                  approve
                </button>
                <button className="btn quiet small" onClick={() => decide(p.id, "declined")}>
                  decline
                </button>
              </div>
            </section>
          ))}
          {pending.length === 0 && (
            <section className="panel" style={{ padding: 16 }}>
              <div className="state-empty" style={{ padding: 4 }}>
                no proposals waiting — the crew speaks up when it sees something
              </div>
            </section>
          )}

          {past.map((p) => (
            <section key={p.id} className="panel" style={{ padding: "12px 16px", opacity: 0.65 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <span className="track-dot dim" style={{ width: 6, height: 6 }} />
                <span className="violet-tag">{p.agent} · {p.kind}</span>
                <span className={`chip ${p.status === "approved" ? "jade" : "ghost"}`}
                  style={{ marginLeft: "auto" }}>{p.status}</span>
              </div>
              <div style={{ fontSize: 12.5, color: "var(--dim)", marginTop: 5 }}>{p.summary}</div>
            </section>
          ))}

          <section className="panel" style={{
            padding: "13px 17px", marginTop: "auto",
            display: "flex", alignItems: "center", gap: 10,
          }}>
            <span className="track-dot dim" style={{ width: 6, height: 6 }} />
            <span style={{ color: "var(--faint)", fontSize: 11.5 }}>
              Approve is the only write path — agents propose, you dispose.
            </span>
          </section>
        </div>
      </div>
    </div>
  );
}
