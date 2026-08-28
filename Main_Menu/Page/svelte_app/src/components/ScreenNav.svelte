<script>
  // ScreenNav.svelte - the header's dropdown tabs, one per built screen,
  // drawn from discovery. No screen name is written in this file: what
  // exists is what the navigation endpoint found. A tab row links to the
  // screen's own address (from its settings file), never to a guessed
  // port. Not-built folders get nothing here - a dropdown that opens
  // into nothing is a button that lies.
  let { swr } = $props();

  const screens = $derived(
    [...(swr.state.data?.screens ?? [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)));

  let open_key = $state(null);
  let root_el = $state(null);

  function toggle(key) { open_key = open_key === key ? null : key; }
  function close_all() { open_key = null; }

  $effect(() => {
    function on_click_outside(event) {
      if (open_key && root_el && !root_el.contains(event.target)) close_all();
    }
    function on_escape(event) {
      if (event.key === 'Escape') close_all();
    }
    document.addEventListener('click', on_click_outside);
    document.addEventListener('keydown', on_escape);
    return () => {
      document.removeEventListener('click', on_click_outside);
      document.removeEventListener('keydown', on_escape);
    };
  });
</script>

<nav class="screen-nav" bind:this={root_el} aria-label="Screens">
  {#each screens as s (s.key)}
    <div class="dd">
      <button type="button" class="dd-trigger" aria-expanded={open_key === s.key}
              aria-haspopup="true" onclick={() => toggle(s.key)}>
        {s.label} <span class="chev" class:open={open_key === s.key}>▾</span>
      </button>
      {#if open_key === s.key}
        <div class="dd-menu" role="menu">
          {#each s.tabs ?? [] as t (t.key)}
            <a role="menuitem" href={s.address ?? '#'} target="_blank" rel="noopener" onclick={close_all}>
              {t.label}
            </a>
          {:else}
            <span class="dd-empty">no tabs declared</span>
          {/each}
        </div>
      {/if}
    </div>
  {:else}
    <span class="dd-wait">{swr.state.phase === 'error' ? 'screens unreachable' : 'finding screens…'}</span>
  {/each}
</nav>

<style>
  .screen-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    flex-wrap: wrap;
    min-width: 0;
  }
  .dd { position: relative; }
  .dd-trigger {
    font-family: var(--font-term, monospace);
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--term-green, #4ade80);
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 7px 10px;
    cursor: pointer;
    white-space: nowrap;
  }
  .dd-trigger:hover, .dd-trigger[aria-expanded='true'] {
    background: var(--ink-panel, #14181D);
    color: var(--bone, #E8E4DA);
  }
  .chev {
    display: inline-block;
    font-size: 0.66rem;
    color: var(--term-green-dim, #2e7d4f);
    transition: transform var(--move-fast, 60ms) ease;
  }
  .chev.open { transform: rotate(180deg); }
  .dd-menu {
    position: absolute;
    left: 0;
    top: calc(100% + 4px);
    z-index: 40;
    min-width: 190px;
    background: var(--ink-panel, #14181D);
    border: 1px solid var(--term-green-faint, #1c3a2a);
    border-radius: 8px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .dd-menu a {
    display: block;
    text-decoration: none;
    color: var(--term-green, #4ade80);
    font-size: 0.76rem;
    letter-spacing: 0.04em;
    padding: 6px 9px;
    border-radius: 5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .dd-menu a::before { content: '· '; color: var(--term-green-dim, #2e7d4f); }
  .dd-menu a:hover { background: var(--ink-raised, #1C222A); color: var(--bone, #E8E4DA); }
  .dd-empty { display: block; padding: 6px 9px; font-size: 0.74rem; color: var(--bone-dim, #8B9099); }
  .dd-wait { font-size: 0.74rem; color: var(--term-green-dim, #2e7d4f); }
</style>