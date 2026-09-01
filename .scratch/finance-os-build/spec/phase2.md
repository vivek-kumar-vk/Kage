# Phase 2 — Overview tab + the wiring primitives H/N depend on

Authoritative: master doc §7 (Overview endpoints), §8.4–8.7, §8.10, §10 (goals
probability). This phase builds the frontend data layer that Phases 5 and 7 rely
on, so it must be right here.

## META-FIX — see phase0.md.

## Files & responsibilities

- `frontend/lib/api.ts` — start from master doc §8.4 (`MUTATING_METHODS` set,
  explicit method detection) and ADD:
  - a module-level **cache-version counter** + a subscribe/notify mechanism
    (`useSyncExternalStore`-compatible). Any mutation bumps the version.
  - `invalidateCache` on a mutation clears the WHOLE cache (5-min TTL, cheap to
    rebuild) — do NOT rely on a hardcoded prefix list that a 9th router breaks.  **[G/N]**
  - `useFinanceData(endpoint)` returns `{data,isLoading,error,refetch}` and
    re-runs its fetch when the cache-version changes (subscribed), so a mutation
    fired anywhere re-renders mounted cards WITHOUT a remount.  **[G/N]**
  - `useSubmit()` hook — POST/PUT/DELETE wrapper → on success calls
    `invalidateCache()` + bumps the version.  **[H]**
- `frontend/components/finance/FormModal.tsx` — Shadcn dialog wrapper used by the
  Overview "+" and "Manage all →" triggers and by the Settings page (Phase 7).  **[H]**
- `frontend/lib/types.ts` — shared response types.
- `frontend/app/layout.tsx`, `app/page.tsx` (redirect → `/finance`),
  `app/finance/layout.tsx` (nav from master doc §8.5 — plain equality `isActive`,
  no dead `/finance/overview` branch), `app/finance/page.tsx` (§8.6 grid).
- `backend/routers/overview.py` — the 9 Overview endpoints (master doc §7). All
  calculations read `active_holdings` (never `holdings`). `/overview/goals`:
  `total_months` comes from a STORED baseline (`goals.start_date` set at
  creation), NOT recomputed from `created_at`→`target_date` each call, so editing
  `target_date` doesn't silently rescale past probabilities. Use
  `goal_probability` from master doc §10 verbatim.  **[E]**
- `backend/services/calculations/{net_worth,cashflow,emergency,goals}.py` — the
  deterministic formulas (master doc §10). No LLM.
- `frontend/components/finance/cards/*` — NetWorthCard, CashflowCard,
  PortfolioPulseCard, EmergencyFundCard, DebtStatusCard, SurplusAllocationCard,
  GoalsCard, TopActionsCard, DataHealthCard. Each fetches its own data via
  `useFinanceData`, handles loading / error / **empty** explicitly.
  - NetWorthCard sparkline: use master doc §8.7 BUT drop the forced `0` —
    `Math.max(...values)` / `Math.min(...values)` on the real data, keep
    `const range = (max - min) || 1`. An all-positive ₹40–50L series must fill
    the box, not get crushed into the top 1%.  **[F]**
  - GoalsCard header links `/finance/settings?tab=goals` (master doc §8.8).
- `frontend/components/finance/three/HeroScene.tsx` — Three.js hero,
  `next/dynamic(..., {ssr:false})`, 2D fallback component when WebGL absent or
  `prefers-reduced-motion`.

## REFERENCE BLOCKS (you do NOT have the master plan file — use these)

### lib/api.ts — start from this, then add the version counter + refetch
```typescript
import { useState, useEffect } from 'react';

const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000;
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export function invalidateCache(prefix: string) {
  for (const key of cache.keys()) if (key.startsWith(prefix)) cache.delete(key);
}

export async function fetchFinanceData<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const method = (options?.method ?? 'GET').toUpperCase();
  const isMutation = MUTATING_METHODS.has(method);
  if (!isMutation) {
    const cached = cache.get(endpoint);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) return cached.data as T;
  }
  const response = await fetch(endpoint, options);
  if (!response.ok) throw new Error(`Failed to fetch ${endpoint}`);
  const data = await response.json();
  if (!isMutation) cache.set(endpoint, { data, timestamp: Date.now() });
  // ADD: on mutation, clear the WHOLE cache (not a hardcoded prefix list) + bump version
  return data;
}
```
ADD to that file: `let cacheVersion = 0; const listeners = new Set<() => void>();`
`export function subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);}`
`export function getVersion(){return cacheVersion;}` — on any mutation:
`cache.clear(); cacheVersion++; listeners.forEach(l => l());`
`useFinanceData(endpoint)` uses `useSyncExternalStore(subscribe, getVersion)` so a
version bump re-runs its fetch effect (no remount); returns `{data,isLoading,
error,refetch}`. `useSubmit()` → `async submit(endpoint, options) { const r = await
fetchFinanceData(endpoint, options); return r; }` (mutation path already bumps).

### app/finance/layout.tsx — nav shape
```tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
const tabs = [
  { name: 'Overview', href: '/finance' },
  { name: 'Investments', href: '/finance/investments' },
  { name: 'Debt', href: '/finance/debt' },
  { name: 'Tracker', href: '/finance/tracker' },
  { name: 'Learning', href: '/finance/learning' },
];
// header: <span className="status-dot"/> + <h1>FINANCE OS</h1>; nav maps tabs,
// const isActive = pathname === tab.href;  (plain equality — no /finance/overview branch)
// active class: 'bg-racing-red text-white shadow-neon-red' else 'text-gray-400 hover:text-white hover:bg-carbon-light'
// plus a trailing <Link href="/finance/settings">Settings</Link>
```

### NetWorthCard sparkline — corrected scaling (NO forced 0)
```tsx
const values = data.trend.map(p => p.net_worth);
const hasData = values.length > 0;
const max = hasData ? Math.max(...values) : 1;      // NOT Math.max(...values, 0)
const min = hasData ? Math.min(...values) : 0;      // NOT Math.min(...values, 0)
const range = (max - min) || 1;                     // flat-trend guard
// per point: x = trend.length > 1 ? (i/(trend.length-1))*100 : 50;
//            y = 35 - ((point.net_worth - min) / range) * 30;
```

### goal probability (for /overview/goals; total_months from goals.start_date)
```python
def goal_probability(current, target, months_left, total_months):
    if target <= 0: return 0.0
    if months_left <= 0: return 100.0 if current >= target else 0.0
    time_factor = min(months_left / total_months, 1.0)
    progress = min(current / target, 1.0)
    return min(100.0, max(0.0, (progress * 0.7 + time_factor * 0.3) * 100))
```

## Gate (`gate_phase2.py`)
`lib/api.ts` has a cache-version counter subscribers read + `refetch`;
NetWorthCard sparkline has no forced 0 and keeps `||1`; `<FormModal>` + `useSubmit`
exist; `next build` produces `frontend/out/`; every `/overview/*` endpoint returns
200 with no `NaN`/`Infinity` on a fresh empty DB.
