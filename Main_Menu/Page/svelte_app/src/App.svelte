<script>
  // App.svelte - the landing page as a terminal, laid out to the
  // owner's final mockup (ADR-128 era): header with INKY + greeting on
  // the left, one dropdown tab per built screen in the middle, clock
  // and date on the right; then a row of four equal widgets; then a
  // 70/30 split with the not-wired chat on the left and the agent
  // fleet accordion on the right.
  //
  // The data machinery is untouched: every block is still an
  // independent card on its own SWR hook, honest states and all.
  // One framework per screen, five tabs untouched.
  import ClockCard from './components/ClockCard.svelte';
  import ScreenNav from './components/ScreenNav.svelte';
  import MoneyCard from './components/MoneyCard.svelte';
  import AiUsageCard from './components/AiUsageCard.svelte';
  import CalendarCard from './components/CalendarCard.svelte';
  import AgentsCard from './components/AgentsCard.svelte';
  import ChatPanel from './components/ChatPanel.svelte';
  import { create_swr } from './swr.svelte.js';

  // The screens navigator owns the navigation endpoint directly.
  const navigation = create_swr('/api/main_menu/navigation', 'inky_mm_nav_v2', { fresh_window_ms: 120_000 });
</script>

<main class="page">
  <ClockCard>
    {#snippet middle()}
      <ScreenNav swr={navigation} />
    {/snippet}
  </ClockCard>

  <div class="widgets">
    <MoneyCard />
    <AiUsageCard />
    <CalendarCard />
  </div>

  <div class="split">
    <div class="chat-col">
      <ChatPanel />
    </div>
    <div class="fleet-col">
      <AgentsCard />
    </div>
  </div>

  <footer class="foot">
    <p>// ink v2 · the chat panel is not wired to anything yet - it says so itself</p>
  </footer>
</main>

<style>
  .page {
    max-width: 1180px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* ---- the four equal widgets ---- */
  .widgets {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  /* ---- the 70/30 split ---- */
  .split {
    display: grid;
    grid-template-columns: 7fr 3fr;
    gap: 12px;
    align-items: stretch;
  }
  .chat-col, .fleet-col { display: flex; flex-direction: column; min-width: 0; }
  .chat-col :global(.chat) { flex: 1; }

  .foot p {
    margin: 4px 0 0;
    text-align: center;
    font-size: 0.66rem;
    letter-spacing: 0.1em;
    color: var(--term-green-dim, #2e7d4f);
  }

  /* The four agreed widths only. */
  @media (max-width: 1100px) {
    .widgets { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 820px) {
    .split { grid-template-columns: 1fr; }
    .chat-col :global(.chat) { min-height: 260px; }
  }
  @media (max-width: 560px) {
    .widgets { grid-template-columns: 1fr; }
  }
  @media (max-height: 560px) and (orientation: landscape) {
    .page { gap: 8px; }
  }
</style>