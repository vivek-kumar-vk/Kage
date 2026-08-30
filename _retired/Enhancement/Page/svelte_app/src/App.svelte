<script>
  // The pilot page: two cards, nothing else. One framework per screen,
  // five tabs untouched - this app is the whole of the experiment here,
  // exactly as in the Main_Menu pilot.
  import IdeaBoardCard from './components/IdeaBoardCard.svelte';
  import StatsCard from './components/StatsCard.svelte';
</script>

<main class="pilot">
  <h1>INKY - Enhancement</h1>
  <p class="pilot-note">
    Svelte 5 pilot, served only while the USE_SVELTE flag is on.
    The hand-drawn Kanban board is one flag-flip away.
  </p>
  <IdeaBoardCard />
  <StatsCard />
</main>
