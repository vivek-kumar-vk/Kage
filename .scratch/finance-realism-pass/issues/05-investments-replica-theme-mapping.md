Type: grilling
Status: open
Blocked by: 01

## Question

The Investments tab becomes the `Screenshot 2026-08-22 090804.png` replica,
**replacing** the current `InvestmentsPanel` entirely (NAV ledger / per-holding
XIRR / `AskStrip` all removed). Data: `app/lib/replicaHoldings.ts` (already
extracted — `REPLICA_SUMMARY`, `REPLICA_GATE`, `REPLICA_HOLDINGS`).

The screenshot is a light theme; the app is dark. Map every element onto the
ticket-01 theme:

- Top bar: ₹ badge · "FINANCE" · clock · "Back to Menu" — keep, or fold into the
  shared shell header from ticket 04?
- Gate alert banner ("Blocked at G2: BUFFER GATE …") — grey→pink in the image;
  new theme's "act" treatment (red is the act colour per AGENTS Rule 8 — this
  one legitimately IS an alert).
- Side nav in the image (Overview / Investments / Portfolio Analysis / Debt &
  Liabilities / Chat) — use the shared vertical nav from ticket 04 instead, or
  reproduce this 5-item variant?
- 3 stat cards (INVESTED / CURRENT VALUE / GAIN-LOSS, green in image) — gain
  colour in the new palette (jade stays, or a themed positive tone?).
- Holdings table: scheme + kind + code + NAV pill, invested, **editable current
  input**, gain/loss (₹ + %), **editable units input**, analysis / save / delete
  buttons — all **non-functional visual placeholders** (locked). Confirm the
  NAV-pill states ("NAV fresh 2d" / "not in NAV ledger yet").
- Row zebra / hover, table scroll-x (C9).

### Output

A field-by-field mapping table (image element → themed component + tokens),
enough for ticket 07 to write build tasks against.
