<script>
  // MoneyCard.svelte - the three money figures off the noticeboard.
  // Surplus leads because it is the number the day is planned around;
  // a blank noticeboard value shows as a dash, never a guessed zero.
  import Card from './Card.svelte';
  import { money } from '../data_for_money.js';

  const brief = $derived(money.state.data ?? {});

  const surplus = $derived(brief.before_slice_refill ?? {});
  const assets = $derived(brief.total_assets ?? {});
  const liabilities = $derived(brief.total_liabilities ?? {});

  const surplus_class = $derived(
    surplus.amount === null || surplus.amount === undefined ? 'blank'
    : surplus.amount < 0 ? 'neg' : 'pos');

  function show(fig) {
    return fig.amount === null || fig.amount === undefined ? '—' : (fig.display ?? '—');
  }
</script>

<Card title="Money" sub="this month, off the noticeboard" swr={money}>
  {#if money.state.phase === 'ready'}
    <div class="money-grid">
      <div class="figure wide {surplus_class}">
        <span class="label">left this month</span>
        <span class="value">{show(surplus)}</span>
      </div>
      <div class="figure">
        <span class="label">assets</span>
        <span class="value small">{show(assets)}</span>
      </div>
      <div class="figure">
        <span class="label">liabilities</span>
        <span class="value small">{show(liabilities)}</span>
      </div>
    </div>
  {/if}
</Card>

<style>
  .money-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .figure {
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: var(--ink-void, #0B0D10);
    border-radius: 10px;
    padding: 10px 12px;
    min-width: 0;
  }
  .figure.wide { grid-column: 1 / -1; border-left: 3px solid var(--ink-edge, #232A33); }
  .figure.wide.pos { border-left-color: var(--p5-lime, #4ade80); }
  .figure.wide.neg { border-left-color: var(--p5-red, #d90000); }
  .label {
    font-size: 0.66rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-faint, #5C6572);
  }
  .value {
    font-size: 1.7rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--bone, #E8E4DA);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .figure.wide .value { font-size: 2.2rem; }
  .value.small { font-size: 1.15rem; }
  .surplus-pos { color: var(--p5-lime, #4ade80); }
  .surplus-neg { color: #ff6b6b; }
  .pos .value, :global(.pos) .value { color: inherit; }
  .wide.pos .value { color: var(--p5-lime, #4ade80); }
  .wide.neg .value { color: #ff6b6b; }
  .blank .value { color: var(--ink-dim, #8B94A3); }
</style>