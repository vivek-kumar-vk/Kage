"""Google Calendar for the Calendar card (D23): read the real calendar,
and write the events the agent proposes and the owner approved.

Two files, both in Calendar_Data/ (gitignored):

    Calendar_Data/calendar_credentials.json   the Desktop OAuth client
                                              you download from Google
    Calendar_Data/calendar_token.json         written by the one consent
                                              visit; refreshed in place

One scope, `calendar.events`, because the card does exactly two things
with Google: list events, and create/update the ones the owner approved.
It is deliberately not `calendar` (which would also let it delete whole
calendars) and deliberately not `.readonly` (the whole point is that an
approved event reaches the phone).

Same shape as email_gmail.py so the two cards stay one pattern. Every
failure is raised as CalendarError with a sentence a human can act on -
the card prints it rather than showing an empty month (Rule 8).
"""

from pathlib import Path

import settings_for_main_menu as cfg

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarError(RuntimeError):
    """Anything that stops us reaching Google, said in one sentence."""


def credentials_file() -> Path:
    return cfg.CALENDAR_DATA_DIR / "calendar_credentials.json"


def token_file() -> Path:
    return cfg.CALENDAR_DATA_DIR / "calendar_token.json"


def libs_missing() -> str | None:
    """The google client libraries are an optional install; say so by
    name instead of throwing ImportError out of an endpoint."""
    try:
        import google.oauth2.credentials  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError as exc:
        return f"google client libraries not installed ({exc.name})"
    return None


def has_credentials_file() -> bool:
    return credentials_file().exists()


def has_token() -> bool:
    return token_file().exists()


def run_consent():
    """The one-time browser consent. Blocks until Google redirects back
    to the loopback port, then writes the token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not has_credentials_file():
        raise CalendarError(
            f"no OAuth client at {credentials_file()} - see CALENDAR_SETUP.md"
        )
    cfg.CALENDAR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_file()), SCOPES
    )
    creds = flow.run_local_server(port=cfg.CALENDAR_OAUTH_PORT, open_browser=True)
    token_file().write_text(creds.to_json(), encoding="utf-8")
    return True


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not has_token():
        raise CalendarError("not connected - no token yet")

    creds = Credentials.from_authorized_user_file(str(token_file()), SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            raise CalendarError(
                "token expired and refresh failed - reconnect Google Calendar"
            )
        token_file().write_text(creds.to_json(), encoding="utf-8")
    if not creds.valid:
        raise CalendarError("stored token is not valid - reconnect Google Calendar")
    return creds


def _service():
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=_credentials(),
                 cache_discovery=False)


# ---------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------
def list_events(time_min_iso, time_max_iso, max_results=2500):
    """Every event in the window, single events (recurrences expanded),
    ordered by start. Returns the raw Google items - the store decides
    what it keeps."""
    service = _service()
    items, page_token = [], None
    while True:
        response = service.events().list(
            calendarId=cfg.CALENDAR_ID,
            timeMin=time_min_iso,
            timeMax=time_max_iso,
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
            pageToken=page_token,
        ).execute()
        items.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token or len(items) >= max_results:
            break
    return items


# ---------------------------------------------------------------------
# WRITE - only ever called for a proposal the owner approved
# ---------------------------------------------------------------------
def create_event(summary, start_iso, end_iso, description="", timezone=None,
                 reminder_minutes=10):
    """Create one event. `source` marks it as ours so the mirror can tell
    agent-written events from ones the owner made by hand, and so a
    mistake is findable and deletable later.

    Reminders are left on: an event the owner approved is meant to reach
    the phone - that is the entire reason this write path exists.
    """
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
        "extendedProperties": {"private": {"kage_agent": "1"}},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": int(reminder_minutes)}],
        },
    }
    if timezone:
        body["start"]["timeZone"] = timezone
        body["end"]["timeZone"] = timezone
    created = _service().events().insert(
        calendarId=cfg.CALENDAR_ID, body=body
    ).execute()
    return created.get("id")


def delete_event(google_event_id):
    """Undo for a written proposal. Google returns 410 for an event that
    is already gone; that is success from the card's point of view."""
    from googleapiclient.errors import HttpError

    try:
        _service().events().delete(
            calendarId=cfg.CALENDAR_ID, eventId=google_event_id
        ).execute()
    except HttpError as exc:
        if exc.resp.status in (404, 410):
            return True
        raise
    return True
