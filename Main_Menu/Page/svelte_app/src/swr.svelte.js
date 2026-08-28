// swr.svelte.js - one stale-while-revalidate engine every card shares.
//
// The .svelte.js suffix matters: Svelte 5 runes only work inside
// .svelte.js modules or .svelte components. Everything reactive in the
// pilot goes through here so each card gets the same honest contract:
//
//     phase      'loading' | 'ready' | 'error'
//     data       the JSON answer, or null
//     error      words for what went wrong, or null
//     fetched_at ISO time of the last successful answer
//     status     'fresh' | 'stale' - age against fresh_window_ms
//     source     'cache' | 'network'
//
// Honesty rules: a cached answer shows as stale once old; an error is
// shown as an error; there is no invented fallback data anywhere. Every
// refresh sends an X-Correlation-ID so a click can be traced end to end.

const DEFAULT_FRESH_MS = 60_000;

function now_iso() {
  return new Date().toISOString();
}

function age_status(fetched_at, window_ms) {
  if (!fetched_at) return 'stale';
  const age = Date.now() - new Date(fetched_at).getTime();
  return age <= window_ms ? 'fresh' : 'stale';
}

export function create_swr(endpoint, cache_key, opts = {}) {
  const fresh_window_ms = opts.fresh_window_ms ?? DEFAULT_FRESH_MS;
  const method = opts.method ?? 'GET';

  const state = $state({
    phase: 'loading',
    data: null,
    error: null,
    fetched_at: null,
    status: 'stale',
    source: null,
  });

  let inflight = null;

  function read_cached() {
    try {
      const raw = localStorage.getItem(cache_key);
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || !parsed.fetched_at) return false;
      state.data = parsed.data ?? null;
      state.fetched_at = parsed.fetched_at;
      state.source = 'cache';
      state.status = age_status(parsed.fetched_at, fresh_window_ms);
      state.phase = 'ready';
      state.error = null;
      return true;
    } catch {
      return false; // broken cache is no cache at all, never data
    }
  }

  function save_cached(data) {
    try {
      localStorage.setItem(cache_key, JSON.stringify({ data, fetched_at: state.fetched_at }));
    } catch { /* storage full - cache is optional, truth is not */ }
  }

  async function load() {
    const cid = crypto.randomUUID();
    if (inflight) return inflight;
    inflight = (async () => {
      try {
        const res = await fetch(endpoint, {
          method,
          headers: { 'X-Correlation-ID': cid },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        state.data = data;
        state.error = null;
        state.fetched_at = now_iso();
        state.source = 'network';
        state.status = 'fresh';
        state.phase = 'ready';
        save_cached(data);
      } catch (err) {
        // A network miss keeps the last good answer visible as stale -
        // but only when there IS one. Otherwise it is simply an error.
        state.error = err instanceof Error ? err.message : String(err);
        if (state.phase !== 'ready') state.phase = 'error';
        else state.status = 'stale';
      } finally {
        inflight = null;
      }
    })();
    return inflight;
  }

  read_cached();
  if (!opts.lazy) load();

  return {
    state,
    refresh: () => load(),
    get busy() { return inflight !== null; },
  };
}
