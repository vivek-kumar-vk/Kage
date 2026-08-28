Type: grilling
Status: open
Blocked by: —

## Question

Confirm the exact removals and pin the shared-shell reskin detail.

### Removals (locked in principle — confirm the file-level plan)

- `ActivityRail` + plumbing: delete `app/components/ActivityRail.tsx`,
  `useLiveEvents.ts`, `LiveBadge.tsx`; drop the `<ActivityRail />` + right-rail
  column from `app/page.tsx`; drop the grid from `grid-cols-[64px_1fr_300px]`.
  Decide: also delete the `/api/finance/live` route + any `Trace_Ledger` wiring,
  or leave the endpoint and just remove the consumer?
- Header: remove the `<span>` subtitle
  "overview · investments · debt · portfolio · telemetry" in `app/page.tsx`.
- Footer: remove the whole disclaimer `<p>` (C4/C5/P8/live-events lines).
- Remove the "could not reach /api/finance/command" error text path from
  `OverviewPanel` (and the analogous strings once Overview is seed-only).

### Shell reskin (user: panel + nav + header/footer; all tabs inherit)

- `SpeedoNav` → plain vertical nav (icon + label + active state, ticket-01
  style). Keep the `items` / `tab` / `onSelect` contract so tab-switching is
  unchanged. Keep or drop the `TELEMETRY` entry? (ties to ticket 06.)
- Header + footer restyle to the ticket-01 tokens.
- Background: `AuroraBackground` → the ticket-01 evening-tone background +
  sakura layer. Delete `AuroraBackground.tsx` or repurpose it?
- Confirm Debt + Portfolio tabs only inherit the shell this effort (internals
  untouched → they'll look half-migrated; acceptable?).
