<script>
  // ClockCard.svelte - the header strip: INKY wordmark and greeting on
  // the left, IST clock and date on the right, and whatever the page
  // drops in the middle (the screens nav) via the `middle` snippet.
  // The one card whose data is the time itself - it needs no server,
  // so it carries no honesty badge.
  let { middle } = $props();

  let now = $state(new Date());

  $effect(() => {
    const t = setInterval(() => { now = new Date(); }, 1000);
    return () => clearInterval(t);
  });

  const time = $derived(now.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata', hour12: false,
  }));
  const date = $derived(now.toLocaleDateString('en-IN', {
    timeZone: 'Asia/Kolkata',
    weekday: 'long', day: 'numeric', month: 'short', year: 'numeric',
  }));
  const greeting = $derived.by(() => {
    const h = Number(now.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: 'numeric', hour12: false }));
    if (h < 5) return 'still up';
    if (h < 12) return 'good morning';
    if (h < 17) return 'good afternoon';
    return 'good evening';
  });
</script>

<header class="strip">
  <div class="brand">
    <span class="mark">INKY</span>
    <span class="greet">{greeting}</span>
  </div>

  {@render middle?.()}

  <div class="clock">
    <span class="clock-line"><time>{time}</time><span class="date"> · {date} · IST</span></span>
  </div>
</header>

<style>
  .strip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 4px 2px 10px;
    flex-wrap: wrap;
  }
  .brand { display: flex; flex-direction: column; gap: 0; min-width: 0; }
  .mark {
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: 0.22em;
    color: var(--term-green, #4ade80);
  }
  .mark::before { content: '┌ '; color: var(--term-green-faint, #1c3a2a); }
  .greet {
    font-size: 0.74rem;
    color: var(--term-green-dim, #2e7d4f);
    white-space: nowrap;
  }
  .clock { text-align: right; margin-left: auto; }
  .clock-line {
    display: block;
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .clock time {
    font-weight: 700;
    color: var(--term-green, #4ade80);
  }
  .date { font-size: 0.72rem; color: var(--bone-dim, #8B9099); }
  @media (max-width: 820px) {
    .clock { margin-left: 0; }
    .clock-line { font-size: 0.72rem; }
    .mark { font-size: 1.15rem; letter-spacing: 0.16em; }
  }
</style>