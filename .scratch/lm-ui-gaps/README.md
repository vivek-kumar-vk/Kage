# ui-gap-scout — a Hermes Bot for profiling Model A's UI gaps

`ui_gap_scout` is a **Hermes agent Bot** (Bot Mode:
https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode). It watches every
local-model build task and maintains `ledger.md`, `prompt-contract.md`, and
`improvement-progress.md` in this folder. Persona: `SOUL.md`.

## Status: created (2026-08-28)

Done for you this session:

- `hermes profile create ui_gap_scout` — profile at
  `C:\Users\vkjha\AppData\Local\hermes\profiles\ui_gap_scout\`, alias
  `ui_gap_scout` → `hermes -p ui_gap_scout`.
- `config.yaml` → **runs on the local model** (`local-model-a` @
  `localhost:8080`, `free_only: true`) — **zero Claude cost per review**, which
  is what "use less claude usage" wants. The review task (classify against a
  fixed tag list, append a line, tweak a contract) is well within the 7B's
  reach. If review quality proves poor, swap `config.yaml` `model.provider` to an
  Anthropic Haiku provider — one-line change.
- `SOUL.md` installed into the profile (source of truth stays here; re-copy after
  edits: `cp .scratch/lm-ui-gaps/SOUL.md "$LOCALAPPDATA/hermes/profiles/ui_gap_scout/SOUL.md"`).

Optional, if you want richer reviews later: drop the profile's
`.no-bundled-skills` file and enable the Matt Pocock skills cloned at
`C:\inky_models\skill_sources\mattpocock-skills\` — `writing-for-agents`
(sharper contract edits), `codebase-design` (architecture-level gaps). Not
required.

## Inline fallback (also built)

The orchestrator (Claude) can run the exact same review inline using `SOUL.md`
as its instructions, writing the same files — used when the Hermes gateway is
down or the local model is busy building. The Bot's only edge is persistent
cross-session memory; the fallback re-reads `ledger.md` each time to compensate.

## Per-task invocation (orchestrator, once the WHOLE task is done + gates green)

Run the scout **once per task, at the end** — after every file in the task is
written and tsc/lint/build pass — not per file.

```
hermes -p ui_gap_scout chat --message "$(cat <<'EOF'
task_id: B03
spec_slice: <the ticket / spec-section text this task had to satisfy>
full_ask: <one-para reminder of the overall effort, so deferred != dropped>
prompts: <the exact prompt(s) sent to Model A, one per file>
raw_outputs: .scratch/finance-telemetry/raw/B03-*.json
gates: tsc pass; eslint pass; next build pass
fix_diff: <unified diff the human applied across the task, or "none">
retries: 1
EOF
)"
```

The bot appends one `ledger.md` entry for the task (with the `spec-match`
reconciliation + a `carry-forward` line), updates `prompt-contract.md` if a fail
tag has recurred, updates `improvement-progress.md`, and replies with the entry.
Its chat history in the profile **is** its memory.

## Consumed by the orchestrator

- **After each task:** feed the entry's `carry-forward` line into the next task's
  prompt (genuine drops + any now-due deferred items); prepend the current
  `prompt-contract.md` to every Model A prompt; **then `git commit` the task.**
- **Session end:** read `ledger.md` + `improvement-progress.md`; retune the
  build-ticket slicing (smaller slices for `over-length-truncation`-prone task
  types); fold the confirmed profile into the `local-model-build-loop` memory.

## Backfill

Before the first new build, seed `ledger.md` from the existing
`.scratch/finance-telemetry/` run (19 tasks, `raw/*.json` + `progress.md`).
See `ledger.md` header.
