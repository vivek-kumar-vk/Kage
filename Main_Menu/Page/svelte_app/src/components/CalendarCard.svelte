<script>
  // CalendarCard.svelte - what the calendar agent has on file for today.
  import Card from './Card.svelte';
  import { calendar } from '../data_for_calendar.js';

  const events = $derived.by(() => {
    const d = calendar.state.data;
    if (!d) return [];
    const list = Array.isArray(d) ? d : (d.events ?? []);
    return Array.isArray(list) ? list : [];
  });

  const today_iso = $derived(new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }));

  const todays = $derived(events.filter((ev) => !ev?.date || ev.date === today_iso));
</script>

<Card title="Today" sub="calendar, IST day" swr={calendar}>
  {#if calendar.state.phase === 'ready'}
    {#if todays.length === 0}
      <p class="empty">nothing on file today — that is the truth, not an error.</p>
    {:else}
      <ul class="events">
        {#each todays.slice(0, 4) as ev (ev.title + ev.date)}
          <li>
            {#if ev.date}<span class="ev-date">{ev.date}</span>{/if}
            <span class="ev-title">{ev.title ?? 'untitled'}</span>
          </li>
        {/each}
      </ul>
      {#if todays.length > 4}<p class="more">+{todays.length - 4} more on the calendar screen</p>{/if}
    {/if}
  {/if}
</Card>

<style>
  .empty { color: var(--ink-dim, #8B94A3); font-size: 0.85rem; margin: 6px 0; }
  .events {
    margin: 0; padding: 0; list-style: none;
    display: flex; flex-direction: column; gap: 6px;
  }
  .events li {
    display: flex; gap: 10px; align-items: baseline;
    background: var(--ink-void, #0B0D10);
    border-radius: 8px; padding: 7px 10px;
    font-size: 0.86rem;
  }
  .ev-date {
    color: var(--p5-cyan, #00e5ff);
    font-size: 0.68rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .ev-title { color: var(--bone, #E8E4DA); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .more { margin: 4px 0 0; font-size: 0.7rem; color: var(--ink-faint, #5C6572); }
</style>