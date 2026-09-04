"""Honest-zero seed for the Storage screen (PLAN item 2, phase 3).

Two generic, real, sourced notes so a fresh KAGE_DATA_DIR isn't a blank
page the first time the status page's hybrid search box is tried. Guarded
by a marker file through the seam, not by "does the note still exist" -
a user who deletes a seed note has made a decision, and the next boot
must not silently undo it (Rule 8).
"""

import json

from services import seam

_MARKER = "knowledge/_seed_marker.json"

_NOTES = {
    "knowledge/notes/what-is-this-seam.md": (
        "---\n"
        "title: What is the storage seam?\n"
        "---\n\n"
        "Every screen's own persistence funnels through one seam instead of\n"
        "scattering local files: read_doc, write_doc, list_docs, delete_doc,\n"
        "search - addressed by a logical path under KAGE_DATA_DIR, outside the\n"
        "repo. A note lives here once; a hybrid index (keyword + dense) sits on\n"
        "top so it can be found later without remembering the exact path.\n\n"
        "**Source:** Screens/Storage/Backend/README_storage.md\n"
    ),
    "knowledge/notes/how-to-add-a-note.md": (
        "---\n"
        "title: How to add a note\n"
        "---\n\n"
        "PUT /api/storage/doc?path=knowledge/notes/<slug>.md with a JSON body\n"
        "{\"content\": \"...\"}. A note without a source line is rejected once the\n"
        "RAG layer enforces it - every note here should end with a **Source:**\n"
        "line naming where the fact came from.\n\n"
        "**Source:** Screens/Storage/Backend/services/rag.py\n"
    ),
}


def run() -> None:
    try:
        seam.read_doc(_MARKER)
        return  # already seeded - a missing note now was a deliberate delete
    except FileNotFoundError:
        pass

    for path, content in _NOTES.items():
        try:
            seam.read_doc(path)
        except FileNotFoundError:
            seam.write_doc(path, content)

    seam.write_doc(_MARKER, json.dumps({"seeded": True}))
