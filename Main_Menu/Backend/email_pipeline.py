"""The Email card's pipeline (D22): one background loop -
sync Gmail -> categorize with the brain -> maybe digest - and the
summary the card renders.

Honesty rules this module lives by (CLAUDE.md Rule 8):
  - every state the card can be in is named (not connected, needs the
    OAuth client file, token expired, brain offline, syncing) and the
    card repeats it verbatim;
  - nothing is ever invented to fill the count;
  - EMAIL_DEMO=1 swaps in a labelled simulated summary (D12.2 pattern)
    purely for reviewing the design before Gmail is connected.
"""

import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

import email_brain
import email_digest
import email_gmail
import email_store
import settings_for_main_menu as cfg

CATEGORY_META = [
    {"key": "newsletters", "label": "NEWSLETTERS"},
    {"key": "finance", "label": "FINANCE"},
    {"key": "jobs", "label": "JOBS & APPLICATIONS"},
    {"key": "priority", "label": "PRIORITY PICKS"},
]

FIRST_SYNC_DAYS = 7          # what a first successful sync reaches back for
MAX_CATEGORISE_ROUNDS = 6    # batches per cycle; the rest wait for the next

_lock = threading.Lock()     # one cycle at a time
_lifecycle = threading.Lock()
_started = False
_activity = {"syncing": False, "connecting": False}


def _utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------
def start_once():
    global _started
    with _lifecycle:
        if _started:
            return
        _started = True
    threading.Thread(target=_loop, daemon=True, name="email-pipeline").start()


def _loop():
    try:
        sync_cycle()
    except Exception:
        pass
    while True:
        time.sleep(cfg.EMAIL_SYNC_MINUTES * 60)
        try:
            sync_cycle()
        except Exception:
            email_store.set_state("last_error", traceback.format_exc(limit=3))


# ---------------------------------------------------------------------
# one cycle
# ---------------------------------------------------------------------
def sync_cycle():
    with _lock:
        _activity["syncing"] = True
        try:
            return _sync_cycle_inner()
        finally:
            _activity["syncing"] = False


def _sync_cycle_inner():
    email_store.init_db()
    email_store.set_state("last_sync_at", _utcnow())

    missing = email_gmail.libs_missing()
    if missing:
        return _fail("needs_install", f"Google client libraries missing: {missing}")
    if not email_gmail.has_credentials_file():
        return _fail("needs_credentials",
                     f"no OAuth client at {email_gmail.credentials_file()} - "
                     "see EMAIL_SETUP.md")
    if not email_gmail.has_token():
        return _fail("not_connected", "Gmail connected awaits your one-time consent")

    last_ok = email_store.get_state("last_sync_ok_epoch")
    if last_ok:
        since = float(last_ok)
    else:
        since = (datetime.now(timezone.utc)
                 - timedelta(days=FIRST_SYNC_DAYS)).timestamp()

    try:
        svc_profile = email_gmail.profile()
        rows = email_gmail.fetch_since(since)
    except email_gmail.GmailError as exc:
        return _fail("auth_error", str(exc))
    except Exception as exc:
        return _fail("error", f"{exc.__class__.__name__}: {exc}")

    new_count = email_store.upsert_messages(rows)
    email_store.set_state("account", svc_profile.get("email", ""))

    categorised = _categorise_pending()
    digest = email_digest.maybe_run()

    email_store.set_state("last_sync_ok_epoch", str(time.time()))
    email_store.set_state("last_sync_ok_at", _utcnow())
    email_store.set_state("connection", "connected")
    email_store.set_state("last_error", "")
    return {"state": "ok", "fetched": len(rows), "new": new_count,
            "categorised": categorised, "digest": digest}


def _fail(state, detail):
    email_store.set_state("connection", state)
    email_store.set_state("last_error", detail)
    return {"state": state, "detail": detail}


def _categorise_pending():
    """Batch uncategorized mail through the brain until the batch comes
    back empty-invalid (brain broken) or nothing is left. Rounds are
    capped per cycle so a big first sync cannot run away with the quota."""
    total = 0
    if email_brain.brain_state()["state"] != "ok":
        email_store.set_state("brain_error",
                              email_brain.brain_state()["detail"])
        return 0
    for _ in range(MAX_CATEGORISE_ROUNDS):
        batch = email_store.uncategorized(limit=30)
        if not batch:
            break
        items = [dict(r) for r in batch]
        try:
            mapping = email_brain.categorize(items)
        except Exception as exc:
            email_store.set_state("brain_error",
                                  f"{exc.__class__.__name__}: {exc}")
            return total
        if not mapping:
            break
        email_store.apply_categories(mapping)
        total += len(mapping)
        if len(mapping) < len(items):
            break
    email_store.set_state("brain_error", "")
    return total


# ---------------------------------------------------------------------
# the consent thread
# ---------------------------------------------------------------------
def connect_start():
    if email_gmail.has_token():
        return {"state": "already_connected"}
    if not email_gmail.has_credentials_file():
        return {"state": "needs_credentials",
                "path": str(email_gmail.credentials_file()),
                "note": "download the Desktop OAuth client from the Google "
                        "Cloud console (EMAIL_SETUP.md) and save it there"}
    with _lifecycle:
        if _activity["connecting"]:
            return {"state": "connecting"}
        _activity["connecting"] = True

    def _consent():
        try:
            email_gmail.run_consent()
            email_store.init_db()
            sync_cycle()
        except Exception as exc:
            email_store.init_db()
            _fail("auth_error", f"consent failed: {exc}")
        finally:
            _activity["connecting"] = False

    threading.Thread(target=_consent, daemon=True).start()
    email_store.init_db()
    email_store.set_state("connection", "connecting")
    return {"state": "consent_started",
            "note": "a Google consent tab just opened in your browser"}


# ---------------------------------------------------------------------
# what the card renders
# ---------------------------------------------------------------------
def is_syncing():
    return _activity["syncing"]


def summary(hours=24):
    hours = max(1, min(int(hours), 72))
    email_store.init_db()

    if cfg.EMAIL_DEMO:
        return _demo_summary(hours)

    state = email_store.all_state()
    connection = state.get("connection", "not_connected")

    # First serve the states that have no mailbox data behind them yet.
    if connection in ("not_connected", "needs_credentials", "needs_install",
                      "auth_error", "connecting", "error", ""):
        payload = {
            "state": connection if connection != "" else "not_connected",
            "problem": state.get("last_error", ""),
            "hours": hours,
            "credentials_path": str(email_gmail.credentials_file()),
            "setup_doc": "Main_Menu/Backend/EMAIL_SETUP.md",
            "brain": email_brain.brain_state(),
            "syncing": _activity["syncing"],
            "connecting": _activity["connecting"],
        }
        if connection == "needs_credentials":
            payload["state"] = "needs_credentials"
        return payload

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)) \
        .replace(microsecond=0).isoformat()

    conn = email_store.connect()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE received_at >= ?",
            (cutoff,),
        ).fetchone()["c"]
        counts = {r["category"]: r["c"] for r in conn.execute(
            "SELECT category, COUNT(*) AS c FROM messages "
            "WHERE received_at >= ? GROUP BY category", (cutoff,),
        )}
        uncategorised = counts.get(None, 0)

        categories = []
        for meta in CATEGORY_META:
            latest = conn.execute(
                """SELECT subject, reason, received_at FROM messages
                   WHERE category = ? AND received_at >= ?
                   ORDER BY received_at DESC LIMIT 1""",
                (meta["key"], cutoff),
            ).fetchone()
            categories.append({
                **meta,
                "count": counts.get(meta["key"], 0),
                "latest": dict(latest) if latest else None,
            })
    finally:
        conn.close()

    other_count = counts.get("other", 0)
    mix = {c["key"]: c["count"] for c in categories}
    mix["other"] = other_count

    digest_note = ""
    last_digest = email_store.last_digest_created_at()
    if not email_digest.read_senders():
        digest_note = "digest: no senders chosen yet"
    elif last_digest:
        digest_note = f"last digest {last_digest[:16].replace('T', ' ')}"

    return {
        "state": "ok",
        "hours": hours,
        "total": total,
        "account": state.get("account", ""),
        "owner": cfg.EMAIL_OWNER_NAME,
        "synced_at": state.get("last_sync_ok_at", ""),
        "syncing": _activity["syncing"],
        "categories": categories,
        "other": other_count,
        "uncategorised": uncategorised,
        "brain": email_brain.brain_state()
        | {"error": state.get("brain_error", "")},
        "digest_note": digest_note,
    }


# ---------------------------------------------------------------------
# the opt-in, clearly-labelled simulated card (D12.2 pattern)
# ---------------------------------------------------------------------
def _demo_summary(hours):
    def _ago(minutes):
        return (datetime.now(timezone.utc)
                - timedelta(minutes=minutes)).replace(microsecond=0).isoformat()

    return {
        "state": "ok",
        "demo": True,
        "hours": hours,
        "total": 47,
        "account": "team@robonuggets.com",
        "owner": cfg.EMAIL_OWNER_NAME,
        "synced_at": _ago(4),
        "syncing": False,
        "categories": [
            {"key": "newsletters", "label": "NEWSLETTERS", "count": 18,
             "latest": {"subject": "The Monday Loop - shipping small agents",
                        "reason": "weekly engineering digest",
                        "received_at": _ago(52)}},
            {"key": "finance", "label": "FINANCE", "count": 9,
             "latest": {"subject": "Your card statement is ready",
                        "reason": "monthly card statement",
                        "received_at": _ago(130)}},
            {"key": "jobs", "label": "JOBS & APPLICATIONS", "count": 6,
             "latest": {"subject": "Forward-deploy engineer - follow-up",
                        "reason": "recruiter follow-up",
                        "received_at": _ago(35)}},
            {"key": "priority", "label": "PRIORITY PICKS", "count": 4,
             "latest": {"subject": "Interview slot confirmation needed",
                        "reason": "reply expected today",
                        "received_at": _ago(20)}},
        ],
        "other": 10,
        "uncategorised": 0,
        "brain": email_brain.brain_state() | {"error": ""},
        "digest_note": "digest: simulated for review",
        "problem": "",
    }
