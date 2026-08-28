"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/** Left column, bottom module - "TERMINAL / CHAT" in the reference's
    layout. Same request/response logic as the earlier ChatPanel.tsx
    (ported from ChatPanel.svelte, Phase H) - POSTs to
    /api/main_menu/chat, walks the Orchestrator fallback chain (claude
    seat only with the owner's recorded approval, ADR-132), a reply
    always carries its source model, a failed/empty walk says so
    plainly. Only the panel's visual container changed. */

interface Line {
  who: "me" | "sys";
  text: string;
}

export function TerminalChatPanel() {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [lines, setLines] = useState<Line[]>([
    { who: "sys", text: "chat is wired to the inky backend (local models first)." },
    { who: "sys", text: "the claude seat answers only with the owner's explicit approval." },
  ]);
  const log_ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (log_ref.current) log_ref.current.scrollTop = log_ref.current.scrollHeight;
  }, [lines, busy]);

  function push(line: Line) {
    setLines((prev) => [...prev, line]);
  }

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    push({ who: "me", text });
    setDraft("");
    setBusy(true);
    try {
      const res = await fetch("/api/main_menu/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) {
        push({ who: "sys", text: `backend refused the message (http ${res.status}) - nothing was answered.` });
        return;
      }
      const data = await res.json();
      if (data.has_data && data.answer) {
        push({ who: "sys", text: `[${data.source_model || "unknown model"}] ${data.answer}` });
      } else {
        push({ who: "sys", text: "every model rung came back empty - no honest answer exists right now." });
      }
    } catch {
      push({ who: "sys", text: "backend unreachable - your message was not answered." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-label="Chat panel (wired to the inky backend)"
      data-figure="chat"
      data-fresh="fresh"
      className="agentic-panel flex h-56 flex-col gap-2 p-3"
    >
      <p className="agentic-label">Terminal / Chat</p>

      <div ref={log_ref} aria-live="polite" className="flex flex-1 flex-col gap-1 overflow-y-auto">
        <AnimatePresence initial={false}>
          {lines.map((line, i) => (
            <motion.p
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.15 }}
              className={`num text-[11px] ${line.who === "me" ? "text-white" : "text-dim"}`}
            >
              <span className="opacity-60">{line.who === "me" ? "you>" : "sys>"}</span> {line.text}
            </motion.p>
          ))}
          {busy && (
            <motion.p key="thinking" role="status" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="num text-[11px] text-dim">
              <span className="opacity-60">sys&gt;</span> thinking&hellip;
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-2 border-t border-[#262626] pt-2">
        <span className="num text-xs agentic-accent">inky&gt;</span>
        <input
          type="text"
          value={draft}
          maxLength={500}
          placeholder="ask inky…"
          aria-label="Chat message (sent to the inky backend)"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          className="num min-w-0 flex-1 rounded border border-[#333] bg-black px-2 py-1 text-xs text-white outline-none"
        />
        <button
          type="button"
          onClick={send}
          disabled={!draft.trim() || busy}
          className="num rounded border px-3 py-1 text-[10px] uppercase tracking-widest disabled:opacity-40"
          style={{ borderColor: "var(--agentic-amber, #ff7a00)", color: "var(--agentic-amber, #ff7a00)" }}
        >
          send
        </button>
      </div>
    </section>
  );
}
