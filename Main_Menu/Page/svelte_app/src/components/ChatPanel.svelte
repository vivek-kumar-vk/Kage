<script>
  // ChatPanel.svelte - wired (Phase H 8). send() POSTs to the menu
  // backend's /api/chat, which walks the Orchestrator fallback chain
  // (claude seat only with the owner's recorded yes - ADR-132 - so a
  // browser chat starts at Model B -> Model A -> free providers).
  // Replies carry their source model as an honest badge; a failed or
  // empty walk says so plainly instead of fabricating a reply.
  let draft = $state('');
  let busy = $state(false);
  let lines = $state([
    { who: 'sys', text: 'chat is wired to the inky backend (local models first).' },
    { who: 'sys', text: 'the claude seat answers only with the owner\u2019s explicit approval.' },
  ]);
  let log_el = $state(null);

  function push(line) {
    lines = [...lines, line];
    requestAnimationFrame(() => {
      if (log_el) log_el.scrollTop = log_el.scrollHeight;
    });
  }

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    push({ who: 'me', text });
    draft = '';
    busy = true;
    try {
      const res = await fetch('/api/main_menu/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) {
        push({ who: 'sys', text: `backend refused the message (http ${res.status}) - nothing was answered.` });
        return;
      }
      const data = await res.json();
      if (data.has_data && data.answer) {
        push({ who: 'sys', text: `[${data.source_model || 'unknown model'}] ${data.answer}` });
      } else {
        push({ who: 'sys', text: 'every model rung came back empty - no honest answer exists right now.' });
      }
    } catch {
      push({ who: 'sys', text: 'backend unreachable - your message was not answered.' });
    } finally {
      busy = false;
    }
  }

  function on_keydown(event) {
    if (event.key === 'Enter') send();
  }
</script>

<section class="chat" aria-label="Chat panel (wired to the inky backend)">
  <header class="chat-head">
    <h2>chat</h2>
    <span class="plug live" title="Wired to POST /api/main_menu/chat (Phase H)">● wired</span>
  </header>

  <div class="log" bind:this={log_el} aria-live="polite">
    {#each lines as line, i (i)}
      {#if line.who === 'me'}
        <p class="line me"><span class="who">you&gt;</span> {line.text}</p>
      {:else}
        <p class="line sys"><span class="who">sys&gt;</span> {line.text}</p>
      {/if}
    {/each}
    {#if busy}
      <p class="line sys" role="status"><span class="who">sys&gt;</span> thinking…</p>
    {/if}
  </div>

  <div class="composer">
    <span class="ps1" aria-hidden="true">inky&gt;</span>
    <input type="text" bind:value={draft} onkeydown={on_keydown} maxlength="500"
           placeholder="ask inky… (local models answer; claude needs owner approval)"
           aria-label="Chat message (sent to the inky backend)" />
    <button type="button" onclick={send} disabled={!draft.trim() || busy}>send</button>
  </div>
</section>

<style>
  .chat {
    border: 1px solid var(--term-green-faint, #1c3a2a);
    border-radius: 10px;
    background: var(--ink-panel, #14181D);
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    height: 100%;
    min-height: 320px;
  }
  .chat-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }
  .chat-head h2 {
    margin: 0;
    font-size: 0.78rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--term-green-dim, #2e7d4f);
    font-weight: 600;
  }
  .plug {
    font-size: 0.64rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--amber, #F2A93B);
    white-space: nowrap;
  }
  .plug.live { color: var(--term-green, #4ade80); }
  .log {
    flex: 1;
    min-height: 96px;
    overflow-y: auto;
    border-left: 2px solid var(--term-green-faint, #1c3a2a);
    padding-left: 10px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .line { margin: 0; font-size: 0.76rem; overflow-wrap: anywhere; }
  .line.me { color: var(--bone, #E8E4DA); }
  .line.sys { color: var(--term-green-dim, #2e7d4f); }
  .who { opacity: 0.75; }
  .composer {
    display: flex;
    align-items: center;
    gap: 8px;
    border-top: 1px solid var(--term-green-faint, #1c3a2a);
    padding-top: 8px;
  }
  .ps1 { font-size: 0.76rem; color: var(--term-green, #4ade80); white-space: nowrap; }
  .composer input {
    flex: 1;
    min-width: 0;
    font-family: inherit;
    font-size: 0.78rem;
    color: var(--bone, #E8E4DA);
    background: var(--ink-void, #0B0D10);
    border: 1px solid var(--sumi-line, #2A3038);
    border-radius: 6px;
    padding: 6px 9px;
  }
  .composer input:focus { outline: 1px solid var(--term-green-dim, #2e7d4f); outline-offset: -1px; }
  .composer button {
    font-family: inherit;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    color: var(--term-green, #4ade80);
    background: transparent;
    border: 1px solid var(--term-green-faint, #1c3a2a);
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    white-space: nowrap;
  }
  .composer button:hover:not(:disabled) { border-color: var(--term-green-dim, #2e7d4f); }
  .composer button:disabled { opacity: 0.4; cursor: default; }
</style>