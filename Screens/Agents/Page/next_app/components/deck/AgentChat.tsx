"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AgentView, OfficeAgent } from "../../lib/office";
import PixelAvatar from "./PixelAvatar";

interface ChatMessage {
  id: string;
  room_id: string;
  author: "user" | "agent" | "system";
  agent_name: string | null;
  body: string;
  created_at: string | null;
}

interface MessagesResponse {
  state: string;
  room_id: string;
  messages: ChatMessage[];
}

interface PostResponse {
  state: "ok" | "error";
  message: ChatMessage;
  reply_message?: ChatMessage;
  problem?: string;
  run_id?: number;
  model?: string;
}

const DAY_LABELS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function dayKey(iso: string | null) {
  if (!iso) return "?";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "?";
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function dayLabel(iso: string | null) {
  if (!iso) return "EARLIER";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "EARLIER";
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86400000);
  if (dayKey(iso) === dayKey(today.toISOString())) return "TODAY";
  if (dayKey(iso) === dayKey(yesterday.toISOString())) return "YESTERDAY";
  return `${DAY_LABELS[date.getDay()]} ${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

function clockOf(iso: string | null) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

interface Props {
  agent: OfficeAgent;
  accent: string;
  states: Map<string, AgentView>;
}

/** Center pane: 1:1 chat with one agent (D17.3). Bodies stay human-readable. */
export default function AgentChat({ agent, accent, states }: Props) {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const name = agent.name;

  useEffect(() => {
    let cancelled = false;
    setMessages(null);
    setError(null);

    fetch(`/api/agents/agents/${encodeURIComponent(name)}/messages`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<MessagesResponse>;
      })
      .then((data) => {
        if (!cancelled) setMessages(data.messages ?? []);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "messages failed");
          setMessages([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [name]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const send = useCallback(async () => {
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);

    try {
      const res = await fetch(`/api/agents/agents/${encodeURIComponent(name)}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ body }),
      });
      const data = (await res.json()) as PostResponse;
      if (!res.ok) throw new Error(data.problem ?? `HTTP ${res.status}`);

      setMessages((prev) => {
        const next = [...(prev ?? []), data.message];
        if (data.state === "ok" && data.reply_message) {
          next.push(data.reply_message);
        } else if (data.state === "error" && data.problem) {
          // A run that failed shows why, inline — never a fabricated reply (Rule 8).
          next.push({
            id: `${data.message.id}-problem`,
            room_id: data.message.room_id,
            author: "system",
            agent_name: null,
            body: data.problem,
            created_at: new Date().toISOString(),
          });
        }
        return next;
      });
      setDraft("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "send failed");
    } finally {
      setSending(false);
    }
  }, [draft, name, sending]);

  const view = states.get(name);
  const statusLine =
    view?.status === "working"
      ? "working now"
      : view?.status === "stuck"
        ? "needs attention"
        : "idle";

  const rows = useMemo(() => {
    const out: ({ kind: "day"; key: string; label: string } | { kind: "msg"; msg: ChatMessage })[] =
      [];
    let lastDay = "";
    for (const msg of messages ?? []) {
      const key = dayKey(msg.created_at);
      if (key !== lastDay) {
        out.push({ kind: "day", key, label: dayLabel(msg.created_at) });
        lastDay = key;
      }
      out.push({ kind: "msg", msg });
    }
    return out;
  }, [messages]);

  return (
    <section className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b-2 border-deck-line bg-deck-panel px-4 py-2">
        <PixelAvatar name={name} color={accent} size={32} />
        <div className="min-w-0">
          <p className="truncate font-display text-sm tracking-wide">{name.replace(/_Agent$/, "")}</p>
          <p className="flex items-center gap-2 text-xs text-deck-dim">
            <span
              className={
                view?.status === "working"
                  ? "presence presence-working"
                  : view?.status === "stuck"
                    ? "presence presence-stuck"
                    : "presence presence-idle"
              }
              aria-hidden="true"
            />
            {statusLine}
            {view?.text ? <span className="truncate">· {view.text}</span> : null}
          </p>
        </div>
      </header>

      <div ref={scrollRef} className="deck-scroll flex min-h-0 flex-1 flex-col gap-2 p-4">
        {messages === null ? (
          <p className="section-label">Loading messages…</p>
        ) : messages.length === 0 ? (
          <div className="px-panel m-auto max-w-md p-4 text-sm text-deck-dim">
            <p className="font-display text-sm text-deck-text">Say hello to {name.replace(/_Agent$/, "")}</p>
            <p className="mt-2">
              Your DMs are stored per agent and answered live through OmniRoute. If the
              gateway is down, the failure shows here — never a fabricated reply.
            </p>
          </div>
        ) : (
          rows.map((row) =>
            row.kind === "day" ? (
              <span key={`day-${row.key}`} className="day-chip">
                {row.label}
              </span>
            ) : row.msg.author === "user" ? (
              <div key={row.msg.id} className="deck-msg deck-msg-user">
                {row.msg.body}
                <span className="deck-msg-meta">{clockOf(row.msg.created_at)}</span>
              </div>
            ) : row.msg.author === "system" ? (
              <div key={row.msg.id} className="deck-msg deck-msg-system">
                {row.msg.body}
              </div>
            ) : (
              <div key={row.msg.id} className="deck-msg deck-msg-agent">
                {row.msg.body}
                <span className="deck-msg-meta">
                  {row.msg.agent_name ?? "agent"} · {clockOf(row.msg.created_at)}
                </span>
              </div>
            )
          )
        )}

        {view?.status === "working" ? (
          <div className="flex items-center gap-2 self-start px-1 text-xs text-deck-dim">
            <span className="typing-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            {name.replace(/_Agent$/, "")} is working…
          </div>
        ) : null}

        {error ? (
          <p className="deck-msg deck-msg-system" style={{ color: "var(--deck-alert)" }}>
            {error}
          </p>
        ) : null}
      </div>

      <div className="flex items-end gap-2 border-t-2 border-deck-line bg-deck-raised p-3">
        <textarea
          className="px-input min-h-[42px] flex-1 resize-y"
          rows={1}
          placeholder={`message ${name.replace(/_Agent$/, "")}…`}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void send();
            }
          }}
          aria-label={`Message ${name}`}
        />
        <button
          type="button"
          className="px-btn px-btn-primary"
          onClick={() => void send()}
          disabled={sending || draft.trim().length === 0}
        >
          {sending ? "…" : "SEND ▸"}
        </button>
      </div>
    </section>
  );
}
