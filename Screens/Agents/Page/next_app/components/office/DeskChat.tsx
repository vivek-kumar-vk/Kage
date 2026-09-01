"use client";

import { useCallback, useEffect, useState } from "react";
import type { OfficeAgent } from "../../lib/office";

interface ChatMessage {
  id: string;
  room_id: string;
  author: "user" | "agent" | "system";
  agent_name: string | null;
  body: string;
  created_at: string | null;
}

export default function DeskChat({
  agent,
  onClose,
  reloadSignal,
}: {
  agent: OfficeAgent;
  onClose: () => void;
  reloadSignal: number;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/agents/${encodeURIComponent(agent.name)}/messages`);
      const data = await res.json();
      setMessages(data.messages ?? []);
    } catch {
      // keep whatever is already on screen
    }
  }, [agent.name]);

  useEffect(() => {
    load();
  }, [load, reloadSignal]);

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  async function send() {
    const message = input.trim();
    if (!message || sending) return;

    setSending(true);
    setError(null);

    try {
      const res = await fetch(`/api/agents/agents/${encodeURIComponent(agent.name)}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.problem ?? `HTTP ${res.status}`);
      }
      setInput("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "send failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="chat-panel">
      <header className="flex items-start justify-between gap-2 border-b border-deck-line px-3 py-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-deck-text">{agent.name}</p>
          <p className="section-label truncate">
            {agent.role || "agent"}
            {agent.parent ? ` · reports to ${agent.parent.replace(/_Agent$/, "")}` : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="border border-deck-line px-2 py-0.5 text-xs text-deck-dim hover:border-deck-copper hover:text-deck-text"
        >
          ✕
        </button>
      </header>

      <div className="chat-scroll flex min-h-0 flex-1 flex-col gap-2 p-2">
        {messages.length === 0 ? (
          <p className="text-xs text-deck-dim">
            Say something — the reply streams onto the stage. If the gateway is down you get an
            honest error bubble, never a fake answer.
          </p>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-msg chat-msg-${msg.author === "agent" ? "agent" : msg.author}`}
            >
              <span className="section-label block">{msg.author === "user" ? "you" : msg.author === "system" ? "system" : agent.name}</span>
              {msg.body}
            </div>
          ))
        )}
      </div>

      {error ? (
        <p className="border-t border-deck-line px-3 py-1.5 text-xs text-deck-alert">{error}</p>
      ) : null}

      <div className="flex items-center gap-2 border-t border-deck-line p-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          placeholder={`Message ${agent.name}…`}
          className="min-w-0 flex-1 border border-deck-line bg-deck-bg px-2 py-1.5 text-sm text-deck-text outline-none placeholder:text-deck-dim focus:border-deck-copper"
        />
        <button
          type="button"
          onClick={send}
          disabled={sending || !input.trim()}
          className="border border-deck-copper px-3 py-1.5 text-sm text-deck-copper hover:bg-[rgba(255,122,0,0.08)] disabled:opacity-40"
        >
          {sending ? "…" : "Send"}
        </button>
      </div>
    </section>
  );
}
