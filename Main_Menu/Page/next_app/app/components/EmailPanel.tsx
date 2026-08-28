"use client";

/** Right column, top module - "EMAIL" in the reference image's own
    layout (count badge, flagged list, a today's-mix bar). No inbox is
    connected to INKY yet, so this is UI only for now - the owner's own
    words: "i will wire it up later." Same honesty pattern
    TerminalChatPanel already used for its own unwired seat: it says
    plainly that nothing is connected, and invents no count, no flagged
    row, no mix bar out of thin air (C12). The layout is built so a real
    endpoint can fill every one of these slots later without a redraw. */
export function EmailPanel() {
  return (
    <section
      aria-label="Email"
      data-figure="email"
      data-fresh="empty"
      className="agentic-panel flex h-72 flex-col p-3"
    >
      <header className="mb-2 flex items-baseline justify-between">
        <p className="agentic-label">Email</p>
        <span className="num text-lg font-semibold text-dim">—</span>
      </header>
      <p className="mb-3 text-[10px] text-dim">emails past 24h</p>

      <div className="flex flex-1 flex-col items-start justify-center gap-2">
        <p className="text-xs text-dim">not connected yet</p>
        <p className="text-[10px] leading-relaxed text-dim">
          no inbox is wired to INKY. Once one is, this panel reads a real
          count, real flagged rows and a real today&rsquo;s-mix split -
          nothing here is invented in the meantime.
        </p>
      </div>

      <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-[#232323]" aria-hidden="true">
        <div className="h-full w-full bg-[#2a2a2a]" />
      </div>
    </section>
  );
}
