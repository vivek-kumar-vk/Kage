# KAGE Learning — Claude Chat work pack (office edition)

Storage is not wired yet. Until it is, **claude.ai chat is the staging area**: you
research there, it emits JSON that matches the Learning schema exactly, you paste
that JSON back into this repo later and an importer writes it to `learning.db`.
Nothing is retyped, nothing is re-researched.

Board today: 2 tracks · 13 modules · **101 rooms, 0 steps, 0 cards**. Rooms are
titles only — "planned, not taught". The point of the office day is to fill steps +
cards for the rooms you will actually study, **plus** pre-build the agents that
don't exist yet, so M8 becomes assembly instead of invention.

House rule that survives into chat, verbatim: **nothing records work that has not
happened.** Chat writes *content* (lessons, cards, agent prompts). Chat never writes
sessions, attempts, reviews, streaks, or lab proof.

**PII rule:** never paste `Screens/Learning/Context/*` (Master_Context, Resume_ATS,
14-week plan) or employer-identifying work-log detail into cloud chat. Those are
local-model-only (D17.3). Talk about topics, not about yourself.

---

## PROMPT A — paste once, as Claude Project instructions

Make a claude.ai Project named **"KAGE Learning"**. Paste everything between the
lines as its instructions. Every later message is then a one-liner.

--------------------------------- PASTE A ----------------------------------
You are the content factory for KAGE Learning OS — a local self-hosted learning
screen (FastAPI + SQLite + Next). I am a Splunk/observability engineer moving toward
forward-deployed AI engineering. I study in short windows: 15m morning drip, 45-60m
evening core, one 60m second-track slot, one daily TryHackMe slot.

The DB already holds tracks -> modules -> rooms. Rooms are empty titles. You produce
the content that goes INSIDE rooms, and the prompts/fixtures for agents that are not
built yet. You never invent my history: no sessions, no attempts, no reviews, no
streaks, no lab proof, no progress numbers. If you do not know, say UNKNOWN.

SCHEMA YOU WRITE INTO (exact field names — I paste your JSON into an importer):

room:       {id, name, est_minutes, feynman}
step:       {position, title, minutes, explain, realworld, lab_objective, lab_env,
             lab_link, lab_checklist: [string]}
checkpoint: {position, kind: "mcq"|"freetext", question, options: [string],
             answer_idx: int|null, model_answer: string|null}
card:       {front, part1..part5, tag: "core"|"drip"|"capture", tether}
note:       {room_id, step_position|null, body}

A room is taught in 4 beats per step, in this fixed order with these fixed names:
  beat 1 EXPLAIN    -> step.explain     plain-English mechanism, why it exists,
                                        where it breaks. 120-200 words, no fluff.
  beat 2 REAL WORLD -> step.realworld   a concrete incident / ticket / interview
                                        moment where this exact thing decides the
                                        outcome. 60-120 words.
  beat 3 LAB        -> lab_objective + lab_env + lab_link + lab_checklist
                                        something I can actually run: my own KAGE
                                        stack, a local container, a free tier, or a
                                        TryHackMe room. lab_env states exactly what
                                        must exist first. lab_checklist = 3-6 ticks,
                                        each an observable result, never "read about
                                        X". lab_link = a real URL or null — never a
                                        guessed URL.
  beat 4 CHECKPOINT -> 1-2 checkpoints, at least one freetext whose model_answer is
                                        written the way I would have to say it out
                                        loud in an interview.

Card parts are fixed and map to UI labels ELEVATOR / FOLLOW-UP / TRAP / REAL WORLD /
RESUME:
  part1  elevator answer, <=3 sentences, interview-grade
  part2  the likely follow-up question, plus its answer
  part3  the trap follow-up — what exposes someone who only memorised part1
  part4  real-world example (generic; I replace it later with my own work log)
  part5  resume connection — the one line this earns me, or "NOT YET DEFENSIBLE"

RESEARCH RULES
- Use web search for anything version-, product-, or pricing-dependent (Splunk 10.x,
  Dynatrace DQL/DPL/Grail/OpenPipeline, Bindplane, OpenTelemetry, Arize, THM rooms).
- Cite: every non-obvious claim gets a source URL and the date you saw it, collected
  in a SOURCES block at the end.
- Mark anything you could not verify as UNVERIFIED. I have a verify-then-keep gate in
  the app and I honour it. Do not smooth over gaps.
- Vendor docs > vendor blog > reputable third party > forum. Never a content farm.
- If two sources disagree on syntax, show both and say which is current.

OUTPUT DISCIPLINE
- Default output = one fenced json block validating against the shapes above, then a
  short SOURCES list. No preamble, no recap, no encouragement.
- When I ask for prose notes: write for a reader who must teach it back tomorrow.
  Mechanism first, commands and queries exact and runnable, zero marketing language.
- Never output my personal documents back to me, never ask for them.
- Concision over grammar. No emoji.
--------------------------------- END A ------------------------------------

---

## PROMPT B — the workhorse: one room -> a ROOM PACK

One line per room, new chat inside the project. Repeat all day.

--------------------------------- PASTE B ----------------------------------
ROOM PACK: room_id <ID> "<ROOM NAME>" (track: <Project->DevOps | Observability>)

4-6 steps totalling <= 60 minutes, full 4 beats each, plus 3-5 cards for the room and
a 2-sentence `feynman` prompt — the thing I must be able to explain back before the
room counts as done.

Return, in order:
1. one json block: {"room": {...}, "steps": [...], "cards": [...]}
2. NOTES — 300-500 words readable cold on a phone, mechanism-first.
3. SOURCES — url + date seen, one per line, UNVERIFIED flagged.
--------------------------------- END B ------------------------------------

**Office-day queue — day-job leverage first:**

| # | room_id | room | why now |
|---|---------|------|---------|
| 1 | 81 | Bindplane (day job) | you touch it at work; pays back same week |
| 2 | 76 | DQL — the query language | the differentiator, nothing on the board yet |
| 3 | 77 | DPL — the pattern language | pairs with DQL |
| 4 | 79 | OpenPipeline → Grail | where DQL/DPL actually run |
| 5 | 78 | OneAgent — deployment & host groups | interview staple |
| 6 | 80 | Migration story — SPL↔DQL parity | your headline story |
| 7 | 62 | SPL fundamentals | keeps the hunt current |
| 8 | 56 | Splunk architecture + component roles | screening-round bread and butter |
| 9 | 83 | Signals — logs, metrics, traces | frames everything above |
| 10 | 54 | Networking from ground 0 | ground floor, quick-checkpoint it |

Track 1 rooms are better at home with the repo open — their labs are "do it to KAGE".
Exceptions that work fine from the office: 43/44/45 (model routing), 46/47 (RAG
theory), 52 (cloud concepts).

---

## PROMPT C — the real headstart: build the agents before the agents exist

M8 is gated (no agent goes live until real data is wired), but an agent is 90%
**prompt + IO contract + eval fixtures** — all three writable now, droppable into
`services/crew.py` later. Do 2-3 of these between room packs.

--------------------------------- PASTE C ----------------------------------
AGENT SPEC: <AGENT>

Context: KAGE Learning OS. Every agent call goes through one local gateway
(OmniRoute, OpenAI-compatible, 127.0.0.1:8003). Agents never act unilaterally — they
write rows into proposals(agent, kind, summary, detail, status='pending') and I
approve or decline in the Crew tab. Every run logs to agent_runs(agent, text, source)
with tokens and cost. Cheap model by default. Anything touching my resume,
interviews, or work log is LOCAL-MODEL-ONLY.

Produce, in this order:
1. ROLE — 2 sentences.
2. SYSTEM PROMPT — final copy-paste text, including refusal rules and the
   never-fabricate-history rule.
3. INPUT CONTRACT — the exact JSON the service hands it, naming the DB tables or API
   routes each field comes from.
4. OUTPUT CONTRACT — strict JSON it must return, and how each field maps onto a
   proposals row.
5. MODEL ROUTING — cheap-default model class, when to escalate, hard local-only flag.
6. TRIGGER — cron/daily/weekly/on-event, at the cheapest cadence that still works.
7. FAILURE MODES — 3 ways it goes wrong plus the guard for each; cover hallucinated
   progress, runaway token spend, silent empty results.
8. EVAL FIXTURES — 3 synthetic input/expected-output pairs I can commit as tests.
   Synthetic only, obviously fake values, never realistic personal data.

Agents, one per message:
  PLANNER    weekly rebalance: actual minutes per track vs target -> reorder proposals
  QUIZMASTER checkpoint questions + card minting from a finished room
  TUTOR      re-explain + hint ladder (hint 1 never contains the answer)
  AUDITOR    Sunday gap report from Insights: stale rooms, weak cards, dead tracks
  RESEARCHER whitelist fetch -> raw items, no opinions
  CURATOR    digest + categorise fetched items; everything UNVERIFIED until I approve
  SCOUT      TryHackMe matchmaker: today's topics -> room pick + time estimate +
             evening streak-risk nudge. Never touches THM on my behalf.
  REPORTER   weekly funnel + apply nudges (Office screen)
  TAILOR     resume/JD variant drafts — LOCAL ONLY
  PREPARER   JD -> likely questions -> my STAR stories — LOCAL ONLY
--------------------------------- END C ------------------------------------

TAILOR and PREPARER: spec only. Do **not** feed real JD or resume text into cloud
chat — that pairing waits for the local model.

---

## PROMPT D — Curator / Scout seed data (highest value per token)

--------------------------------- PASTE D1 ---------------------------------
SIGNAL SOURCES: build the whitelist for the Researcher agent.

25-40 sources across: frontier-lab news (Anthropic, OpenAI, Google), Chinese open
models (DeepSeek, Qwen, Moonshot), agent tooling + MCP, RAG/eval tooling,
observability (Dynatrace, Splunk, OpenTelemetry, Bindplane, Grafana, Prometheus), and
TryHackMe / lab catalogues.

Per source: {name, url, feed_url|null, kind: blog|rss|release|catalog|forum, cadence,
why_it_matters, cost: free|login|paid}. Prefer RSS/Atom or a stable JSON endpoint over
scraping. Flag login-walled or scrape-hostile sources — those become manual-paste
sources, not fetches.

Output: one json array, then 5 lines on polite fetching (user agent, timeout, daily
batch, no polling storms).
--------------------------------- END D1 -----------------------------------

--------------------------------- PASTE D2 ---------------------------------
THM MAP: map TryHackMe rooms onto my board.

room_ids: 54 (networking ground 0), 55 (linux ground 0), 62 (SPL), 56 (Splunk
architecture), 83 (logs/metrics/traces), 86 (AWS identity + logging), 93-97 (parked
detection: linux telemetry, windows telemetry, MITRE, sigma, emulate->detect).

Per entry: {room_id, thm_room_name, thm_url, free_or_sub, est_minutes, prereqs,
what_it_proves}. Only rooms you can verify exist — mark UNVERIFIED rather than guess a
URL. Where TryHackMe is login-walled, say so; that becomes a one-time manual paste,
not a fetch.

This becomes steps.lab_link plus Scout's daily pick.
--------------------------------- END D2 -----------------------------------

---

## PROMPT E — end of every chat: emit the import bundle

So nothing is stranded in chat scrollback.

--------------------------------- PASTE E ----------------------------------
IMPORT BUNDLE. Collapse everything produced in this chat into one JSON object:

{"generated_at": "<ISO date>",
 "room_packs": [{"room_id": n, "room": {...}, "steps": [...], "cards": [...]}],
 "notes": [{"room_id": n, "step_position": n|null, "body": "..."}],
 "agent_specs": [{"agent": "...", "system_prompt": "...", "input_contract": {...},
                  "output_contract": {...}, "routing": {...}, "fixtures": [...]}],
 "signal_sources": [...],
 "thm_map": [...],
 "unverified": ["<claim> — <why unverified>"]}

Valid JSON only, no commentary. Nothing about my sessions, progress, or history.
--------------------------------- END E ------------------------------------

Save each as `bundle-YYYY-MM-DD.json`, all in one place (chat project files or a Drive
folder) until the importer exists.

---

## The plan this feeds — office notes to running app

1. **Office day (chat only).** Prompts B/C/D produce bundles. No repo access needed,
   no personal data leaves the machine.
2. **Home, same week.** Bundles land in `Screens/Learning/Context/bundles/`
   (gitignored, same rule as the rest of `Context/`).
3. **Importer** — `Screens/Learning/Backend/import_pack.py`, not yet written, ~1h of
   work. Reads a bundle, validates it against the schema above, writes ONLY
   steps / checkpoints / cards / notes / feynman. It refuses to write sessions,
   attempts, reviews or lab_proof, so the honest-zero invariant is enforced in code
   rather than by discipline. Idempotent per (room_id, step position).
4. **Cards enter review** as status `new`, due today — but a card only surfaces once
   its room has a real logged session. You never review what you never studied.
5. **M6 lab wiring.** `lab_link` from the THM map lights the TryHackMe line on Today;
   Scout's daily pick reads the same rows.
6. **M8 assembly.** Agent specs become `services/crew.py` prompts; fixtures become
   pytest cases. The gate holds — agents go live only after real data is wired, and
   every fetched item stays UNVERIFIED until you approve it.

Payoff: on day one of actual studying, rooms already hold real steps, real labs and
real cards, and the crew is a wiring job, not a design job.

**Open, non-blocking:**
- Bundle storage before Drive is wired — chat project files, or local folder?
- Cards per room: 3-5 (dense) or 1-2 (fast)?
- Parked detection rooms 93-101: content now, or stay title-only?
