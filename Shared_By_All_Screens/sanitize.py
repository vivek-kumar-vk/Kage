"""Sanitisation (K-10): replace personal identifiers with reversible
tokens before text leaves the box, and restore them in replies.

One mapping per ask; mapping files under spine/sanitize/ are the only way
to restore a stored reply and are never deleted here. Amounts, dates and
ISO timestamps are deliberately not matched (Rule 22: never guess).
"""

import json
import os
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Shared_By_All_Screens import spine  # noqa: E402

KINDS = ("PAN", "AADHAAR", "ACCT", "FOLIO", "EMAIL", "PHONE", "NAME")
PATTERNS = {
    "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "AADHAAR": r"\b[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}\b",
    "ACCT": r"\b[0-9]{9,18}\b",
    "FOLIO": r"\b[0-9]{6,12}\s?/\s?[0-9]{1,3}\b",
    "EMAIL": r"\b[\w.+-]+@[\w-]+\.[\w.]+\b",
    "PHONE": r"\b(?:\+91[ -]?)?[6-9][0-9]{9}\b",
}
# Working match order. Deviation from the literal KINDS order, proven by the
# ticket's own EV-SAN-01 fixture: a bare 10-digit number must come out as
# [[PHONE_1]], so PHONE has to run before ACCT (the patterns are fixed, not
# editable). PHONE only claims exactly-10-digit numbers starting 6-9.
_PATTERN_ORDER = ("PAN", "AADHAAR", "PHONE", "ACCT", "FOLIO", "EMAIL")
NAMES_PATH: Path = spine.spine_dir() / "_names.json"
MAPPING_DIR: Path = spine.spine_dir() / "sanitize"

_TOKEN = re.compile(r"\[\[[A-Za-z]+_[0-9]+\]\]")


def _names_path() -> Path:
    return spine.spine_dir() / "_names.json"


def _mapping_dir() -> Path:
    return spine.spine_dir() / "sanitize"


def _load_names() -> list:
    path = _names_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return []
    return [name for name in data if isinstance(name, str) and name]


def load_mapping(mapping_id: str) -> dict:
    path = _mapping_dir() / f"{mapping_id}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def store_mapping(mapping_id: str, mapping: dict) -> None:
    directory = _mapping_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{mapping_id}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, ensure_ascii=False, separators=(",", ":"))
        fh.flush()
        os.fsync(fh.fileno())


def sanitize(text: str, *, mapping_id: str | None = None,
             names: list[str] | None = None) -> tuple[str, str]:
    """Replace identifiers with [[KIND_n]] tokens. Returns (text, mapping_id)
    and stores the mapping (fsync) before returning. A second call with the
    same mapping_id extends it: same original, same token."""
    if mapping_id is None:
        mapping_id = uuid.uuid4().hex
    mapping = load_mapping(mapping_id)
    reverse = {original: token for token, original in mapping.items()}
    counters: dict[str, int] = {}
    for token in mapping:
        kind, number = token[2:-2].rsplit("_", 1)
        counters[kind] = max(counters.get(kind, 0), int(number))

    def token_for(kind: str, original: str) -> str:
        if original in reverse:
            return reverse[original]
        counters[kind] = counters.get(kind, 0) + 1
        token = f"[[{kind}_{counters[kind]}]]"
        mapping[token] = original
        reverse[original] = token
        return token

    out = text
    for kind in _PATTERN_ORDER:
        pieces: list[str] = []
        last = 0
        for match in re.finditer(PATTERNS[kind], out):
            pieces.append(out[last:match.start()])
            pieces.append(token_for(kind, match.group(0)))
            last = match.end()
        pieces.append(out[last:])
        out = "".join(pieces)

    name_list = list(names) if names is not None else _load_names()
    for name in sorted({n for n in name_list if n}, key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
        pieces = []
        last = 0
        for match in pattern.finditer(out):
            pieces.append(out[last:match.start()])
            token = None
            for existing, original in mapping.items():
                if existing.startswith("[[NAME_") and original.lower() == match.group(0).lower():
                    token = existing
                    break
            pieces.append(token or token_for("NAME", match.group(0)))
            last = match.end()
        pieces.append(out[last:])
        out = "".join(pieces)

    store_mapping(mapping_id, mapping)
    return out, mapping_id


def desanitize(text: str, mapping_id: str) -> tuple[str, list[str]]:
    """Restore every token the mapping knows. Unknown [[...]] tokens stay
    literal and are returned in order of appearance — never guessed."""
    mapping = load_mapping(mapping_id)
    unresolved: list[str] = []

    def replace(match: re.Match) -> str:
        token = match.group(0)
        if token in mapping:
            return mapping[token]
        if token not in unresolved:
            unresolved.append(token)
        return token

    return _TOKEN.sub(replace, text), unresolved
