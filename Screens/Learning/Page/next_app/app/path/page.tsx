"use client";

import { useState } from "react";
import { del, post, put, useResource } from "@/lib/api";

type Room = {
  id: number; name: string; short: string; status: string; position: number;
  est_minutes: number; mastery: number; level: string;
  steps_done: number; steps_total: number;
};
type Module = { id: number; name: string; position: number; rooms: Room[] };
type Track = {
  id: number; name: string; color: string; mastery: number; level: string;
  room_count: number; modules: Module[];
};
type PathData = { tracks: Track[] };

function Ring({ pct, color, size = 40 }: { pct: number; color: string; size?: number }) {
  return (
    <span className={`ring ${color}`} style={{ width: size, height: size }}>
      <i>{pct}%</i>
    </span>
  );
}

const STATUS_CHIP: Record<string, string> = {
  done: "jade", learning: "ember", todo: "",
};

export default function PathPage() {
  const { data, error, loading, refetch } = useResource<PathData>("/api/learning/path");
  const [quick, setQuick] = useState("");
  const [quickModule, setQuickModule] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [addingRoom, setAddingRoom] = useState<number | null>(null);
  const [roomName, setRoomName] = useState("");

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      await fn();
      refetch();
    } catch (e) {
      alert(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  function moveRoom(track: Track, module: Module, room: Room, dir: -1 | 1) {
    const siblings = module.rooms;
    const idx = siblings.findIndex((r) => r.id === room.id);
    const other = siblings[idx + dir];
    if (!other) return;
    act(async () => {
      await put(`/api/learning/rooms/${room.id}`, { position: other.position });
      await put(`/api/learning/rooms/${other.id}`, { position: room.position });
    });
  }

  if (loading) return <div className="state-loading">loading path…</div>;
  if (error) return <div className="state-error">{error}</div>;
  if (!data) return null;

  const allModules = data.tracks.flatMap((t) =>
    t.modules.map((m) => ({ id: m.id, label: `${t.name} · ${m.name}` })),
  );
  const target = quickModule ?? allModules[0]?.id ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <div className="page-head">
        <div>
          <div className="kicker">The map · tracks live side by side</div>
          <h1 className="display">Path</h1>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input
            style={{ width: 270 }}
            placeholder="Add a room — paste a topic name"
            value={quick}
            onChange={(e) => setQuick(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && quick.trim() && target) {
                act(async () => {
                  await post(`/api/learning/modules/${target}/rooms`, { name: quick.trim() });
                  setQuick("");
                });
              }
            }}
          />
          <select value={target ?? ""} onChange={(e) => setQuickModule(Number(e.target.value))}>
            {allModules.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          <span className="chip ghost clickable" onClick={() => {
            const name = prompt("New track name:");
            if (name?.trim()) act(() => post("/api/learning/tracks", { name: name.trim() }));
          }}>+ track</span>
          <span className="chip ghost clickable" onClick={() => {
            if (!data.tracks.length) return alert("Add a track first");
            const t = data.tracks.length === 1 ? data.tracks[0]
              : data.tracks.find((x) => x.name === prompt(`Track? (${data.tracks.map((x) => x.name).join(" / ")})`));
            if (!t) return;
            const name = prompt("New module name:");
            if (name?.trim()) act(() => post(`/api/learning/tracks/${t.id}/modules`, { name: name.trim() }));
          }}>+ module</span>
          <span className="chip">archive is a state, not a loss</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22, flex: 1 }}>
        {data.tracks.map((track) => (
          <section key={track.id} className="panel" style={{
            display: "flex", flexDirection: "column", overflow: "hidden",
          }}>
            <div className="track-head" style={{
              display: "flex", alignItems: "center", gap: 14, padding: "20px 22px",
              borderBottom: "1px solid var(--hairline)",
            }}>
              <span className={`track-dot ${track.color}`} />
              <div>
                <h3 style={{
                  fontFamily: "var(--font-fraunces), serif", fontWeight: 420, fontSize: 20,
                }}>{track.name}</h3>
                <div style={{ color: "var(--faint)", fontSize: 12 }}>
                  {track.room_count} rooms · {track.modules.length} modules
                </div>
              </div>
              <span style={{ marginLeft: "auto" }}>
                <Ring pct={track.mastery} color={track.color} />
              </span>
              <span style={{ display: "flex", gap: 6 }}>
                <span className="chip ghost clickable" title="Rename track" onClick={() => {
                  const name = prompt("Rename track:", track.name);
                  if (name?.trim()) act(() => put(`/api/learning/tracks/${track.id}`, { name: name.trim() }));
                }}>✎</span>
                <span className="chip ghost clickable danger" title="Delete track" onClick={() => {
                  if (confirm(`Delete "${track.name}" and everything in it?`))
                    act(() => del(`/api/learning/tracks/${track.id}`));
                }}>✕</span>
              </span>
            </div>

            <div style={{ padding: "14px 16px 16px", overflow: "auto", flex: 1 }}>
              {track.modules.map((mod) => (
                <div key={mod.id} style={{ marginBottom: 18 }}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 8px 10px",
                  }}>
                    <span className="mono-micro" style={{ color: "var(--dim)" }}>{mod.name}</span>
                    <span style={{ color: "var(--faint)", fontSize: 11 }}>
                      {mod.rooms.length} rooms
                    </span>
                    <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                      <span className="chip ghost clickable"
                        onClick={() => { setAddingRoom(addingRoom === mod.id ? null : mod.id); setRoomName(""); }}>
                        + room
                      </span>
                      <span className="chip ghost clickable" title="Rename module" onClick={() => {
                        const name = prompt("Rename module:", mod.name);
                        if (name?.trim()) act(() => put(`/api/learning/modules/${mod.id}`, { name: name.trim() }));
                      }}>✎</span>
                    </span>
                  </div>

                  {addingRoom === mod.id && (
                    <div style={{ display: "flex", gap: 8, padding: "0 8px 10px" }}>
                      <input style={{ flex: 1 }} autoFocus placeholder="Room name"
                        value={roomName} onChange={(e) => setRoomName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && roomName.trim()) {
                            act(async () => {
                              await post(`/api/learning/modules/${mod.id}/rooms`, { name: roomName.trim() });
                              setAddingRoom(null); setRoomName("");
                            });
                          }
                        }} />
                      <button className="btn quiet small"
                        onClick={() => roomName.trim() && act(async () => {
                          await post(`/api/learning/modules/${mod.id}/rooms`, { name: roomName.trim() });
                          setAddingRoom(null); setRoomName("");
                        })}>add</button>
                    </div>
                  )}

                  {mod.rooms.map((room, ri) => (
                    <div key={room.id} className={room.status === "learning" ? "panel raised" : ""}
                      style={{
                        display: "flex", alignItems: "center", gap: 12,
                        padding: "9px 10px", borderRadius: 10, marginBottom: 2,
                        background: room.status === "learning" ? "var(--ember-dim)" : undefined,
                        border: room.status === "learning" ? "1px solid rgba(232,168,81,.3)" : "1px solid transparent",
                      }}>
                      <Ring pct={room.mastery} color={room.mastery > 0 ? track.color : "lock"} size={22} />
                      <a href={`/room?id=${room.id}`}
                        style={{
                          color: room.status === "todo" ? "var(--dim)" : "var(--bone)",
                          fontWeight: room.status === "todo" ? 400 : 500,
                          textDecoration: "none", fontSize: 13.5, minWidth: 0,
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                        {room.short}
                      </a>
                      {room.status === "learning" && <span className="chip ember">you are here</span>}
                      {room.status === "done" && <span className="chip jade">done</span>}
                      <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, color: "var(--faint)", fontSize: 11.5 }}>
                        <span>{room.steps_done}/{room.steps_total} steps</span>
                        <span style={{ display: "flex", gap: 3 }}>
                          <span className="chip ghost clickable"
                            style={{ opacity: ri === 0 ? 0.3 : 1 }}
                            onClick={() => ri > 0 && !busy && moveRoom(track, mod, room, -1)}>↑</span>
                          <span className="chip ghost clickable"
                            style={{ opacity: ri === mod.rooms.length - 1 ? 0.3 : 1 }}
                            onClick={() => ri < mod.rooms.length - 1 && !busy && moveRoom(track, mod, room, 1)}>↓</span>
                          <span className="chip ghost clickable" title="Archive room"
                            onClick={() => !busy && act(() => put(`/api/learning/rooms/${room.id}`, { archived: true }))}>⌃</span>
                          <span className="chip ghost clickable" title="Delete room"
                            onClick={() => confirm(`Delete "${room.short}"? Its steps, notes and cards go too.`) &&
                              act(() => del(`/api/learning/rooms/${room.id}`))}>✕</span>
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      <div style={{
        marginTop: 12, display: "flex", justifyContent: "space-between",
        color: "var(--faint)", fontSize: 11.5, padding: "0 8px",
      }}>
        <span>Archived rooms keep their notes, cards and history — they just step out of the way.</span>
        <span>↑ ↓ reorder · ⌃ archive · ✕ delete</span>
      </div>
    </div>
  );
}
