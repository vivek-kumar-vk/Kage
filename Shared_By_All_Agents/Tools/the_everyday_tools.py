"""The tools every agent may be granted. Deterministic, no model, no
guessing. Importing this module registers them - nothing else is needed.

Each one returns a dict with has_data, so a caller can always tell the
difference between "nothing found" and "zero".
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent           # Shared_By_All_Agents/Tools
PROJECT_ROOT = HERE.parent.parent                 # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))

from the_tool_registry import a_tool                                          # noqa: E402
from Shared_By_All_Screens.read_and_write_numbers import read_state, write_state  # noqa: E402


@a_tool(
    name="read_a_csv_file",
    what_it_does="Reads a CSV from one screen's own Saved_Records and returns its rows.",
    gives_back="has_data, columns, rows, and how_many.",
)
def read_a_csv_file(project_root, screen, filename, most_rows=500):
    """Confined to one screen's own Saved_Records folder. An agent asking
    for ../../Secrets_Keys, or another screen's records by name, gets a
    refusal rather than a file - the same C8 isolation that applies to
    every screen applies to what an agent may read on its behalf."""
    import csv

    if any(bad in filename for bad in ("/", "\\", "..")):
        return {"has_data": False,
               "note": f"Only a plain filename is allowed, and '{filename}' is not one."}

    where = Path(project_root) / "Screens" / screen / "Saved_Records" / filename
    if not where.exists():
        return {"has_data": False, "note": f"There is no {filename} in {screen}'s records yet."}

    with where.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for number, row in enumerate(reader):
            if number >= most_rows:
                break
            rows.append(row)
        columns = list(reader.fieldnames or [])

    return {"has_data": bool(rows), "columns": columns, "rows": rows,
           "how_many": len(rows), "where_from": f"{screen}/{filename}"}


@a_tool(
    name="read_a_text_file",
    what_it_does="Reads one text file from anywhere in this project - source, guides or settings - except the folders that must stay closed.",
    gives_back="has_data, text, characters, and where_from.",
)
def read_a_text_file(project_root, relative_path, most_characters=60000):
    """Read-only eyes on this repo's own source and notes. An agent that
    answers questions about the codebase needs exactly this and nothing
    more. Secrets_Keys and .git are refused outright, path tricks are
    refused, and anything that resolves outside the project root is
    refused."""
    allowed_kinds = (".py", ".md", ".json", ".yaml", ".yml", ".txt",
                     ".csv", ".html", ".js", ".jsx", ".css", ".bat",
                     ".mmd", ".cfg")
    raw = str(relative_path)
    if any(bad in raw for bad in ("..", "\\", ":")) or raw.startswith(("/", "~")):
        return {"has_data": False,
                "note": (f"Only a plain relative path inside this project "
                         f"is allowed, and '{raw}' is not one.")}

    root = Path(project_root).resolve()
    where = (root / raw).resolve()
    if root not in where.parents:
        return {"has_data": False,
                "note": "That path resolves outside this project and was refused."}
    parts = {piece.lower() for piece in where.parts}
    if "secrets_keys" in parts or ".git" in parts:
        return {"has_data": False,
                "note": "Keys and git internals are never read, by anyone."}
    if where.suffix.lower() not in allowed_kinds:
        return {"has_data": False,
                "note": f"'{where.suffix}' is not a text kind this tool reads."}
    if not where.is_file():
        return {"has_data": False, "note": f"There is no file at {raw}."}

    text = where.read_text(encoding="utf-8", errors="replace")[:most_characters]
    return {"has_data": bool(text), "text": text, "characters": len(text),
            "where_from": raw}


@a_tool(
    name="do_arithmetic",
    what_it_does="Works out a sum, average, percentage or difference from numbers already in hand.",
    gives_back="has_data and answer.",
)
def do_arithmetic(project_root, operation, numbers):
    """Tier 0 made available as a tool, so an agent never has a reason to
    ask a model to add up."""
    try:
        values = [float(n) for n in numbers]
    except (TypeError, ValueError):
        return {"has_data": False, "note": "Some of those were not numbers."}
    if not values:
        return {"has_data": False, "note": "No numbers were given."}

    if operation == "sum":
        answer = sum(values)
    elif operation == "average":
        answer = sum(values) / len(values)
    elif operation == "difference":
        answer = values[0] - sum(values[1:])
    elif operation == "percent_change":
        if len(values) != 2 or values[0] == 0:
            return {"has_data": False,
                   "note": "percent_change needs two numbers and the first cannot be zero."}
        answer = (values[1] - values[0]) / abs(values[0]) * 100
    elif operation == "biggest":
        answer = max(values)
    elif operation == "smallest":
        answer = min(values)
    else:
        return {"has_data": False, "note": (
            f"'{operation}' is not an operation this tool knows. It knows: "
            "sum, average, difference, percent_change, biggest, smallest."
        )}

    return {"has_data": True, "answer": round(answer, 4), "operation": operation}


class _JustTheText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pieces: list[str] = []
        self.skipping = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self.skipping = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer"):
            self.skipping = False

    def handle_data(self, data):
        if not self.skipping and data.strip():
            self.pieces.append(data.strip())


@a_tool(
    name="fetch_a_web_page",
    what_it_does="Fetches a public web page and returns its readable text.",
    gives_back="has_data, text, how_many_characters, and where_from.",
)
def fetch_a_web_page(project_root, address, most_characters=20000):
    """Text only. No JavaScript, no images, no login."""
    if not address.startswith(("http://", "https://")):
        return {"has_data": False, "note": "That is not an http address."}

    request = urllib.request.Request(address, method="GET")
    request.add_header("User-Agent", "INKY/1.0 (personal research tool)")
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as problem:
        return {"has_data": False, "note": f"The page answered HTTP {problem.code}.",
               "where_from": address}
    except Exception as problem:                                    # noqa: BLE001
        return {"has_data": False, "note": f"Could not fetch it: {problem}",
               "where_from": address}

    reader = _JustTheText()
    try:
        reader.feed(raw)
    except Exception:                                                # noqa: BLE001
        pass
    text = " ".join(reader.pieces)[:most_characters]

    if len(text.strip()) < 40:
        return {"has_data": False, "where_from": address, "note": (
            "The page returned almost no readable text. It probably needs "
            "JavaScript, which this tool does not run."
        )}

    return {"has_data": True, "text": text, "how_many_characters": len(text),
           "where_from": address}


@a_tool(
    name="read_the_noticeboard",
    what_it_does="Reads Shared_By_All_Screens/Current_Numbers/all_current_numbers.md.",
    gives_back="has_data and entries, one per key.",
)
def read_the_noticeboard(project_root):
    state = read_state()
    entries = [{"about": k, "value": v} for k, v in state.items() if v is not None]
    return {"has_data": bool(entries), "entries": entries}


@a_tool(
    name="write_to_the_noticeboard",
    what_it_does="Updates one existing key on the noticeboard so other screens and agents can read it.",
    gives_back="has_data and what_was_written.",
)
def write_to_the_noticeboard(project_root, about, value, written_by):
    """The only sanctioned way a fact crosses between agents and screens
    (C8). Deliberately narrower than it sounds: the noticeboard is a
    fixed set of keys a person laid out by hand, and write_state()
    refuses to invent a new one - an agent can update `portfolio_total`,
    it cannot add a line that was never there."""
    try:
        write_state({about: value})
    except KeyError:
        return {"has_data": False, "note": (
            f"'{about}' is not an existing key on the noticeboard. An agent "
            "may update a figure a person already laid out, not invent a "
            "new one - add the key by hand first if it is genuinely needed."
        )}
    return {"has_data": True, "what_was_written": f"{about}: {value}", "by": written_by}


@a_tool(
    name="read_a_json_file",
    what_it_does="Reads a JSON file from the Models screen's fund facts cache.",
    gives_back="has_data and contents.",
)
def read_a_json_file(project_root, filename):
    import json

    if any(bad in filename for bad in ("/", "\\", "..")):
        return {"has_data": False, "note": "Only a plain filename is allowed."}
    where = Path(project_root) / "Screens" / "Finance" / "Saved_Records" / "fund_facts_cache" / filename
    if not where.exists():
        return {"has_data": False, "note": f"There is no {filename} cached."}
    try:
        return {"has_data": True, "contents": json.loads(where.read_text(encoding="utf-8"))}
    except ValueError:
        return {"has_data": False, "note": f"{filename} is not readable JSON."}
