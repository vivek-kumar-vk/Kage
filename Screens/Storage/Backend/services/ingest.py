"""Ingestion adapter (K-23): Pomodoro logs, Books PDFs and YouTube day
files from kage-data/inbox into spine events and the books library.

scan() runs when called — no watcher. A file is processed exactly once:
the move to _done happens in the same call as its events, and event ids
are derived from the file's sha256 so a crash-and-rescan stays idempotent.
Rejected files keep their bytes under _rejected/<source>/_rejected/.
"""

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_for_storage as cfg  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from Shared_By_All_Screens import spine  # noqa: E402

SOURCES = ("pomodoro", "books", "youtube")
QUOTA_PAGES_PER_DAY = 12
_POMO_AREAS = {"LEARN", "FIN", "CAREER", "BOOKS", "WORK", "OTHER"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _inbox() -> Path:
    override = os.environ.get("KAGE_INBOX_DIR")
    return Path(override) if override else cfg.KAGE_DATA_DIR / "inbox"


def _library_books() -> Path:
    return cfg.KAGE_DATA_DIR / "library" / "books"


INBOX: Path = _inbox()


def _front_matter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("no front matter block")
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise ValueError("front matter block not closed")
    out: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accept(path: Path, source: str, payload: dict, data_as_of: str) -> str:
    """Emit the accepted-file events and move the file into _done."""
    sha = _sha256(path)
    spine.emit("storage", "ingest_received", source,
               {"source": source, "file": path.name}, event_id=sha[:32])
    spine.emit("storage", "fetch_succeeded", f"{source}_inbox",
               {"data_as_of": data_as_of, "items": 1}, event_id=sha[32:64])
    done = _inbox() / "_done" / source
    done.mkdir(parents=True, exist_ok=True)
    os.replace(path, done / path.name)
    return sha[:32]


def _reject(path: Path, source: str, error: str) -> None:
    rejected = _inbox() / "_done" / source / "_rejected"
    rejected.mkdir(parents=True, exist_ok=True)
    os.replace(path, rejected / path.name)
    (rejected / f"{path.name}.error.txt").write_text(error, encoding="utf-8")
    spine.emit("storage", "fetch_failed", f"{source}_inbox", {"error": error})


def ingest_pomodoro(path: Path) -> dict:
    front = _front_matter(path.read_text(encoding="utf-8", errors="replace"))
    required = ("kind", "started", "ended", "minutes", "area", "label")
    missing = [key for key in required if key not in front]
    if missing:
        raise ValueError(f"missing front-matter keys {missing}")
    if front["kind"].strip() != "pomodoro":
        raise ValueError("kind is not pomodoro")
    try:
        started = datetime.fromisoformat(front["started"].strip().strip('"'))
        ended = datetime.fromisoformat(front["ended"].strip().strip('"'))
    except ValueError as exc:
        raise ValueError(f"unparsable timestamp: {exc}") from exc
    if started.tzinfo is None or ended.tzinfo is None:
        raise ValueError("timestamps must carry an offset")
    try:
        minutes = int(front["minutes"].strip())
    except ValueError as exc:
        raise ValueError(f"minutes is not an integer: {exc}") from exc
    area = front["area"].strip()
    if area not in _POMO_AREAS:
        raise ValueError(f"area {area!r} not one of {sorted(_POMO_AREAS)}")
    label = front["label"].strip().strip('"')
    span = round((ended - started).total_seconds() / 60.0)
    if abs(span - minutes) > 1:
        raise ValueError(f"minutes {minutes} disagree with span {span}")
    payload = {"source": "pomodoro", "started": started.isoformat(),
               "ended": ended.isoformat(), "minutes": minutes,
               "area": area, "label": label, "file": path.name}
    payload["event_id"] = _accept(path, "pomodoro", payload,
                                  data_as_of=started.date().isoformat())
    return payload


def ingest_book(path: Path) -> dict:
    if path.suffix.lower() != ".pdf":
        raise ValueError("only .pdf books are ingested")
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        pages = len(pdf.pages)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    meta_path = _library_books() / slug / "meta.json"
    if meta_path.is_file():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
        if existing.get("sha256") == sha:
            raise ValueError("duplicate: same sha256 already ingested")
        raise ValueError(f"duplicate: slug {slug!r} already exists")
    meta = {"title": path.stem, "pages": pages, "added": date.today().isoformat(),
            "sha256": sha, "quota_pages_per_day": QUOTA_PAGES_PER_DAY,
            "cursor_page": 0}
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = meta_path.with_name("meta.json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, meta_path)
    payload = {"source": "books", "slug": slug, "title": path.stem,
               "pages": pages, "sha256": sha, "file": path.name}
    payload["event_id"] = _accept(path, "books", payload,
                                  data_as_of=date.today().isoformat())
    today = date.today().isoformat()
    spine.emit("storage", "number_set", f"books.{slug}.pages",
               {"value": pages, "data_as_of": today})
    spine.emit("storage", "number_set", f"books.{slug}.cursor_page",
               {"value": 0, "data_as_of": today})
    return payload


def _youtube_channels() -> dict:
    path = spine.spine_dir() / "_youtube_channels.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if v in ("deep", "passive")}


def _week_of(day_iso: str) -> set:
    day = date.fromisoformat(day_iso)
    monday = day - timedelta(days=day.weekday())
    return {(monday + timedelta(days=offset)).isoformat() for offset in range(7)}


def ingest_youtube(path: Path) -> dict:
    match = re.fullmatch(r"watch_(\d{4}-\d{2}-\d{2})\.json", path.name)
    if not match:
        raise ValueError("filename must be watch_YYYY-MM-DD.json")
    day = match.group(1)
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("expected a JSON list of videos")
    channels = _youtube_channels()

    def split(items):
        deep = passive = 0
        for entry in items:
            minutes = int(entry.get("minutes") or 0)
            if channels.get(entry.get("channel_id") or "", "passive") == "deep":
                deep += minutes
            else:
                passive += minutes
        return deep, passive

    deep, passive = split(entries)
    payload = {"source": "youtube", "day": day, "deep_minutes": deep,
               "passive_minutes": passive, "videos": len(entries),
               "file": path.name}
    payload["event_id"] = _accept(path, "youtube", payload, data_as_of=day)

    # Week totals are recomputed from every same-week file in _done, so a
    # re-dropped day replaces the old one instead of double-counting.
    week = _week_of(day)
    done_dir = _inbox() / "_done" / "youtube"
    week_entries: list[dict] = []
    for done_path in sorted(done_dir.glob("watch_*.json")):
        done_match = re.fullmatch(r"watch_(\d{4}-\d{2}-\d{2})\.json", done_path.name)
        if done_match and done_match.group(1) in week:
            try:
                week_entries.extend(json.loads(done_path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    deep_total, passive_total = split(week_entries)
    today = date.today().isoformat()
    spine.emit("storage", "number_set", "youtube.week.deep_minutes",
               {"value": deep_total, "data_as_of": today})
    spine.emit("storage", "number_set", "youtube.week.passive_minutes",
               {"value": passive_total, "data_as_of": today})
    return payload


def scan() -> dict:
    received: list[dict] = []
    rejected: list[dict] = []
    inbox = _inbox()
    for source in SOURCES:
        source_dir = inbox / source
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.iterdir()):
            if not path.is_file():
                continue
            try:
                if source == "pomodoro":
                    payload = ingest_pomodoro(path)
                elif source == "books":
                    payload = ingest_book(path)
                elif source == "youtube":
                    payload = ingest_youtube(path)
                else:
                    continue
                received.append({"source": source, "file": path.name,
                                 "event_id": payload.get("event_id")})
            except Exception as exc:  # noqa: BLE001 - one bad file never stops the scan
                error = str(exc)[:300]
                try:
                    _reject(path, source, error)
                except Exception:  # noqa: BLE001
                    pass
                rejected.append({"source": source, "file": path.name,
                                 "error": error})
    return {"state": "ok", "received": received, "rejected": rejected}


router = APIRouter()


@router.post(cfg.API_PREFIX + "/ingest/scan")
def api_scan():
    return scan()


@router.post(cfg.API_PREFIX + "/books/upload")
async def api_books_upload(file: UploadFile):
    target = _inbox() / "books" / Path(file.filename or "upload.pdf").name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(await file.read())
    return scan()


@router.post(cfg.API_PREFIX + "/books/{slug}/read")
def api_book_read(slug: str, body: dict):
    meta_path = _library_books() / slug / "meta.json"
    if not meta_path.is_file():
        raise HTTPException(status_code=404, detail="book not found")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cursor = int(meta.get("cursor_page") or 0)
    pages = int(meta.get("pages") or 0)
    upto = body.get("upto_page")
    if not isinstance(upto, int) or isinstance(upto, bool) or upto < cursor or upto > pages:
        raise HTTPException(
            status_code=422,
            detail=f"upto_page must be between cursor_page ({cursor}) and pages ({pages})")
    meta["cursor_page"] = upto
    tmp = meta_path.with_name("meta.json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, meta_path)
    spine.emit("storage", "number_set", f"books.{slug}.cursor_page",
               {"value": upto, "data_as_of": date.today().isoformat()})
    return {"state": "ok", "slug": slug, "cursor_page": upto}


@router.get(cfg.API_PREFIX + "/books")
def api_books():
    books = []
    root = _library_books()
    if root.is_dir():
        for slug_dir in sorted(root.iterdir()):
            meta_path = slug_dir / "meta.json"
            if not meta_path.is_file():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            books.append({
                "slug": slug_dir.name,
                "title": meta.get("title"),
                "pages": meta.get("pages"),
                "cursor_page": meta.get("cursor_page"),
                "quota_pages_per_day": meta.get("quota_pages_per_day"),
                "added": meta.get("added"),
            })
    return {"books": books}
