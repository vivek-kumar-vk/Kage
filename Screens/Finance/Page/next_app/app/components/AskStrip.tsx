"use client";

import { useState } from "react";

/** One "Ask INKY" strip. Reused by Investments and Portfolio Analysis -
    the same two strips the vanilla page carries, wired to the same real
    endpoints, never faked or stubbed. Every message travels through this
    screen's own server (server_for_finance.py) to the Models screen's
    router over HTTP on port 8003 (C8) - the router is Tier 0 by default
    (ADR-040) here, so an honest refusal is the ordinary answer until a
    provider is cleared for the message shape asked. The reply is never
    a recommendation to buy, sell, switch or redeem (C5) - this UI shows
    whatever text the router returns and adds no advice of its own. */
export function AskStrip({ endpoint, placeholder }: { endpoint: string; placeholder: string }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const ask = () => {
    const trimmed = message.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setReply(null);
    setNote(null);
    setFailed(false);
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: trimmed }),
    })
      .then((r) => r.json())
      .then((body) => {
        setBusy(false);
        if (body.ok && body.reply) {
          setReply(body.reply as string);
        } else {
          setFailed(true);
          setNote((body.note as string) || (body.problem as string) || "no answer came back");
        }
      })
      .catch((e) => {
        setBusy(false);
        setFailed(true);
        setNote(`could not reach the router: ${e}`);
      });
  };

  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <h3 className="num mb-2 text-xs tracking-[0.2em] text-dim">ASK INKY</h3>
      <div className="flex gap-2">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded border border-line bg-void px-3 py-2 text-sm text-bone outline-none focus:border-cyan"
        />
        <button
          type="button"
          onClick={ask}
          disabled={busy || !message.trim()}
          className="num shrink-0 rounded border border-line px-3 py-2 text-xs tracking-widest text-dim hover:border-jade hover:text-jade disabled:opacity-40"
        >
          {busy ? "ASKING..." : "ASK"}
        </button>
      </div>
      {reply && (
        <p className="ai-generated mt-3 whitespace-pre-wrap text-sm text-bone">{reply}</p>
      )}
      {failed && note && (
        <p className="mt-3 text-xs text-p5red">{note}</p>
      )}
      <p className="mt-2 text-[10px] text-dim">
        never a buy/sell recommendation (C5) - this screen only shows what the router answers
      </p>
    </div>
  );
}
