Type: task
Status: open
Blocked by: 01, 02, 03, 04, 05, 06

## Question

Fold decisions 01–06 into the local-model build package.

### Deliverables

1. `.scratch/finance-realism-pass/spec.md` via `to-spec` (synthesis only, no
   interview) — problem, solution, user stories, implementation decisions,
   testing seams (prefer one seam: the `next build` + browser-verify pass).
2. `.scratch/finance-realism-pass/issues/build/NN-*.md` via `to-tickets` —
   vertical, ~one-file slices sized to the local model's context window, each
   with blocking edges. Granularity tuned by `.scratch/lm-ui-gaps/ledger.md`
   (smaller slices for truncation-prone tags). Order:
   **shell/theme tokens → Overview blocks → goals list → removals →
   TELEMETRY de-dup → Investments replica**.
3. Prepend `.scratch/lm-ui-gaps/prompt-contract.md` to the per-task prompt
   template.
4. `AGENTS.md`: add **D1.1** (Red Bull / crimson palette overrides D1 for the
   Finance screen; red still = "act" only where it means act).
5. `PLANNED_WORK.md`: pointer to this map + a note that Debt/Portfolio internals
   and live wiring (P8) remain follow-ups. Enhancement-tab card — decide now
   whether to add the stub (deferred question from the plan).

### Done when

The spec + build tickets exist and the first build ticket is unblocked and
prompt-ready. This ticket is the map's destination artifact.
