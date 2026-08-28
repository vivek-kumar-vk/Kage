<script>
  // AgentsCard.svelte - who is on the fleet, as an accordion: one
  // collapsible header per section (the server sorts every agent into
  // one section per navigation tab, plus EVERYWHERE ELSE). Click a
  // header to expand its agents; click again to collapse. The first
  // section that actually has agents starts open, the rest stay shut.
  import Card from './Card.svelte';
  import { fleet } from '../data_for_agents.js';

  const sections = $derived(fleet.state.data?.sections ?? []);
  const total = $derived(sections.reduce((n, s) => n + (s.agents?.length ?? 0), 0));

  const state_class = {
    ok: 'st-ok', idle: 'st-ok', finished: 'st-ok',
    error: 'st-err', failed: 'st-err', blocked: 'st-warn',
  };

  let open = $state({});

  $effect(() => {
    if (fleet.state.phase === 'ready' && sections.length && Object.keys(open).length === 0) {
      const first = sections.find((s) => (s.agents ?? []).length > 0) ?? sections[0];
      if (first) open = { [first.key]: true };
    }
  });

  function toggle(key) { open = { ...open, [key]: !open[key] }; }
</script>

<Card title="Agent fleet" sub="{total} agents on duty" swr={fleet}>
  {#if fleet.state.phase === 'ready'}
    {#if total === 0}
      <p class="empty">no agents registered yet.</p>
    {:else}
      <div class="accordion">
        {#each sections as sec (sec.key)}
          <div class="acc" class:open={open[sec.key]}>
            <button type="button" class="acc-head" aria-expanded={!!open[sec.key]}
                    onclick={() => toggle(sec.key)}>
              <span class="tri" aria-hidden="true">{open[sec.key] ? '▼' : '▶'}</span>
              <span class="acc-label">{sec.label}</span>
              <span class="acc-count">{sec.agents?.length ?? 0}</span>
            </button>
            {#if open[sec.key]}
              <div class="acc-body">
                {#if (sec.agents ?? []).length === 0}
                  <p class="acc-empty">no agents here.</p>
                {:else}
                  {#each sec.agents as a (a.name)}
                    <p class="agent" title={a.what_i_am_for}>
                      <span class="dot {(state_class[a.state] ?? 'st-ok')}"></span>{a.name}
                    </p>
                  {/each}
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</Card>

<style>
  .empty { color: var(--bone-dim, #8B9099); font-size: 0.85rem; margin: 6px 0; }
  .accordion { display: flex; flex-direction: column; gap: 3px; }
  .acc {
    border: 1px solid var(--term-green-faint, #1c3a2a);
    border-radius: 6px;
    overflow: hidden;
  }
  .acc.open { border-color: var(--term-green-dim, #2e7d4f); }
  .acc-head {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    font-family: inherit;
    background: var(--ink-void, #0B0D10);
    border: none;
    color: var(--term-green, #4ade80);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-align: left;
    padding: 7px 10px;
    cursor: pointer;
  }
  .acc-head:hover { background: var(--ink-raised, #1C222A); }
  .acc.open .acc-head { background: var(--ink-raised, #1C222A); color: var(--bone, #E8E4DA); }
  .tri { font-size: 0.6rem; color: var(--term-green-dim, #2e7d4f); width: 12px; flex: none; }
  .acc-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .acc-count {
    font-size: 0.62rem;
    color: var(--bone-dim, #8B9099);
    font-variant-numeric: tabular-nums;
  }
  .acc-body { padding: 4px 10px 8px 30px; display: flex; flex-direction: column; gap: 4px; }
  .agent {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 0.74rem;
    color: var(--bone, #E8E4DA);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .acc-empty { margin: 0; font-size: 0.7rem; color: var(--bone-dim, #8B9099); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--p5-lime, #4ade80); flex: none; }
  .dot.st-err { background: var(--p5-red, #d90000); }
  .dot.st-warn { background: var(--p5-orange, #ff9800); }
</style>