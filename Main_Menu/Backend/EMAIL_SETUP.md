# Email card setup (D22)

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

The card reads Gmail **read-only** and sorts it with a short-lived
`claude -p` run. It never sends, never replies, never deletes — the scope
it asks for cannot do any of those things.

Everything personal — OAuth client, token, the SQLite store, the digest
sender list — lives in `Main_Menu/Backend/Email_Data/`, which is
gitignored (Rule 7).

**Scope used:** `https://www.googleapis.com/auth/gmail.readonly`.

---

## Steps (yours — Claude cannot do these)

1. <https://console.cloud.google.com> → create a project, or reuse the
   one you use for the Calendar card.
2. **APIs & Services → Library** → enable **Gmail API**.
3. **APIs & Services → OAuth consent screen** → **External** → add your
   own Google address under **Test users**. (Leave it in Testing mode;
   publishing is for apps with other people's users.)
4. **Credentials → Create credentials → OAuth client ID → Desktop app**.
5. Download the JSON and save it as exactly:

   ```
   Main_Menu/Backend/Email_Data/gmail_credentials.json
   ```

   The card is polling for this file — it flips from *"One file away
   from live"* to a **CONNECT GMAIL** button within a minute of it
   appearing. No restart needed.

6. Press **CONNECT GMAIL** on the card (or
   `curl -X POST http://127.0.0.1:8000/api/main_menu/email/connect`).
   A Google tab opens on port **8788**. Approve it.

   Google will warn that the app is unverified — that is expected for a
   Desktop client in Testing mode that you built yourself. **Advanced →
   Go to (your app name)**.

7. The token lands at `Email_Data/gmail_token.json` and is refreshed in
   place from then on. The card syncs immediately and then every
   `EMAIL_SYNC_MINUTES` (default 5).

---

## What the card does once connected

- **Big count** — mail received in the selected window (1H / 4H / 12H / 24H).
- **Sorted by the agent** — every message filed into exactly one of
  *newsletters · finance · jobs · priority · other* by one `claude -p`
  call per batch. Only sender, subject and snippet are sent — never a
  body. Anything the brain answers invalidly is left **uncategorised**
  rather than guessed into a bucket, and the card says how many are
  waiting.
- **Today's Mix** — the same counts as a bar.
- **Newsletter digest** — once a day (`EMAIL_DIGEST_HOUR`, default 08:00)
  the brain summarises new mail from the senders you list, and posts it
  into the AGENT DECK as a note from `EMAIL_DIGEST_AGENT`.

### Turning the digest on

It is off until you choose senders. Edit
`Email_Data/digest_senders.json`:

```json
{
  "senders": ["news@bytebytego.com", "substack.com", "@tldrnewsletter.com"],
  "note": "emails FROM these addresses or domains (lowercase) are summarized in the daily digest"
}
```

Bare domains match any sender at that domain. Run it now with:

```
curl -X POST http://127.0.0.1:8000/api/main_menu/email/digest
```

---

## Settings

All in `settings_for_main_menu.py`, all overridable by env:

| Name | Default | What |
|---|---|---|
| `EMAIL_SYNC_MINUTES` | 5 | how often Gmail is polled |
| `EMAIL_CLAUDE_MODEL` | `sonnet` | the categoriser's model |
| `EMAIL_DIGEST_HOUR` | 8 | local hour the digest runs |
| `EMAIL_DIGEST_AGENT` | `KB_Librarian_Agent` | who the deck note comes from |
| `EMAIL_OWNER_NAME` | `SINGH` | the name on the card footer |
| `EMAIL_OAUTH_PORT` | 8788 | only while the consent tab is open |
| `EMAIL_DEMO` | off | opt-in fixture, labelled DEMO, for reviewing the card before Gmail is connected |

---

## Honest states

The card never shows a number it does not have. What you may see:

| On the card | Means |
|---|---|
| *One file away from live* | step 5 not done — it prints the exact path it wants |
| *Gmail not connected yet* | file present, consent not given — press CONNECT GMAIL |
| *Finish the consent in the Google tab that just opened* | step 6 in progress |
| *The Gmail token stopped working* | refresh failed — press RECONNECT |
| *The Gmail client libraries are not installed* | `pip install -r Main_Menu/Setup/requirements_email.txt` |
| *AI sorting offline* | the `claude` CLI is not on PATH; mail still syncs, it just stays unsorted |

---

## Revoking

<https://myaccount.google.com/permissions> → remove the app. Then delete
`Email_Data/gmail_token.json`. The card drops back to *not connected*;
the Calendar card is unaffected, because the two keep separate tokens on
purpose.
