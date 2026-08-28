"""Recall cards over real material - the SM-2 flavour of the Recall tab.

WHAT THIS FILE OWNS
    `Saved_Records/recall_cards.json` - one card per thing worth being
    able to explain out loud: the elevator answer, the likely question,
    the trap question, a real example and where it lands on the resume.

THE SEED CARD
    One example card ships so a fresh install has something to look at
    (Splunk's parsing pipeline). It carries no personal data - replace
    or delete it. Everything after that first card is added by hand.

WHY SIMPLIFIED SM-2, EXACTLY AND ONLY
    The intervals are the whole point of a spaced-repetition file, so
    review_card() implements the reduced SM-2 below literally - no
    extra branches, no cleverness - so any interval on any card can be
    re-derived by reading one function.

RUN IT
    python Screens\\Learning\\Calculations\\Recall_Tab\\manage_recall_cards.py
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IST = timezone(timedelta(hours=5, minutes=30), "IST")

SAVED_RECORDS = SCREEN / "Saved_Records"
CARDS_FILE = SAVED_RECORDS / "recall_cards.json"
SEED_MARKER = SAVED_RECORDS / "recall_cards_starter_seed.json"

QUALITIES = (0, 3, 4, 5)        # Again, Hard, Good, Easy
EASE_FLOOR = 1.3
RESUME_STREAK = 2               # Good/Easy across two separate reviews

# Fields a caller may edit through update_card(). The scheduling state
# (ease/interval/reps/due/last_reviewed/clean_streak) changes only
# through review_card(), so it can always be trusted.
CONTENT_FIELDS = ("topic", "track", "elevator", "likely_q", "trap_q",
                  "example", "resume_link")


class NoSuchCard(Exception):
    """Raised for a card id that is not in the file - most likely
    already deleted, never silently ignored."""


class DuplicateCard(Exception):
    """Raised by add_card() when a card with exactly the same content
    is already in the file (Phase-1 CS-2): a retried save must never
    become a second card. `.existing` carries the stored card.

    Exact match only, over every content field with surrounding
    whitespace stripped - scheduling state plays no part, since a fresh
    card has none of its own yet."""
    def __init__(self, existing: dict):
        super().__init__(
            "identical recall card already stored "
            f"(id {existing.get('id')})")
        self.existing = existing


def _today() -> date:
    return datetime.now(IST).date()


# A single example card, so a fresh install has one to look at. Replace
# or delete it - it carries no personal data.
SEED_CARD: dict = {
    "topic": "Parsing \u2192 indexing pipeline",
    "track": "A",
    "elevator": (
        "Splunk moves data through four pipeline segments \u2014 input, "
        "parsing, indexing, search. Input tags the source and reads bytes; "
        "parsing breaks the stream into events, does line-breaking, "
        "timestamp extraction and sourcetyping; indexing writes events to "
        "buckets on disk; search reads them back. A forwarder usually "
        "handles input+parsing, an indexer handles indexing+search."
    ),
    "likely_q": (
        "Q: Where does timestamp extraction happen?\n"
        "A: In the parsing phase, on whatever component parses \u2014 typically "
        "the indexer, or a heavy forwarder if you parse at the edge. "
        "Universal forwarders don't parse, so they don't extract timestamps."
    ),
    "trap_q": (
        "Q: Does a universal forwarder parse events?\n"
        "A: No \u2014 that's the trap. A UF forwards unparsed streams; parsing "
        "happens downstream on an indexer or heavy forwarder. Only a heavy "
        "forwarder parses at the edge."
    ),
    "example": (
        "A common real-world case: timestamp-parsing and sourcetype issues on "
        "a log-source onboarding trace back to this - fixing them means "
        "correcting props/transforms at the parsing tier, not the input."
    ),
    "resume_link": (
        "Ties to 'end-to-end log source onboarding' and "
        "'timestamp/field-extraction troubleshooting' skills."
    ),
}

def read_cards() -> list[dict]:
    """Every card, due order is the caller's business. Empty when no
    cards exist yet - not an error, the honest starting state."""
    if not CARDS_FILE.exists():
        return []
    return json.loads(CARDS_FILE.read_text(encoding="utf-8")).get("cards", [])


def _write_cards(cards: list[dict]) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    CARDS_FILE.write_text(json.dumps({"cards": cards}, indent=2),
                          encoding="utf-8")


def seed_cards_if_empty() -> bool:
    """Write the one real card on first run. Returns True when written,
    False when cards already exist - a re-run must never overwrite
    scheduling state earned by real reviews.

    Seeding happens ONCE, ever: once the marker file exists, a deleted
    or emptied card file stays that way. Resurrecting the starter card
    after the person deleted it would turn their deletion into a lie
    (Phase-1 CS-4). The seeded card carries `starter: true` so the page
    can label it 'starter data - yours to delete'."""
    if CARDS_FILE.exists():
        return False
    if SEED_MARKER.exists():
        return False
    card = {
        "id": uuid.uuid4().hex[:12],
        **SEED_CARD,
        "starter": True,
        "ease": 2.5,
        "interval": 0,
        "reps": 0,
        "due": _today().isoformat(),
        "last_reviewed": None,
        "clean_streak": 0,
    }
    _write_cards([card])
    SEED_MARKER.write_text(json.dumps({
        "seeded_at": datetime.now(IST).isoformat(timespec="seconds"),
        "what": "the one starter recall card",
        "note": ("seeding is one-time; this marker is why deleting "
                 "cards stays deleted after a restart"),
    }, indent=2), encoding="utf-8")
    return True


def add_card(topic: str, track: str = "A", elevator: str = "",
             likely_q: str = "", trap_q: str = "", example: str = "",
             resume_link: str = "") -> dict:
    """Add one card. A card without a topic would be an unanswerable
    question, so that is refused. A new card is due immediately.

    An EXACT repeat of a card already stored raises DuplicateCard
    carrying that card (Phase-1 CS-2): the add button double-pressed,
    or the request retried, must never file the same card twice."""
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("a recall card needs a topic")
    track = (track or "A").strip().upper()
    if track not in ("A", "B"):
        raise ValueError(f"track must be 'A' or 'B', got {track!r}")

    content = {
        "topic": topic,
        "track": track,
        "elevator": (elevator or "").strip(),
        "likely_q": (likely_q or "").strip(),
        "trap_q": (trap_q or "").strip(),
        "example": (example or "").strip(),
        "resume_link": (resume_link or "").strip(),
    }

    cards = read_cards()
    for c in cards:
        if all((c.get(field) or "").strip() == value
               for field, value in content.items()):
            raise DuplicateCard(c)
    card = {
        "id": uuid.uuid4().hex[:12],
        **content,
        "ease": 2.5,
        "interval": 0,
        "reps": 0,
        "due": _today().isoformat(),
        "last_reviewed": None,
        "clean_streak": 0,
    }
    cards.append(card)
    _write_cards(cards)
    return card


def _find_card(cards: list[dict], card_id: str) -> dict:
    for card in cards:
        if card["id"] == card_id:
            return card
    raise NoSuchCard(f"no recall card with id '{card_id}'")


def update_card(card_id: str, **fields) -> dict:
    """Edit the content fields of one card. Scheduling state is not
    editable here on purpose - it belongs to review_card() alone."""
    unknown = set(fields) - set(CONTENT_FIELDS)
    if unknown:
        raise ValueError(
            f"cannot edit {sorted(unknown)} - only {CONTENT_FIELDS}")
    cards = read_cards()
    card = _find_card(cards, card_id)
    for key, value in fields.items():
        card[key] = value
    _write_cards(cards)
    return card


def delete_card(card_id: str) -> None:
    cards = read_cards()
    kept = [c for c in cards if c["id"] != card_id]
    if len(kept) == len(cards):
        raise NoSuchCard(f"no recall card with id '{card_id}'")
    _write_cards(kept)


def due_cards(today=None) -> list[dict]:
    """Cards whose due date has arrived (or passed). ISO dates compare
    correctly as strings, so no parsing needed."""
    today = (today or _today()).isoformat() \
        if not isinstance(today, str) else today
    return [c for c in read_cards() if c["due"] <= today]


def review_card(card_id: str, quality: int, today=None) -> dict:
    """One review, simplified SM-2 exactly:

    quality < 3 (Again): reps reset to 0, interval back to 1 day,
                         clean streak broken.
    quality >= 3:        interval 1 on the first pass, 3 on the second,
                         then previous interval * ease; ease moves by
                         the SM-2 formula but never below 1.3; Good or
                         Easy extends the clean streak, Hard breaks it.
    """
    if quality not in QUALITIES:
        raise ValueError(
            f"quality must be one of {QUALITIES} "
            f"(0=Again, 3=Hard, 4=Good, 5=Easy), got {quality!r}")
    today = today or _today()
    if isinstance(today, str):
        today = date.fromisoformat(today)

    cards = read_cards()
    card = _find_card(cards, card_id)

    if quality < 3:
        card["reps"] = 0
        card["interval"] = 1
        card["clean_streak"] = 0
    else:
        if card["reps"] == 0:
            card["interval"] = 1
        elif card["reps"] == 1:
            card["interval"] = 3
        else:
            card["interval"] = round(card["interval"] * card["ease"])
        card["reps"] += 1
        n = 5 - quality
        card["ease"] = max(EASE_FLOOR,
                           card["ease"] + (0.1 - n * (0.08 + n * 0.02)))
        card["clean_streak"] = card["clean_streak"] + 1 \
            if quality >= 4 else 0

    card["due"] = (today + timedelta(days=card["interval"])).isoformat()
    card["last_reviewed"] = today.isoformat()
    _write_cards(cards)
    return card


def resume_ready(card: dict) -> bool:
    """The resume rule: this card can back a bullet once it has been
    answered well twice across two separate reviews."""
    return card.get("clean_streak", 0) >= RESUME_STREAK


def main() -> None:
    seeded = seed_cards_if_empty()
    if seeded:
        print("  Seeded recall_cards.json with the one real card.")
    cards = read_cards()
    due = due_cards()
    print("RECALL CARDS")
    print("=" * 50)
    print(f"  {len(cards)} card(s), {len(due)} due today")
    for card in cards:
        flag = " [resume-ready]" if resume_ready(card) else ""
        print(f"  Track {card['track']}  {card['topic']}{flag}")


if __name__ == "__main__":
    main()

