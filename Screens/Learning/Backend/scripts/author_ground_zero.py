"""Author the Ground Zero rooms' content (steps, checkpoints, recall cards).

Owner's call 2026-09-06: room content stops waiting on the M8 crew loop —
Claude authors it as the crew stand-in, grounded in Master_Context.md's
teaching rules (one concept at a time, 5-part recall format, hands-on
verification wherever a concept can be proven). The five rooms are the two
Ground Zero modules seeded by D17.2/D47:

  module "Ground Zero (project)"       -> rooms 34, 35, 36
  module "Ground Zero (observability)" -> rooms 54, 55

Idempotent: a room that already has steps is skipped entirely — re-running
never duplicates or rewrites content the owner has already studied. Content
is general lesson material (no PII), so this file is committed; learning.db
itself stays gitignored.

Run: .venv/Scripts/python Screens/Learning/Backend/scripts/author_ground_zero.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "learning.db"

# Per room: a list of steps. Each step is a dict matching the `steps` and
# `checkpoints` schema; `cards` ride at room level (5-part recall format:
# part1 elevator, part2 likely follow-up, part3 trap follow-up, part4 real
# world, part5 resume connection).
CONTENT: dict[int, dict] = {
    # ---- Ground Zero (project) -------------------------------------------
    34: {  # Git & GitHub from basics
        "steps": [
            {
                "title": "Snapshots, not diffs — what a commit really is",
                "minutes": 8,
                "explain": (
                    "Git stores a full snapshot of every tracked file at each commit, "
                    "plus a pointer to the parent commit(s). A branch is just a movable "
                    "pointer to one commit — which is why creating one costs nothing. "
                    "Between your working directory and the next commit sits the staging "
                    "area (the index): `git add` chooses *what* goes into the next "
                    "snapshot, `git commit` takes the picture. This three-stage model — "
                    "working tree, index, history — explains almost every 'weird' Git "
                    "behaviour: `git status` shows the gaps between the three, and "
                    "`git diff` vs `git diff --staged` compares different pairs of them."
                ),
                "realworld": (
                    "Kage's decision log says 'rationale lives in git history'. That only "
                    "works because commits are immutable snapshots: `git log -p AGENTS.md` "
                    "shows exactly what a decision changed and when, even months later."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "What does a Git commit actually contain?",
                    "options": [
                        "A diff from the previous commit plus a pointer to it",
                        "A full snapshot of tracked files plus parent pointer(s)",
                        "A compressed archive of the whole repository folder",
                        "A list of file names changed since the last commit",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "The daily loop — status, add, commit, log",
                "minutes": 8,
                "explain": (
                    "Ninety percent of Git usage is four commands. `git status` — what "
                    "changed and what's staged. `git add <path>` — stage it (or "
                    "`git add -p` to stage piece by piece, which keeps commits small). "
                    "`git commit -m \"reason\"` — record it. `git log --oneline` — read "
                    "the history. Undo tools slot into the same model: `git restore "
                    "<file>` throws away uncommitted work-tree changes, "
                    "`git restore --staged <file>` unstages without deleting, "
                    "`git revert <sha>` writes a *new* commit that undoes an old one — "
                    "safe on shared branches, unlike `git reset`, which rewinds history."
                ),
                "realworld": (
                    "Working rule in this repo: one commit per shipped step. A commit "
                    "message like 'Plan: active_imple.md' is a label you'll grep in six "
                    "months; 'stuff' is a label future-you cannot use."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": (
                        "You staged a file you didn't mean to include. It is NOT committed "
                        "yet, and you want to keep your edits. Name the command."
                    ),
                    "model_answer": (
                        "git restore --staged <file> (older spelling: git reset HEAD <file>). "
                        "It unstages but keeps the working-tree copy. git restore <file> "
                        "would have *deleted* the edits."
                    ),
                },
            },
            {
                "title": "Branches and merges without fear",
                "minutes": 10,
                "explain": (
                    "`git branch vivek/feature` creates a pointer; `git switch` moves to "
                    "it; commits now advance *that* pointer while main stays put. "
                    "`git merge` brings the line back together. If both lines touched the "
                    "same region, Git stops mid-merge and marks conflict markers "
                    "(<<<<<<< ======= >>>>>>>) inside the file — you edit to the wanted "
                    "result, `git add`, `git commit`. Rebase replays your commits on top "
                    "of another branch: cleaner history, but it rewrites commits, so only "
                    "rebase branches nobody else is building on. Rule of thumb used here: "
                    "feature branch per task, merge to main, delete the branch."
                ),
                "realworld": (
                    "This session works on branch vivek/main-menu-rubric-agentic-os. "
                    "Work happens on the vivek/* branch; main is what the owner reviews. "
                    "If a mid-air conflict appeared in active_imple.md, you'd open the "
                    "file, keep the intended lines, and commit the merge."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "Why is `git revert` preferred over `git reset` on a shared branch?",
                    "options": [
                        "revert is faster because it doesn't touch files",
                        "revert removes the bad commit from history entirely",
                        "revert adds a new undo commit instead of rewriting history",
                        "revert automatically pushes to the remote",
                    ],
                    "answer_idx": 2,
                },
            },
            {
                "title": "Remotes, pull requests, and what .gitignore protects",
                "minutes": 8,
                "explain": (
                    "A remote (usually `origin`) is another copy of the repo. "
                    "`git push` uploads your branch; `git pull` fetches and merges others' "
                    "work. On GitHub you open a *pull request* to propose merging your "
                    "branch — that's where review and CI happen. `.gitignore` lists paths "
                    "Git must never track. In Kage that line is a security boundary, not "
                    "tidiness: personal data lives in gitignored locations "
                    "(`kage-data/`, `learning.db`, `Screens/Learning/Context/`) so a "
                    "`git push` can never publish it. A file already tracked before it "
                    "was ignored stays tracked — `git rm --cached` stops tracking it."
                ),
                "realworld": (
                    "`git check-ignore Screens/Learning/Backend/learning.db` answers "
                    "'would a push leak this?'. Run it on any file you're unsure about "
                    "before committing — the check is cheaper than the leak."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": "Why does adding learning.db to .gitignore alone not remove it from a repo that already pushed it?",
                    "model_answer": (
                        ".gitignore only affects untracked files. An already-tracked file "
                        "keeps being committed, so you must also `git rm --cached "
                        "learning.db` and commit that removal — and the history still "
                        "holds old copies, which for real secrets means rotating them."
                    ),
                },
            },
        ],
        "cards": [
            {
                "front": "What does a Git commit store, and why does that make branches cheap?",
                "part1": "A commit is a full snapshot of tracked files plus parent pointer(s); a branch is just a movable pointer to a commit, so creating one is one file write — free.",
                "part2": "Likely follow-up: 'Then what is the staging area?' — the index: the exact contents the *next* commit will snapshot. add stages, status shows the three-way gap (working tree vs index vs history).",
                "part3": "Trap follow-up: 'So Git stores diffs, right?' — No. It stores snapshots and computes diffs on demand. Thinking in diffs is the #1 mental-model bug.",
                "part4": "Real world: `git log -p AGENTS.md` reconstructs the whole decision history of Kage because every commit holds the full file state.",
                "part5": "Resume connection: 'Git, branching and PR-based review' — you can explain the object model, not just memorise commands, which is what separates a TSE who uses Git from one who fears it.",
            },
            {
                "front": "revert vs reset vs restore — which undo does what?",
                "part1": "restore discards/unstages working changes; reset moves a branch pointer (rewinds local history); revert adds a new commit that undoes an old one — the only safe undo on shared/pushed history.",
                "part2": "Likely follow-up: 'When is reset fine?' — on a branch only you have, e.g. dropping half-made local commits before pushing.",
                "part3": "Trap follow-up: 'Is `git reset --hard` destructive?' — yes: it discards uncommitted work permanently. There is no trash can for uncommitted changes.",
                "part4": "Real world: a bad commit is already on origin/main → `git revert <sha>` + push. Same fix locally, unpushed → `git reset --hard HEAD~1`.",
                "part5": "Resume connection: incident hygiene — you can say 'I never rewrite shared history' and mean it, which is a trust signal in any platform role.",
            },
            {
                "front": "What does .gitignore actually protect in Kage, and what doesn't it protect?",
                "part1": "It stops *untracked* paths from being tracked — in Kage that's the PII/data boundary (kage-data/, learning.db, Context/). It does nothing for files already tracked: those need git rm --cached, and old history keeps them.",
                "part2": "Likely follow-up: 'How do you verify?' — `git check-ignore <path>` for 'would this be ignored?', `git ls-files <path>` for 'is it currently tracked?'.",
                "part3": "Trap follow-up: 'So secrets in .gitignore are safe forever?' — no: anything ever committed stays in history until history is rewritten, and clones/caches may retain it. Rotate real secrets.",
                "part4": "Real world: `git check-ignore Screens/Learning/Backend/learning.db` → ignored; that's why a routine `git add -A` on Kage can't leak study data.",
                "part5": "Resume connection: 'nothing personal in git' is a policy you can *enforce* — being the person who wires the boundary, not just follows it.",
            },
        ],
    },
    35: {  # Linux shell from basics
        "steps": [
            {
                "title": "One tree, one PATH — the shell's mental model",
                "minutes": 8,
                "explain": (
                    "Everything on Linux hangs off one root `/` (no C:\\ vs D:\\). Your "
                    "location is the working directory (`pwd`); `.` is here, `..` is up, "
                    "`~` is home. When you type a command, the shell searches the "
                    "directories listed in `$PATH`, left to right, and runs the first "
                    "match — `which python` shows which one won. That single fact "
                    "explains 'command not found' (not on PATH), wrong-version bugs "
                    "(earlier on PATH), and why `.venv/Scripts/activate` works: it "
                    "prepends the venv's bin dir to PATH. `echo $PATH` to see the order."
                ),
                "realworld": (
                    "Kage's launcher is run as `.venv/Scripts/python` — explicit path, "
                    "no PATH luck. Same discipline on a server: pin the interpreter, "
                    "don't inherit whatever happens to be first in PATH."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "You type `python` and get a different version than expected. First thing to check?",
                    "options": [
                        "Reinstall Python",
                        "`which python` and the order of dirs in $PATH",
                        "The file's execute bit",
                        "DNS resolution",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "Reading files like a log analyst — ls, cat, less, head, tail, grep, find",
                "minutes": 10,
                "explain": (
                    "`ls -la` — list with permissions and hidden files. `cat` dumps a "
                    "small file; `less` pages a big one (`/text` searches inside, `q` "
                    "quits). `head -n 20` / `tail -n 20` take the edges; `tail -f` "
                    "follows a growing file live. `grep -i pattern file` filters lines "
                    "(`-i` ignore case, `-r` recurse a folder, `-n` line numbers, `-c` "
                    "count, `-v` invert). `find <dir> -name \"*.log\" -mtime -1` finds "
                    "files by name/age/size. Pipes chain them: a *stream* flows from one "
                    "command into the next — `grep ERROR app.log | tail -n 5` is a "
                    "tiny pipeline."
                ),
                "realworld": (
                    "This is Splunk search at the metal: `grep -i timeout /var/log/app.log "
                    "| wc -l` is the same shape as `index=app timeout | stats count`. "
                    "The day Splunk is down, these commands are your search head."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": "Count lines mentioning 'connection refused' (case-insensitive) in /var/log/syslog. Write the command.",
                    "model_answer": (
                        "grep -ci 'connection refused' /var/log/syslog — -c counts, -i "
                        "ignores case. Without -c add | wc -l."
                    ),
                },
            },
            {
                "title": "Processes — ps, top, kill, and foreground vs background",
                "minutes": 8,
                "explain": (
                    "Every running program is a process with a PID. `ps aux` snapshots "
                    "all of them (user, PID, %CPU, %MEM, command); `top`/`htop` watch "
                    "live. A process attached to your terminal dies with it unless "
                    "backgrounded: `cmd &` runs now, `Ctrl+Z` then `bg` suspends-and-"
                    "resumes in background, `jobs` lists them, `fg` brings one back, "
                    "`nohup cmd &` survives logout. `kill <pid>` sends SIGTERM (please "
                    "exit); `kill -9` sends SIGKILL (kernel yanks it — no cleanup, use "
                    "last). `kill -l` lists all signals."
                ),
                "realworld": (
                    "The Kage launcher refuses a port another process holds *and names "
                    "that process* — finding the culprit is exactly `ps aux | grep 8002` "
                    "or `ss -tlnp | grep 8002`, then a deliberate kill."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "Why is `kill -9` a last resort?",
                    "options": [
                        "It only works on your own processes",
                        "The process gets no chance to clean up (flush buffers, close files)",
                        "It restarts the process automatically",
                        "It requires root always",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "Permissions and sudo — who may touch what",
                "minutes": 8,
                "explain": (
                    "Every file has an owner, a group and nine permission bits: `rwx` for "
                    "owner/group/others. `-rw-r--r--` = owner reads/writes, everyone else "
                    "reads. Directories need `x` to *enter* and `r` to *list*. `chmod` "
                    "changes bits (`chmod +x script.sh` makes it executable; octal 755 = "
                    "rwxr-xr-x), `chown` changes owner. Your identity lives in `id`; "
                    "`sudo` runs one command as root — the least privilege that works, "
                    "never a permanent root shell. `sudo -l` shows what you may run."
                ),
                "realworld": (
                    "Reading another user's logs and getting 'permission denied' is a "
                    "permissions fact, not a bug: `/var/log` files are group-readable at "
                    "best. On a Splunk UF it's why the splunk user needs explicit read "
                    "on every monitored file — the same bits, one layer up."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": "A script won't run: 'Permission denied'. You own the file. What are the two most likely causes and fixes?",
                    "model_answer": (
                        "(1) Not executable → chmod +x script.sh. (2) The *directory* "
                        "lacks x for you, or the interpreter line targets a file you "
                        "can't read — check with ls -ld on the dir and head -1 the "
                        "shebang."
                    ),
                },
            },
        ],
        "cards": [
            {
                "front": "What happens when you type a command and press Enter?",
                "part1": "The shell searches $PATH left-to-right and execs the first match, with stdin/stdout wired to your terminal (or the pipes you set). Not found = not on PATH.",
                "part2": "Likely follow-up: 'How do you see which binary runs?' — `which <cmd>` (or `type <cmd>`), and `echo $PATH` for the search order.",
                "part3": "Trap follow-up: 'Does the shell search the current directory too?' — No, unlike Windows. `./script.sh` is required precisely because '' is not in PATH — a security feature.",
                "part4": "Real world: activating a venv prepends its bin dir, so `python` resolves to the venv — that's the whole trick, no magic.",
                "part5": "Resume connection: 'wrong binary/version' is a weekly support ticket; explaining PATH resolution is the difference between rebooting a box and fixing it.",
            },
            {
                "front": "grep is Splunk search without Splunk — what maps to what?",
                "part1": "grep filters lines by pattern in files/streams; pipes compose stages. `grep -i err f.log | tail` ≈ `index=f err | head`. -c counts, -v inverts, -r recurses, -n numbers lines.",
                "part2": "Likely follow-up: 'How is it different from SPL?' — SPL runs distributed over indexed data with fields; grep is line-oriented over raw files. Same discipline, no index.",
                "part3": "Trap follow-up: 'grep pattern * searches subdirectories?' — No, only the glob matches. Use `grep -r pattern dir/`.",
                "part4": "Real world: `tail -f /var/log/app.log | grep -i timeout` is a live tail with a filter — the poor man's real-time search when a UI isn't available.",
                "part5": "Resume connection: your SPL skill is proof you already think in filter→transform pipelines; shell fluency makes that claim credible at the OS layer too.",
            },
            {
                "front": "SIGTERM vs SIGKILL — and why -9 is last?",
                "part1": "kill sends SIGTERM by default: the process may flush buffers, close sockets, exit cleanly. kill -9 (SIGKILL) is the kernel terminating it with no handler — last resort.",
                "part2": "Likely follow-up: 'How do you find the PID?' — `ps aux | grep name`, or better `pgrep -f name`; `ss -tlnp | grep <port>` maps a port to its process.",
                "part3": "Trap follow-up: 'Can a process ignore SIGKILL?' — effectively yes while stuck in uninterruptible disk sleep (D state) — it dies only when the I/O returns; the load average shows it.",
                "part4": "Real world: the Kage launcher reports which process holds a port; you TERM it first and only escalate to -9 if it ignores the request.",
                "part5": "Resume connection: graceful-shutdown discipline is an SRE/observability value — you know *why* an unclean kill corrupts data and hides the very errors you monitor for.",
            },
        ],
    },
    36: {  # Networking the project uses (DNS, HTTP, ports, localhost)
        "steps": [
            {
                "title": "Localhost and the loopback interface",
                "minutes": 8,
                "explain": (
                    "`127.0.0.1` (IPv6 `::1`, name `localhost`) is the loopback "
                    "interface: traffic sent there never leaves the machine — the kernel "
                    "loops it back internally. A server that *binds* to 127.0.0.1 is "
                    "unreachable from any other device no matter what firewall says; "
                    "binding to 0.0.0.0 means 'all interfaces' and *is* reachable. This "
                    "is the difference between a private service and an exposed one."
                ),
                "realworld": (
                    "Every Kage screen binds loopback, and OpenClaw's gateway uses "
                    "`--bind loopback` so a missing auth token still can't be reached "
                    "off-box. Same habit on a Splunk deployment server: management port "
                    "on a private interface or you're advertising an attack surface."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "A service binds 127.0.0.1:8009. Who can connect?",
                    "options": [
                        "Anyone on the LAN",
                        "Only processes on the same machine",
                        "Anyone, if the firewall allows it",
                        "Only root",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "Ports — one port per service",
                "minutes": 8,
                "explain": (
                    "An IP address finds a machine; the port finds the *program* on it. "
                    "Ports 0–65535: well-known 0–1023 (need root to bind), registered "
                    "1024–49151, ephemeral above that (the random client side of a "
                    "connection). One listening socket per (interface, port) — the "
                    "second binder gets 'address already in use' (EADDRINUSE). "
                    "`ss -tlnp` (or netstat) lists what's listening: address, port, "
                    "process. 'One port per screen, written in one place' is exactly "
                    "this rule applied to a codebase."
                ),
                "realworld": (
                    "Kage's port table (8000 menu, 8002 finance, 8003 learning…) is a "
                    "port allocation map, like Splunk's 8000/8089/9997/514 conventions. "
                    "When two services want one port, the fix is a decision in one "
                    "config file, not a bug hunt."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": "Your FastAPI screen fails with 'address already in use' on 8002. What happened and name the check.",
                    "model_answer": (
                        "Another process already holds a listening socket on that "
                        "interface:port. Check: `ss -tlnp | grep 8002` (or netstat) to "
                        "see which process — then stop it or move the port."
                    ),
                },
            },
            {
                "title": "DNS — turning names into addresses",
                "minutes": 8,
                "explain": (
                    "DNS resolves names to IPs through a resolver chain: your OS cache, "
                    "then the configured resolver, then the hierarchy (root → TLD → "
                    "authoritative). Answers carry a TTL — how long caches may keep "
                    "them. `/etc/hosts` (Windows: `C:\\Windows\\System32\\drivers\\etc"
                    "\\hosts`) overrides DNS for local names. Tools: `nslookup name`, "
                    "`dig name` (full answer + TTL). Split-horizon and stale-cache "
                    "problems are both TTL/override problems at heart."
                ),
                "realworld": (
                    "`groww.in` resolving to a CDN IP that changes by TTL is why a "
                    "scraper must not cache IPs. And `/etc/hosts` is how a lab points "
                    "`splunk.example.local` at 127.0.0.1 without a real DNS server."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "A hostname resolves to a stale IP after a server move. Most likely cause?",
                    "options": [
                        "TCP window size",
                        "A cached DNS answer not yet past its TTL",
                        "Wrong subnet mask",
                        "MTU mismatch",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "HTTP — requests, responses, and honest status codes",
                "minutes": 10,
                "explain": (
                    "HTTP is request/response text over TCP: method + path + headers "
                    "(+ body). GET reads (safe, cacheable), POST creates/acts, "
                    "PUT/PATCH replace/modify, DELETE removes. Status families: 2xx "
                    "ok, 3xx redirect, 4xx *client* error (400 bad request, 401 "
                    "unauthenticated, 403 forbidden, 404 no such thing), 5xx *server* "
                    "error. The status code is part of the contract: returning 200 "
                    "with an error payload (or 404 for something that exists but is "
                    "empty) breaks every client, monitor and cache that trusts it."
                ),
                "realworld": (
                    "Kage's API rule: a thing that is down says so — a 404 on the "
                    "benchmark endpoint is what makes the UI render 'NO BENCHMARK "
                    "LOADED'. A fabricated 200 would render fake data instead. Same "
                    "logic as a Splunk HEC 400 on bad event data: the code *is* the "
                    "message."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "GET /api/x returns 200 with body {\"error\": \"not found\"}. What's wrong?",
                    "options": [
                        "Nothing — 200 just means the server responded",
                        "It should be 404: the status code must match the outcome",
                        "It should be 500",
                        "It should be 301",
                    ],
                    "answer_idx": 1,
                },
            },
        ],
        "cards": [
            {
                "front": "127.0.0.1 vs 0.0.0.0 — what does binding to each mean?",
                "part1": "127.0.0.1 = loopback only: same-machine clients, unreachable from outside regardless of firewall. 0.0.0.0 = every interface: LAN/Internet can reach it (firewall permitting).",
                "part2": "Likely follow-up: 'What about ::1?' — IPv6 loopback; some stacks resolve 'localhost' to it first, which is why a service bound only to IPv4 may seem 'down' to an IPv6 client.",
                "part3": "Trap follow-up: 'Does binding loopback make a service secure?' — It removes *network* exposure only; local users/processes can still reach it, so auth still matters.",
                "part4": "Real world: every Kage screen binds loopback; OpenClaw's gateway pairs loopback with token auth — defence in depth, not either/or.",
                "part5": "Resume connection: you've onboarded HEC/syslog inputs on Splunk Cloud — knowing which interface a listener binds is the same question you'd ask before opening 9997.",
            },
            {
                "front": "What does a port number actually identify, and how do you see who owns one?",
                "part1": "The program (socket) on a machine — IP finds the host, port finds the process. One listener per interface:port; the next binder gets EADDRINUSE. `ss -tlnp` maps ports to processes.",
                "part2": "Likely follow-up: 'Ranges?' — 0–1023 privileged/well-known, 1024–49151 registered, the rest ephemeral client ports.",
                "part3": "Trap follow-up: 'Can two processes share a port?' — Not as plain listeners; only via SO_REUSEPORT (kernel load-balancing) — not the same as sharing.",
                "part4": "Real world: Kage's launcher refuses to start a screen whose port is held and names the holder — 'one port per screen, written once' enforced at boot.",
                "part5": "Resume connection: Splunk's port map (8000 SH, 8089 mgmt, 9997 receiving, 514 syslog) is the same mental model — you already reason in port allocation tables.",
            },
            {
                "front": "Why is a 404 sometimes more honest than a 200?",
                "part1": "The status code is the machine-readable outcome: 4xx = the thing you asked for isn't there / request is bad; 5xx = the server failed. A 200-with-error-payload lies to caches, monitors and clients.",
                "part2": "Likely follow-up: '401 vs 403?' — 401: who are you (not authenticated); 403: I know who you are and you may not (not authorised).",
                "part3": "Trap follow-up: 'Is 204 fine for 'no data yet'?' — 204 means success with no body; if the resource *doesn't exist*, 404 is correct. Empty-but-existing can be 200 with an empty payload.",
                "part4": "Real world: Kage's Finance UI renders 'NO BENCHMARK LOADED' *because* the benchmark endpoint 404s while unloaded — the honest failure drives honest UI.",
                "part5": "Resume connection: you troubleshoot platform APIs for a living; reading status codes precisely (HEC 400 vs 403 vs 5xx) is a skill you can name in an interview.",
            },
        ],
    },
    # ---- Ground Zero (observability) -------------------------------------
    54: {  # Networking from ground 0 (TCP/IP, ports & protocols)
        "steps": [
            {
                "title": "The TCP/IP layers in one pass",
                "minutes": 10,
                "explain": (
                    "Four working layers, each wrapped by the one below: application "
                    "(HTTP, DNS, syslog) → transport (TCP/UDP — ports) → internet "
                    "(IP — addressing and routing) → link (Ethernet/Wi-Fi — actual "
                    "frames). Each layer adds a header; on receive they're stripped in "
                    "reverse. Troubleshooting walks the stack from the bottom: link up? "
                    "IP reachable (`ping`)? port open (`ss`, `nc`)? application answering "
                    "(`curl -v`)? Diagnosing 'Splunk UF can't reach the indexer' is this "
                    "checklist in order — never start at the application layer."
                ),
                "realworld": (
                    "A forwarder 'down' that pings fine but fails `nc -zv idx 9997` is "
                    "a port/firewall problem, not DNS. Two commands localise the layer; "
                    "guessing wastes an hour."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "Ping works but the app connection fails. Which layer do you suspect next?",
                    "options": [
                        "Link layer",
                        "Internet layer",
                        "Transport layer (port/firewall) or the app itself",
                        "DNS immediately",
                    ],
                    "answer_idx": 2,
                },
            },
            {
                "title": "TCP vs UDP — reliability and what it costs",
                "minutes": 8,
                "explain": (
                    "TCP is a conversation: three-way handshake (SYN, SYN-ACK, ACK), "
                    "sequence numbers, retransmission, ordering, flow control — reliable "
                    "but heavier. UDP is a datagram: send and hope — no handshake, no "
                    "retry, minimal overhead, preserves message boundaries. HTTP, HEC "
                    "and Splunk's 9997 all ride TCP because loss is unacceptable; "
                    "classic syslog rides UDP/514 because a dropped line beats a "
                    "blocked pipeline. Consequence to internalise: UDP senders can "
                    "silently lose events under load or MTU problems — TCP senders "
                    "queue and back up instead."
                ),
                "realworld": (
                    "A firewall that silently *drops* (not rejects) UDP/514 makes a "
                    "syslog source look 'intermittent' — the sender never learns. The "
                    "same source over TCP or HEC would error loudly instead."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "Why can UDP syslog quietly lose events under network stress?",
                    "options": [
                        "UDP has smaller maximum message size by standard",
                        "No retransmission — a dropped datagram is gone, sender isn't told",
                        "UDP requires an ACK that the firewall blocks",
                        "UDP cannot cross routers",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "Sockets and the ports an observability stack lives on",
                "minutes": 8,
                "explain": (
                    "A socket = (protocol, local IP, local port, remote IP, remote "
                    "port). Servers *listen*; each accepted connection gets its own "
                    "socket on the same port. `ss -tlnp` lists listeners, "
                    "`ss -tn state established` shows live connections, "
                    "`nc -zv host port` tests reachability, `traceroute` shows the "
                    "path. Know your stack's table cold: Splunk UI 8000, management "
                    "8089, indexer receiving 9997, syslog 514; HEC 8088; Dynatrace "
                    "OneAgent → cluster on 443."
                ),
                "realworld": (
                    "'UF not forwarding' triage in three commands: `ss -tlnp | grep "
                    "9997` on the indexer (is it listening?), `nc -zv <idx> 9997` from "
                    "the forwarder (path open?), then `splunk btool` / outputs.conf "
                    "(is it configured to try?)."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": "Name the three Splunk ports you'd check first when a universal forwarder sends nothing, and what each does.",
                    "model_answer": (
                        "9997 indexer receiving (the data path), 8089 management "
                        "(deployment/REST, phone-home), 8000 web UI (not the data path "
                        "but proves the instance is up). Optionally 8088 HEC if the "
                        "source is HTTP-based."
                    ),
                },
            },
            {
                "title": "DNS and TLS on the path logs actually take",
                "minutes": 10,
                "explain": (
                    "Two silent failure sources sit under every connection. DNS: a name "
                    "that resolves to the wrong/old IP sends your logs to a stranger or "
                    "nowhere — `dig <name>` and TTL explain 'it worked yesterday'. "
                    "TLS: most endpoints *require* certificates now, and the client "
                    "validates the chain, hostname and expiry — a self-signed or "
                    "expired cert fails the connection with a TLS error, not a "
                    "timeout. Common on-prem pattern: point the client at the CA "
                    "bundle (Splunk: `sslRootCAPath`; curl: `--cacert`) or the "
                    "connection dies before any application logic runs."
                ),
                "realworld": (
                    "Forwarder → indexer TLS: `outputs.conf` `sslVerifyServerCert` + "
                    "the CA. When it breaks, the error is 'SSL handshake failed', "
                    "which people misread as 'indexer down' — the handshake never "
                    "got past trust, so check cert chain/expiry first."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "UF log shows 'SSL handshake failed' to the indexer. First check?",
                    "options": [
                        "Indexer disk usage",
                        "Certificate chain/expiry and the client's CA configuration",
                        "Indexer's license",
                        "TCP port 9997 reachable",
                    ],
                    "answer_idx": 1,
                },
            },
        ],
        "cards": [
            {
                "front": "Walk the TCP/IP layers bottom-up and say which tool tests each.",
                "part1": "Link (cable/Wi-Fi) → Internet: ping → Transport: nc/ss on the port → Application: curl -v / the client's own log. Troubleshoot bottom-up, never start at the app.",
                "part2": "Likely follow-up: 'Where does DNS sit?' — Application layer (a service dependency); test it explicitly with dig when anything name-based fails.",
                "part3": "Trap follow-up: 'Ping succeeds so the network is fine?' — No: ping proves ICMP/Internet only. TCP 9997 can still be firewalled — different layer.",
                "part4": "Real world: 'UF down' → ping ok → `nc -zv idx 9997` refused → it's a receiving-port/firewall issue, found in 30 seconds by layer order.",
                "part5": "Resume connection: you've onboarded monitor/scripted/TCP-UDP/REST inputs — this checklist is the actual method behind 'log source onboarding' on your resume.",
            },
            {
                "front": "TCP vs UDP — what does each trade, and where does your stack use them?",
                "part1": "TCP: handshake, retransmit, order, backpressure — reliable, heavier (HTTP, HEC 8088, Splunk 9997). UDP: fire-and-forget, tiny overhead, silent loss (classic syslog 514).",
                "part2": "Likely follow-up: 'Why does syslog still use UDP?' — legacy senders and 'never block the app' philosophy; modern practice prefers TCP/syslog over TLS or HEC for delivery guarantees.",
                "part3": "Trap follow-up: 'UDP loss shows as sender errors?' — No — that's the point: the sender is never told. Loss shows as *missing events*, found by count comparison.",
                "part4": "Real world: a 'flaky' syslog source that's actually a silent-drop firewall rule; switching the input to TCP makes the failure visible and diagnosable.",
                "part5": "Resume connection: choosing TCP vs UDP vs HEC for a source *is* pipeline design — a differentiator line in interviews for support-to-platform roles.",
            },
            {
                "front": "What does a TLS handshake failure mean, and what do you check first?",
                "part1": "The TCP connection succeeded but trust failed: certificate chain, hostname mismatch or expiry. Check cert validity (openssl s_client -connect host:port) and the client's CA config (sslRootCAPath / --cacert).",
                "part2": "Likely follow-up: 'Difference from a timeout?' — timeout = packets never answered (routing/firewall); handshake failure = we talked but didn't trust each other.",
                "part3": "Trap follow-up: 'Is disabling verification a fix?' — It's a hole, not a fix: it converts a trust failure into a MITM risk. Install the proper CA instead.",
                "part4": "Real world: UF → indexer 'SSL handshake failed' after a cert rotation — re-deploying the CA bundle to forwarders fixes it; restarting Splunk does not.",
                "part5": "Resume connection: post-upgrade validation and RCA work you've done is full of TLS trust issues — being precise here sounds senior, not lucky.",
            },
        ],
    },
    55: {  # Linux from ground 0 (filesystem, processes, services, logs)
        "steps": [
            {
                "title": "The filesystem map — where Linux keeps everything",
                "minutes": 10,
                "explain": (
                    "One tree from `/`. The directories that matter daily: `/etc` "
                    "(configuration), `/var/log` (logs), `/var/lib` (state/data), "
                    "`/proc` and `/sys` (kernel-virtual: process and hardware as "
                    "files), `/usr/bin` `/usr/sbin` (programs), `/home` (users), `/tmp` "
                    "(ephemeral), `/opt` (third-party stacks — Splunk installs here). "
                    "Everything is a file, including disks (`/dev/sda1`) and running "
                    "processes (`/proc/<pid>/`). Mount points graft other filesystems "
                    "onto the tree — `df -h` shows what's mounted and how full, "
                    "`du -sh <dir>` shows what's eating space."
                ),
                "realworld": (
                    "Splunk default paths are this map: /opt/splunk (etc/, var/), "
                    "indexes under /opt/splunk/var/lib/splunk. 'Indexer disk 95%' → "
                    "`du -sh /opt/splunk/var/lib/splunk/*` finds which index grew."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "Where does a package-installed service's configuration most likely live?",
                    "options": [
                        "/usr/bin",
                        "/etc",
                        "/var/log",
                        "/tmp",
                    ],
                    "answer_idx": 1,
                },
            },
            {
                "title": "Processes and services — systemd in practice",
                "minutes": 10,
                "explain": (
                    "Process basics first: `ps aux`, `top`, `kill -TERM <pid>` before "
                    "`-KILL`. Services are processes managed by systemd (PID 1): "
                    "`systemctl status <unit>` (running? enabled?), `systemctl "
                    "start|stop|restart <unit>`, `systemctl enable` (start at boot). "
                    "Unit files live in `/etc/systemd/system/` (yours) and "
                    "`/usr/lib/systemd/system/` (packages); after editing, "
                    "`systemctl daemon-reload`. `journalctl -u <unit>` reads that "
                    "unit's logs; `-f` follows; `--since today` bounds time. "
                    "`systemd-analyze verify` catches unit-file typos."
                ),
                "realworld": (
                    "A Splunk UF installed as a service is `systemctl status SplunkForwarder` "
                    "on many boxes. 'Agent down after reboot' is almost always "
                    "`systemctl is-enabled` saying disabled — enable it, then verify "
                    "with status."
                ),
                "checkpoint": {
                    "kind": "freetext",
                    "question": "A service runs now but was gone after the last reboot. One command to confirm why, and the fix.",
                    "model_answer": (
                        "`systemctl is-enabled <unit>` → disabled (not started at boot). "
                        "Fix: `systemctl enable <unit>` (and start it now with start)."
                    ),
                },
            },
            {
                "title": "Logs — where the truth lives",
                "minutes": 10,
                "explain": (
                    "Three log regimes coexist: classic plain files under `/var/log` "
                    "(`syslog`/`messages`, `auth.log` for logins, `kern.log`, app "
                    "logs); journald (systemd's binary journal, read via `journalctl`, "
                    "may or may not be persistent — `/var/log/journal/` existing means "
                    "it is); and application-specific logs that write their own files. "
                    "Read with `tail -f`, filter with `grep`, bound with `--since`/"
                    "`--until` on journalctl. Rotation (logrotate) renames and "
                    "compresses — that's why filenames have `.1`/`.gz` suffixes. "
                    "Security telemetry comes from these same sources: auditd, PAM "
                    "entries in auth.log, FIM — a pointer at the Detection track."
                ),
                "realworld": (
                    "Before Splunk ever indexes a source, someone read it locally: "
                    "`grep -i failed /var/log/auth.log` is the zero-infrastructure "
                    "SSH brute-force check — the same detection, un-shipped."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "journalctl shows nothing for an old incident. Likely cause?",
                    "options": [
                        "The journal is volatile (not persistent) and was lost at reboot",
                        "journalctl only shows kernel logs",
                        "The unit was restarted",
                        "Logs moved to /proc",
                    ],
                    "answer_idx": 0,
                },
            },
            {
                "title": "Users, privilege, and PAM — how access is decided",
                "minutes": 8,
                "explain": (
                    "Accounts live in `/etc/passwd` (shadow hashes in `/etc/shadow`); "
                    "groups in `/etc/group`. `id`, `who`, `last` show identity and "
                    "history. Root bypasses permission checks; `sudo` delegates it "
                    "per `/etc/sudoers` (edit via `visudo` only). Login itself is a "
                    "pipeline: PAM (pluggable authentication modules, configured "
                    "under `/etc/pam.d/`) decides what counts as proof — password, "
                    "key, MFA. SSH keys: `~/.ssh/authorized_keys` grants, "
                    "`ssh -v user@host` shows which method was attempted and why it "
                    "failed. `failed` entries in `auth.log`/`secure` are the raw "
                    "material of brute-force detections."
                ),
                "realworld": (
                    "'I can't SSH in' support tickets resolve in order: network/port → "
                    "sshd running (`systemctl status sshd`) → auth method "
                    "(`ssh -v`, auth.log) → account/permission. Each step names its "
                    "own log line — that's the habit this room builds."
                ),
                "checkpoint": {
                    "kind": "mcq",
                    "question": "What does PAM decide?",
                    "options": [
                        "Which ports a service may bind",
                        "What counts as valid authentication for a service",
                        "File permissions for new files",
                        "The order of DNS resolvers",
                    ],
                    "answer_idx": 1,
                },
            },
        ],
        "cards": [
            {
                "front": "Which Linux directories hold config, logs, state and third-party installs?",
                "part1": "Config: /etc. Logs: /var/log. State/data: /var/lib. Third-party stacks: /opt. Kernel/process pseudo-files: /proc, /sys. Programs: /usr/bin, /usr/sbin.",
                "part2": "Likely follow-up: 'How do you find what's eating disk?' — `df -h` for which mount, `du -sh <dir>/*` descending into the biggest.",
                "part3": "Trap follow-up: 'Is /etc for executables?' — No: /etc is configuration only; binaries live in /usr/bin, /usr/sbin and /opt.",
                "part4": "Real world: Splunk under /opt/splunk (etc/ + var/) — knowing the FHS by heart means you can navigate any fresh box without asking where things are.",
                "part5": "Resume connection: end-to-end onboarding of log sources starts at /var/log on a machine you've never seen — this map is that job's first ten minutes.",
            },
            {
                "front": "systemctl vs journalctl — what does each answer?",
                "part1": "systemctl answers 'what state is the service in' (running, enabled, failed); journalctl answers 'what did it say' (-u <unit>, -f follow, --since to bound time).",
                "part2": "Likely follow-up: 'Where are unit files?' — /etc/systemd/system (yours) and /usr/lib/systemd/system (packages); run daemon-reload after edits.",
                "part3": "Trap follow-up: 'systemctl restart fixed it, so is it fixed?' — Not until you know why it died: journalctl --since with the crash window; otherwise you've treated the symptom.",
                "part4": "Real world: 'forwarder down after reboot' → is-enabled shows disabled → enable it — a 30-second fix you'd never find staring at the forwarder UI.",
                "part5": "Resume connection: 100% SLA support is triage speed — 'state or message first' is the reflex your P2/P4 record claims you already have.",
            },
            {
                "front": "Where does Linux keep login evidence, and what can you detect from it?",
                "part1": "auth.log (Debian) / secure (RHEL) + journalctl: successful/failed logins, sudo usage, SSH key offers. auditd adds syscall-level records; `last`/`who` summarise sessions.",
                "part2": "Likely follow-up: 'What's a quick brute-force check?' — `grep -c 'Failed password' /var/log/auth.log` and per-source counts with grep/awk.",
                "part3": "Trap follow-up: 'Is journald enough for security?' — No: it's often volatile and binary; persistent, indexed telemetry (auditd → forwarder) is what detections need.",
                "part4": "Real world: the same auth.log lines Splunk indexes are the ones you'd grep by hand — proving a detection's source before writing the SPL.",
                "part5": "Resume connection: this is the seam your Track B (detection engineering) builds on — Linux security telemetry is dependency #1 there, and you already operate its big brother at work.",
            },
        ],
    },
}


def _room(cur, room_id: int):
    cur.execute("SELECT id, name FROM rooms WHERE id=?", (room_id,))
    return cur.fetchone()


def main() -> int:
    if not DB.exists():
        print(f"learning.db not found at {DB}")
        return 1
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    authored, skipped = [], []
    for room_id, spec in CONTENT.items():
        row = _room(cur, room_id)
        if row is None:
            print(f"room {room_id} missing — seed.py out of date? skipped")
            continue
        have = cur.execute(
            "SELECT COUNT(*) FROM steps WHERE room_id=?", (room_id,)
        ).fetchone()[0]
        if have:
            skipped.append(row["name"])
            continue
        for pos, s in enumerate(spec["steps"]):
            cp = s["checkpoint"]
            cur.execute(
                """INSERT INTO steps (room_id, position, title, minutes, explain,
                     realworld, lab_objective, lab_checklist)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    room_id, pos, s["title"], s["minutes"], s["explain"],
                    s["realworld"], s.get("lab_objective"), json.dumps(s.get("lab_checklist", [])),
                ),
            )
            step_id = cur.lastrowid
            cur.execute(
                """INSERT INTO checkpoints (step_id, position, kind, question,
                     options, answer_idx, model_answer)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    step_id, 0, cp["kind"], cp["question"],
                    json.dumps(cp.get("options", [])), cp.get("answer_idx"),
                    cp.get("model_answer"),
                ),
            )
        for card in spec["cards"]:
            cur.execute(
                """INSERT INTO cards (room_id, front, part1, part2, part3, part4,
                     part5, tag) VALUES (?,?,?,?,?,?,?,'core')""",
                (
                    room_id, card["front"], card["part1"], card["part2"],
                    card["part3"], card["part4"], card["part5"],
                ),
            )
        authored.append(f"{row['name']} ({len(spec['steps'])} steps, {len(spec['cards'])} cards)")
    conn.commit()
    conn.close()
    for name in authored:
        print(f"authored: {name}")
    for name in skipped:
        print(f"skipped (already has steps): {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
