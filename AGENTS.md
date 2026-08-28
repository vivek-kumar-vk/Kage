# AGENTS.md — Kage

Read this first, every session. Standing rules for this repo; the plan list is
[`PLANNED_WORK.md`](PLANNED_WORK.md).

## Rules

1. **Use the installed custom skills.** Check the skill list at session start and
   invoke the matching skill before falling back to a default approach.
2. **Optimize cloud cost** — for any cloud service, take the cheapest option that
   still meets the requirement exactly.
   - **2.1 (supersedes 2)** — **Optimize Claude Code (Sonnet) usage while
     building this project.** Fewest tokens and tool calls for the outcome: batch
     independent calls, reuse earlier findings instead of re-exploring, keep
     context lean.
3. **Stack.** Frontend: React 19, Tailwind CSS, Next.js, Three.js. Backend:
   Node.js + Express. New and rewritten code uses only these; the current
   Python/FastAPI backends migrate screen by screen (`PLANNED_WORK.md` P4).
4. **Modular to the block.** Every page, tab, and block within a page runs
   independently and calls its dependencies directly, never through a shared
   directory.
5. **Shrink the shared folders.** When you work near `Shared_By_All_Agents/` or
   `Shared_By_All_Screens/`, move logic into its one caller and delete the shared
   file. These folders trend to empty.
6. **Track future work.** Anything named as "later" goes to `PLANNED_WORK.md` and
   a card in the Enhancement tab.
7. **Log every instruction as a numbered item** — a Rule, a Plan
   (`PLANNED_WORK.md`), or a Task. New topic gets a new number. A change to item
   _N_ is filed as _N.1_, _N.2_, …; the highest sub-number is the one in force
   and the parent stays as history. Before adding, diff against what is already
   here and keep only what is new.
8. **Number every logical and design decision** the same way (`D1`, `D1.1`, …),
   wherever it is recorded — not only rules and plans.

## Plans

[`PLANNED_WORK.md`](PLANNED_WORK.md) holds the list with status and detail. Top
items: observability on every tab; remove `Shared_By_All_Agents/` and
`Shared_By_All_Screens/` entirely; build the Enhancement tab UI.
