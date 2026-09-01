<script>
  // The stats card - counts computed from the same SWR answer the board
  // card already holds. No second endpoint exists for this and none is
  // invented: every number here traces to /api/enhancement/ideas, the
  // board's own read route, and an unmeasured thing is never shown as a
  // number (a blank stays blank).
  //
  // Same contract as every card: loading / error / empty / fresh /
  // stale, fetched_at shown, refresh minting an X-Correlation-ID.

  import { read_cached, revalidate, status_of } from '../data_for_ideas.js';

  const STATUSES = ['ideas', 'todo', 'in_progress', 'done']; // the board's own order

  const cached = read_cached();
  let entry = $state(cached);
  let phase = $state(cached ? 'idle' : 'loading'); // loading|idle|error|empty
  let error_message = $state('');
  let refreshing = $state(false);

  let badge = $derived(entry ? status_of(entry.fetched_at) : '');
  let ideas = $derived(entry?.data?.ideas ?? []);

  // One pass over the real rows - no arithmetic is guessed.
  let counts = $derived.by(() => {
    const tally = Object.fromEntries(STATUSES.map((s) => [s, null]));
    if (!entry?.data) return tally;
    for (const s of STATUSES) tally[s] = 0;
    for (const idea of ideas) {
      const where = STATUSES.includes(idea?.status) ? idea.status : 'ideas';
      tally[where] += 1;
    }
    return tally;
  });

  let total = $derived(
    entry?.data ? STATUSES.reduce((sum, s) => sum + (counts[s] ?? 0), 0) : null);

  function label_of(status) {
    return status === 'in_progress' ? 'in progress' : status;
  }

  async function revalidate_now() {
    error_message = '';
    try {
      const answer = await revalidate();
      entry = { data: answer.data, fetched_at: answer.fetched_at };
      phase = (answer.data?.ideas ?? []).length === 0 ? 'empty' : 'idle';
    } catch (trouble) {
      if (entry === null) {
        phase = 'error';
      }
      error_message = `${trouble}`;
    }
  }

  void revalidate_now();

  async function on_refresh() {
    refreshing = true;
    await revalidate_now();
    refreshing = false;
  }
</script>

<section class="card" aria-label="Board stats">
  <header class="card-head">
    <h2>Board Stats</h2>
    {#if phase !== 'loading' && phase !== 'error'}
      {#if badge}
        <span class="badge badge-{badge}">{badge}</span>
      {/if}
    {/if}
  </header>

  {#if phase === 'loading'}
    <p class="state-line">counting what the board holds&hellip;</p>
  {:else if phase === 'error'}
    <p class="state-line error" role="alert">
      could not reach the enhancement server. No number is made up here.
    </p>
  {:else if phase === 'empty'}
    <p class="state-line">the board is empty, so every count is zero. That is honest.</p>
    <ul class="stats">
      {#each STATUSES as status (status)}
        <li><span>{label_of(status)}</span><span>0</span></li>
      {/each}
    </ul>
  {:else}
    <ul class="stats">
      {#each STATUSES as status (status)}
        <li><span>{label_of(status)}</span><span>{counts[status]}</span></li>
      {/each}
      <li class="total"><span>total</span><span>{total}</span></li>
    </ul>
  {/if}

  {#if error_message && phase !== 'error'}
    <p class="state-line error" role="alert">revalidate failed: {error_message} - showing the last known answer.</p>
  {/if}

  {#if entry}
    <p class="meta">fetched at <time>{entry.fetched_at}</time></p>
  {/if}

  <button type="button" class="refresh" onclick={on_refresh} disabled={refreshing}>
    {refreshing ? 'Refreshing\u2026' : 'Refresh'}
  </button>
</section>

<style>
  .card-head { display: flex; align-items: center; gap: 8px; }
  h2 { margin: 0; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.08em; }
  .badge {
    font-size: 0.7rem; padding: 2px 8px; border-radius: 999px;
    border: 1px solid currentcolor; text-transform: uppercase;
  }
  .badge-fresh { color: #7dd88a; }
  .badge-stale { color: #e6b45c; }
  .stats { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 6px; }
  .stats li { display: flex; justify-content: space-between; gap: 12px;
              border-bottom: 1px solid rgba(242, 237, 227, 0.12);
              padding-bottom: 5px; font-variant-numeric: tabular-nums; }
  .stats .total { font-weight: 700; border-bottom: none; padding-top: 4px; }
  .state-line { opacity: 0.75; }
  .state-line.error { color: #e67a6c; opacity: 1; font-size: 0.85rem; }
  .meta { margin: 10px 0 0; font-size: 0.75rem; opacity: 0.6; word-break: break-all; }
  .refresh {
    margin-top: 12px; min-height: 44px; min-width: 44px;
    padding: 10px 18px; border-radius: 8px;
    border: 1px solid rgba(242, 237, 227, 0.4);
    background: transparent; color: inherit;
    font: inherit; cursor: pointer;
  }
  .refresh:hover:not(:disabled) { background: rgba(242, 237, 227, 0.08); }
  .refresh:disabled { opacity: 0.5; cursor: wait; }
</style>
