# Calendar card setup (D23)

> **Faster — one command does all of this.** From PowerShell:
>
> ```powershell
> Main_Menu\Setup\connect_google_and_wakatime.ps1
> ```
>
> It opens each page, places the files and verifies each card afterwards.
> This doc is the reference for what it is doing and what each state means.
>
> Do **not** run `bash …connect_google_and_wakatime.sh` from PowerShell:
> there, `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, not Git
> Bash. With WSL absent or broken it exits silently and looks like nothing
> happened. The `.ps1` above finds the real Git Bash. Inside Git Bash itself,
> `bash Main_Menu/Setup/connect_google_and_wakatime.sh` is fine.

Two connections, independent. The card works with neither, one, or both —
whatever is missing says so in words rather than drawing an empty month
(Rule 8). Everything you create here lands in
`Main_Menu/Backend/Calendar_Data/`, which is gitignored (Rule 7).

---

## 1. Google Calendar

The card mirrors your calendar, and — only when you approve a proposal —
writes an event back to it. Writing is what makes the phone notification
fire; that is the whole point of the write scope.

**Scope used:** `https://www.googleapis.com/auth/calendar.events` — read
and write events. Not `calendar` (which would also allow deleting whole
calendars), not `.readonly` (which would never reach the phone).

### Steps (yours — Claude cannot do these)

1. <https://console.cloud.google.com> → same project you use for the
   Gmail card, or a new one.
2. **APIs & Services → Library** → enable **Google Calendar API**.
3. **APIs & Services → OAuth consent screen** → External, add your own
   address under **Test users**.
4. **Credentials → Create credentials → OAuth client ID → Desktop app**.
5. Download the JSON and save it as:

   ```
   Main_Menu/Backend/Calendar_Data/calendar_credentials.json
   ```

6. Start the Main Menu, then authorise once:

   ```
   curl -X POST http://127.0.0.1:8000/api/main_menu/calendar/connect
   ```

   A Google tab opens on port 8789. Approve it. The token is written to
   `Calendar_Data/calendar_token.json` and refreshed in place from then on.

7. Confirm:

   ```
   curl http://127.0.0.1:8000/api/main_menu/calendar/month
   ```

   `"state": "ok"` means it is mirroring.

### If you already did the Gmail card

Same project, same consent screen, same test user — you only need step 2
(enable Calendar API) and step 4 (a second Desktop client, or reuse the
Gmail one by copying the JSON to `calendar_credentials.json`). The two
cards keep separate tokens on purpose: revoking one never breaks the
other.

---

## 2. WakaTime

Auth is the plain **API key** over HTTP Basic, not OAuth. One local user
reading his own stats has no third party to consent, and an OAuth app
secret is one more thing to leak.

1. <https://wakatime.com/settings/api-key> → copy the key.
2. Create `Main_Menu/Backend/Calendar_Data/wakatime.json`:

   ```json
   { "api_key": "waka_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" }
   ```

   Or set `WAKATIME_API_KEY` in the environment — env wins.
3. Confirm:

   ```
   curl http://127.0.0.1:8000/api/main_menu/wakatime/summary
   ```

### The free plan's 7-day window

WakaTime's free tier exposes only the last week; your stats are retained
server-side but unreadable past that until you upgrade. So the sync loop
snapshots each day's summary into `calendar.sqlite` every cycle. History
accumulates from the day you add the key, regardless of plan — the WAKA
view's week bars and the month grid's coding tint both read the local
snapshot, not the API. `stats/last_7_days` still comes live from
WakaTime; a paid range that returns 402 is reported as a sentence and
the rest of the view keeps working.

---

## 3. The learning agent

Nightly (`CALENDAR_AGENT_HOUR`, default 22:00) it reads what actually
happened — WakaTime seconds, this repo's commits for that day, what was
already on the calendar, what the Email card flagged — and produces:

- **notes** — observations about the past. Written straight to the store;
  they are what you see when you hover a day.
- **proposals** — events it wants to add. **Not written to Google.** They
  sit as `pending` until you press *Add to calendar* in the day popover.

`CALENDAR_AUTO_WRITE=1` lets it write approved-by-default. It ships off.
Turn it on once you have watched a week of proposals and trust them.

Run it by hand any time:

```
curl -X POST "http://127.0.0.1:8000/api/main_menu/calendar/agent/run?days=3"
```

### Which brain

| `CALENDAR_AGENT_BACKEND` | What runs |
|---|---|
| `claude_cli` (default) | one `claude -p` per run — already logged in, no key in `.env` |
| `omniroute` | the same prompt to the gateway on 8003 (OpenAI-compatible), which is where Hermes and DeepSeek arrive |

Switch with `CALENDAR_AGENT_BACKEND=omniroute` and
`CALENDAR_AGENT_MODEL=<the gateway's model id>`. A brain that is not
reachable reports `offline` and the run is skipped — it never guesses
something onto a real calendar.

---

## Undo

A proposal that was written shows *on your calendar* in the popover.
Pressing **Dismiss** on it deletes the Google event again. Every event
the agent created carries `extendedProperties.private.kage_agent = "1"`,
so they are findable in the Google UI too.
