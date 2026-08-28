# AGENTS.md — Kage

Read this first, every session. It carries the standing rules for this repo and
points to the living plan list.

## Rules

1. **Use the installed custom skills.** Check the available-skills list at session
   start and invoke the matching skill (Matt Pocock's set) before falling back to
   a default approach.
2. **Optimize cloud cost.** For every cloud service used, take the
   most cost-optimized option that still meets the requirement exactly.
3. **Stack.** Frontend: React 19, Tailwind CSS, Next.js, Three.js. Backend:
   Node.js + Express. New and rewritten code uses only these. (The current
   Python/FastAPI backends predate this rule and are migrated screen by screen —
   see [`PLANNED_WORK.md`](PLANNED_WORK.md).)
4. **Modular to the block.** Every page, every tab (Finance, Learning, Model, …),
   and every block within a page runs independently. A block gets its
   dependencies by calling them directly, not through a shared directory.
5. **Shrink the shared folders.** Whenever you touch code near
   `Shared_By_All_Agents/` or `Shared_By_All_Screens/`, move logic into the one
   caller that needs it and delete the shared file. These folders trend to empty.
6. **Track future work.** When a response or prompt names something to build
   later, append it to [`PLANNED_WORK.md`](PLANNED_WORK.md) and add a matching
   card in the Enhancement tab.

## Plans

Tracked in [`PLANNED_WORK.md`](PLANNED_WORK.md) with status and detail. Current
top-level items:

- **Observability** — replace a chosen block on every tab with an observability
  feature.
- **Complete modularity** — `Shared_By_All_Agents/` and `Shared_By_All_Screens/`
  fully removed by project end (Rule 5 is the day-to-day mechanism).
- **Enhancement tab** — build its UI and structure to display the tracked plans
  and data items.
