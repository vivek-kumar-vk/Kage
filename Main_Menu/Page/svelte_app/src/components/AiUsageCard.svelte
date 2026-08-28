<script>
  // AiUsageCard.svelte - what INKY's own model calls and Claude Code cost.
  import Card from './Card.svelte';
  import { money } from '../data_for_money.js';

  const brief = $derived(money.state.data ?? {});
  const inky = $derived(brief.inky_usage ?? {});
  const claude = $derived(brief.claude_code_usage ?? {});
</script>

<Card title="AI usage" sub="what thinking cost so far" swr={money}>
  {#if money.state.phase === 'ready'}
    <div class="usage-rows">
      <div class="row">
        <div class="row-top"><span class="who inky">INKY MODELS</span><span class="cost">{inky.cost_display || '—'}</span></div>
        <div class="tokens">{inky.input_display ?? '—'} in · {inky.output_display ?? '—'} out</div>
      </div>
      <div class="row">
        <div class="row-top"><span class="who claude">CLAUDE CODE</span><span class="cost">{claude.cost_display || '—'}</span></div>
        <div class="tokens">{claude.input_display ?? '—'} in · {claude.output_display ?? '—'} out</div>
      </div>
    </div>
  {/if}
</Card>

<style>
  .usage-rows { display: flex; flex-direction: column; gap: 8px; }
  .row {
    display: flex;
    flex-direction: column;
    gap: 3px;
    background: var(--ink-void, #0B0D10);
    border-radius: 8px;
    padding: 9px 12px;
    min-width: 0;
  }
  .row-top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
  }
  .who {
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    white-space: nowrap;
  }
  .who.inky { color: var(--p5-cyan, #00e5ff); }
  .who.claude { color: var(--p5-violet, #7C6FF2); }
  .cost {
    font-size: 1.05rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--bone, #E8E4DA);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tokens {
    font-size: 0.66rem;
    color: var(--bone-dim, #8B9099);
    font-variant-numeric: tabular-nums;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>