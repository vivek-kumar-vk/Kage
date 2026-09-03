"""The read-only Gmail end of the Email card (D22): OAuth once, quiet
refreshes after.

Setup lives in EMAIL_SETUP.md, but the shape is:

    Email_Data/gmail_credentials.json   the Desktop OAuth client you
                                        download from the Google Cloud
                                        console
    Email_Data/gmail_token.json         written by the one consent visit;
                                        copy it to a hosted box (Termux)
                                        later and it keeps refreshing there

Scope is gmail.readonly - the card can never mark mail read, move or
delete anything. Google libraries are imported lazily so the menu still
runs with them missing; the card then reports honestly that the Gmail
side is not installed instead of pretending to be empty.
"""

import json
from email.utils import getaddresses
from pathlib import Path

import settings_for_main_menu as cfg

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_HEADERS_WANTED = ["From", "Subject", "List-Id"]


class GmailError(RuntimeError):
    """Any Gmail-side failure the card should name honestly."""


def credentials_file() -> Path:
    return cfg.EMAIL_DATA_DIR / "gmail_credentials.json"


def token_file() -> Path:
    return cfg.EMAIL_DATA_DIR / "gmail_token.json"


def libs_missing() -> str | None:
    """The Google client libraries' absence, as a readable reason."""
    try:
        import google_auth_oauthlib  # noqa: F401
        import googleapiclient       # noqa: F401
        return None
    except ImportError as exc:
        return str(exc)


def has_credentials_file() -> bool:
    return credentials_file().exists()


def has_token() -> bool:
    return token_file().exists()


def run_consent():
    """The one blocking browser consent. Call from a thread, never from a
    request handler - it does not answer until Google calls back."""
    if not has_credentials_file():
        raise GmailError(
            f"no OAuth client at {credentials_file()} - see EMAIL_SETUP.md"
        )
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_file()), SCOPES
    )
    creds = flow.run_local_server(port=cfg.EMAIL_OAUTH_PORT, prompt="consent")
    token_file().write_text(creds.to_json(), encoding="utf-8")
    return {"email": None, "granted": True}


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not has_token():
        raise GmailError("not connected - no token yet")

    creds = Credentials.from_authorized_user_file(str(token_file()), SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as exc:
            raise GmailError(
                "token expired and refresh failed - reconnect Gmail"
            ) from exc
        token_file().write_text(creds.to_json(), encoding="utf-8")
    if not creds.valid:
        raise GmailError("stored token is not valid - reconnect Gmail")
    return creds


def _service():
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=_credentials(),
                 cache_discovery=False)


def profile():
    """The account the card footer names. Raises GmailError when down."""
    body = _service().users().getProfile(userId="me").execute()
    return {"email": body.get("emailAddress", ""),
            "threads": body.get("threadsTotal")}


def _split_from(raw):
    """"Vivek Singh <team@robonuggets.com>" -> ("team@...", "Vivek Singh")."""
    if not raw:
        return "", ""
    parts = getaddresses([raw])
    if not parts:
        return raw.strip(), ""
    addr, name = parts[0][1], parts[0][0]
    return (addr or "").strip().lower(), name.strip()


def _iso_ms(ms_epoch):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(int(ms_epoch) / 1000, timezone.utc) \
                   .replace(microsecond=0).isoformat()


def fetch_since(epoch_seconds, max_messages=200):
    """Mail newer than the epoch, as plain rows for the store. Metadata
    only - sender, subject, snippet; bodies are never pulled."""
    svc = _service()
    query = f"after:{int(epoch_seconds) - 600}"  # 10 min overlap, deduped by id

    ids, page_token = [], None
    while len(ids) < max_messages:
        batch = svc.users().messages().list(
            userId="me", q=query, maxResults=100, pageToken=page_token
        ).execute()
        ids += [m["id"] for m in batch.get("messages", [])]
        page_token = batch.get("nextPageToken")
        if not page_token:
            break

    rows = []
    for mid in ids[:max_messages]:
        msg = svc.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=_HEADERS_WANTED,
        ).execute()
        headers = {h["name"].lower(): h["value"]
                   for h in msg.get("payload", {}).get("headers", [])}
        sender_email, sender_name = _split_from(headers.get("from", ""))
        rows.append({
            "gmail_id": mid,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "subject": headers.get("subject", "(no subject)"),
            "snippet": msg.get("snippet", ""),
            "list_id": headers.get("list-id", ""),
            "received_at": _iso_ms(msg.get("internalDate", "0")),
        })
    return rows
