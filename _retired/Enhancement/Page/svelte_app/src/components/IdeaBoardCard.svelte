<script>
  // The idea board card - SWR in practice, reading the screen's own
  // existing /api/enhancement/ideas route (nothing new was invented).
  //
  //   1. a cached answer (if any) is shown immediately, badged by its age
  //   2. a background revalidate runs at once; when it lands the badge
  //      turns fresh and the board updates in place
  //   3. no cache and no answer yet -> loading; the request failing with
  //      nothing cached -> error; the server genuinely reporting no
  //      ideas -> empty. Each state is rendered as what it is.
  //
  // Every fetch carries an X-Correlation-ID header minted in
  // data_for_ideas.js so the trace ledger can follow the thread.

  import { read_cached, revalidate, status_of } from '../data_for_ideas.js';

  const cached = read_cached(); // { data, fetched_at } or null
  let entry = $state(cached);
  let phase = $state(cached ? 'idle' : 'loading'); // loading|idle|error|empty
  let error_message = $state('');
  let refreshing = $state(false);

  let badge = $derived(entry ? status_of(entry.fetched_at) : '');
  let ideas = $derived(entry?.data?.ideas ?? []);
  let built = $derived(entry?.data?.built === true);

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

  // Cached row is already on screen; the first revalidate runs now,
  // in the background - that is the whole point of stale-while-revalidate.
  void revalidate_now();

  async function on_refresh() {
    refreshing = true;
    await revalidate_now();
    refreshing = false;
  }
</script>

<section class="card" aria-label="Idea board">
  <header class="card-head">
    <h2>Idea Board</h2>
    {#if phase !== 'loading' && phase !== 'error'}
      {#if badge}
        <span class="badge badge-{badge}">{badge}</span>
      {/if}
    {/if}
  </header>

  {#if phase === 'loading'}
    <p class="state-line">asking the enhancement server for the board&hellip;</p>
  {:else if phase === 'error'}
    <p class="state-line error" role="alert">
      could not reach the enhancement server. Nothing is guessed to fill the gap.
    </p>
  {:else if phase === 'empty'}
    <p class="state-line">
      {#if built}
        the board is empty. That is the truth of it - not one idea saved yet.
      {:else}
        the server answered without a board behind it.
      {/if}
    </p>
  {:else}
    <ul class="rows">
      {#each ideas as idea (idea.id)}
        <li>
          <span class="title">{idea.title}</span>
          <span class="sub">{idea.status ?? 'ideas'} &middot; {idea.area || 'no area'} &middot; {idea.source}</span>
        </li>
      {/each}
    </ul>
    <p class="count">{ideas.length} idea{ideas.length === 1 ? '' : 's'}</p>
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
  .rows { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 8px;
          max-height: 40vh; overflow-y: auto; }
  .rows li { display: grid; gap: 2px; min-width: 0; }
  .title { font-weight: 600; overflow-wrap: anywhere; }
  .sub { font-size: 0.75rem; opacity: 0.65; }
  .count { margin: 10px 0 0; font-size: 0.8rem; opacity: 0.8; }
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
