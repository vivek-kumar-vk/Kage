<script>
  // Card.svelte - the one shell every landing card sits in.
  //
  // Owns NOTHING about data. It draws the frame: title, honesty badge
  // (loading / fresh / stale / error), fetched-at time and a refresh
  // button that asks the card's own hook for a re-fetch. What changes
  // per card is only the snippet body the parent passes in.
  let { title, sub = '', swr, children } = $props();

  const badge_text = $derived(
    swr.state.phase === 'loading' ? 'loading'
    : swr.state.phase === 'error' ? 'error'
    : swr.state.busy ? 'updating'
    : swr.state.status);

  const badge_class = $derived(
    swr.state.phase === 'error' ? 'badge-err'
    : badge_text === 'fresh' ? 'badge-fresh'
    : badge_text === 'stale' ? 'badge-stale'
    : 'badge-wait');

  const clock_time = $derived(
    swr.state.fetched_at
      ? new Date(swr.state.fetched_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })
      : '');
</script>

<section class="card">
  <header class="card-head">
    <div class="card-titles">
      <h2>{title}</h2>
      {#if sub}<p class="card-sub">{sub}</p>{/if}
    </div>
    <div class="card-tools">
      <span class="badge {badge_class}">{badge_text}</span>
      {#if swr.state.fetched_at}<time title={swr.state.fetched_at}>{clock_time}</time>{/if}
      <button class="refresh" onclick={() => swr.refresh()} disabled={swr.busy} aria-label="Refresh {title}">⟳</button>
    </div>
  </header>

  <div class="card-body">
    {#if swr.state.phase === 'loading'}
      <p class="state-line wait">loading…</p>
    {:else if swr.state.phase === 'error'}
      <p class="state-line bad">could not reach the data: {swr.state.error}</p>
      {@render children()}
    {:else}
      {@render children()}
    {/if}
  </div>
</section>

<style>
  .card {
    background: var(--ink-panel, #14181D);
    border: 1px solid var(--term-green-faint, #1c3a2a);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }
  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }
  .card-titles h2 {
    margin: 0;
    font-size: 0.78rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--term-green-dim, #2e7d4f);
    font-weight: 600;
  }
  .card-titles h2::before { content: '// '; color: var(--term-green-faint, #1c3a2a); }
  .card-sub {
    margin: 2px 0 0;
    font-size: 0.72rem;
    color: var(--bone-dim, #8B9099);
  }
  .card-tools {
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }
  .card-tools time {
    font-size: 0.68rem;
    color: var(--bone-dim, #8B9099);
    font-variant-numeric: tabular-nums;
  }
  .badge {
    font-size: 0.62rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 999px;
    border: 1px solid currentColor;
  }
  .badge-fresh { color: var(--p5-lime, #4ade80); }
  .badge-stale { color: var(--p5-orange, #ff9800); }
  .badge-wait  { color: var(--bone-dim, #8B9099); }
  .badge-err   { color: var(--p5-red, #d90000); }
  .refresh {
    background: none;
    border: 1px solid var(--sumi-line, #2A3038);
    color: var(--bone-dim, #8B9099);
    border-radius: 6px;
    width: 26px;
    height: 26px;
    cursor: pointer;
    line-height: 1;
  }
  .refresh:hover:not(:disabled) { color: var(--term-green, #4ade80); border-color: var(--term-green-dim, #2e7d4f); }
  .refresh:disabled { opacity: 0.4; cursor: default; }
  .state-line { margin: 4px 0; font-size: 0.85rem; }
  .state-line.wait { color: var(--bone-dim, #8B9099); }
  .state-line.bad  { color: var(--p5-red, #d90000); }
</style>