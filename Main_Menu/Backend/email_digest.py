"""The daily newsletter digest, posted into the Agent Deck chat (D22).

The owner names the senders worth reading in
Email_Data/digest_senders.json - a JSON list of email addresses or whole
domains; everything new from them since the last digest is summarized by
the brain (email_brain.summarize) and POSTed to the deck as a note from
EMAIL_DIGEST_AGENT. HTTP only - the deck owns its chat DB (Rule 5) - and
a deck that is down leaves the digest marked undelivered for the next
cycle, never silently dropped.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import requests

import email_store
import settings_for_main_menu as cfg

MAX_NOTE_CHARS = 2000  # the deck's own message cap (services/agents.py)


def senders_file():
    return cfg.EMAIL_DATA_DIR / "digest_senders.json"


def read_senders():
    """The sender list; a missing file is created with an empty list so
    the card can say 'no senders chosen yet' instead of erroring."""
    path = senders_file()
    if not path.exists():
        cfg.EMAIL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"senders": [],
                 "note": "emails FROM these addresses or domains (lowercase) "
                         "are summarized in the daily digest"},
                indent=2),
            encoding="utf-8",
        )
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [str(s).strip().lower() for s in data.get("senders", []) if str(s).strip()]
    except (ValueError, OSError):
        return []


def _post_to_deck(body):
    url = (cfg.EMAIL_DECK_URL.rstrip()
           + f"/api/agents/agents/{cfg.EMAIL_DIGEST_AGENT}/notes")
    response = requests.post(url, json={"body": body}, timeout=5)
    response.raise_for_status()
    return response.json()


def maybe_run(force=False):
    """Run the digest when it is due. Honest states:
    disabled (no senders chosen) / empty (nothing new) / ran / error."""
    senders = read_senders()
    if not senders:
        return {"state": "disabled",
                "note": "no digest senders chosen yet - edit "
                        "Email_Data/digest_senders.json"}

    now = datetime.now(timezone.utc)
    last = email_store.last_digest_created_at()
    if not force and last:
        try:
            if (now - datetime.fromisoformat(last)) < timedelta(hours=20):
                return {"state": "not_due", "note": "the last digest is under a day old"}
        except ValueError:
            pass

    since_epoch = 0 if not last else datetime.fromisoformat(last).timestamp()
    items = email_store.newsletters_since(since_epoch, senders)
    if not items:
        return {"state": "empty", "note": "no new mail from the chosen senders"}

    import email_brain
    body = email_brain.summarize(items)[:MAX_NOTE_CHARS]

    digest_id = "dig-" + uuid.uuid4().hex[:10]
    span_start = datetime.fromtimestamp(
        since_epoch or (now - timedelta(days=1)), timezone.utc
    ).isoformat()
    email_store.record_digest(digest_id, span_start, now.isoformat(),
                              len(items), body)
    email_store.mark_summarized([r["gmail_id"] for r in items])

    try:
        _post_to_deck(body)
    except requests.RequestException as exc:
        error = f"Agent Deck unreachable: {exc.__class__.__name__}"
        email_store.mark_digest_delivered(digest_id, error=error)
        return {"state": "error", "note": error,
                "note2": "the digest is kept and will be re-posted next cycle"}

    email_store.mark_digest_delivered(digest_id)
    return {"state": "ran", "mails": len(items), "posted_to": cfg.EMAIL_DIGEST_AGENT}
