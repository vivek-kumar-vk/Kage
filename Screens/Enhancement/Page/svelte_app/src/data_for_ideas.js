// SWR for the enhancement board - stale-while-revalidate, in one small
// file, the same shape the Main_Menu pilot uses.
//
// The shape every caller gets back is always:
//     { data, fetched_at, source, status }
//   data       - the JSON the server sent, or null when there is nothing
//   fetched_at - ISO timestamp of the moment the data was received
//   source     - 'cache' (answered from localStorage) or 'network'
//   status     - 'fresh' (inside FRESH_WINDOW_MS) or 'stale' (past it)
//
// Honesty rules this file obeys: a cached answer is shown as stale the
// moment it is old, never dressed up as fresh; an error is an error;
// there is no made-up fallback data anywhere.
//
// The endpoint is the board's own existing read route on this screen's
// server (server_for_enhancement.py) - nothing was invented for the
// pilot, it reads exactly what the Kanban page already reads.

const ENDPOINT = '/api/enhancement/ideas';
const CACHE_KEY = 'inky_enhancement_svelte_ideas_cache_v1';

// How long an answer may call itself fresh. Past this it still renders -
// with a stale badge - while a background revalidate runs.
export const FRESH_WINDOW_MS = 60_000;

function now_iso() {
  return new Date().toISOString();
}

export function read_cached() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || !parsed.fetched_at) return null;
    return { data: parsed.data ?? null, fetched_at: parsed.fetched_at };
  } catch {
    // A broken cache row is treated as no cache at all, never as data.
    return null;
  }
}

function save_to_cache(entry) {
  try {
    localStorage.setItem(CACHE_KEY,
      JSON.stringify({ data: entry.data, fetched_at: entry.fetched_at }));
  } catch {
    // Storage full or blocked: the session keeps working from memory.
  }
}

export function status_of(fetched_at) {
  if (!fetched_at) return 'stale';
  const age = Date.now() - Date.parse(fetched_at);
  return Number.isFinite(age) && age <= FRESH_WINDOW_MS ? 'fresh' : 'stale';
}

/**
 * Ask the server again. Resolves with the full SWR shape
 * ({data, fetched_at, source: 'network', status}) or throws on any
 * failure - callers render the error, nothing is invented here.
 *
 * Every request carries an X-Correlation-ID header so the server's trace
 * ledger can tie this fetch to everything else that click caused. The
 * server already honours an inbound X-Correlation-Id and echoes it back.
 */
export async function revalidate() {
  const correlation_id = crypto.randomUUID();
  const response = await fetch(ENDPOINT, {
    headers: { 'X-Correlation-ID': correlation_id },
  });
  if (!response.ok) {
    throw new Error(`the enhancement server answered ${response.status}`);
  }
  const data = await response.json();
  const entry = { data, fetched_at: now_iso(), source: 'network', correlation_id };
  save_to_cache(entry);
  return entry;
}
