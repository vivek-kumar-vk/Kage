"""Find ideas already on the board that a new idea's title looks like.

The Enhancement screen's own de-duplication check, as one pure function.
Given the title somebody just typed and every idea already stored, it
returns the existing OPEN ideas worth a second look before saving - so an
idea added twice under slightly different wording gets caught at the door,
not discovered a month later while scrolling.

TIER 0 BY DESIGN (Rule 3). No LLM is called, no file is read or written,
nothing leaves this laptop - this is word-splitting and difflib, nothing
more. It also never blocks: whatever it finds comes back as data, and the
caller decides what to do with it.

HOW IT DECIDES SOMETHING IS SIMILAR - either test alone is enough:

1. A run of WORD_RUN_FOR_WARNING (4) or more consecutive words shared
   between the two titles ("XIRR per holding" vs "True XIRR per holding
   after fees" shares three words and passes; add one more matching word
   and it warns).
2. Whole-title similarity at SIMILARITY_FOR_WARNING (0.75) or higher on
   a difflib SequenceMatcher ratio over the normalised titles - catches
   rewordings no single word-run would ("Payoff race chart" vs "The
   payoff race charted").

Only OPEN ideas are compared against. An idea already marked done does
not warn you off adding a fresh one about the same subject - done means
shipped, and shipping one version of an idea does not retire the subject.

WHAT COMES BACK: a list, best match first, possibly empty. Each entry is
    {"of_id": <the existing idea's id>,
     "of_key": <its ENH key, when the board stores one>,
     "of_title": <its title>,
     "reason": <plain English, why it matched>}

HOW THE SERVER WIRES IT IN (after manage_enhancement_ideas.py's SQLite
rewrite lands - this module exists precisely so that wiring stays a
three-line change):

    from find_similar_ideas import find_similar_ideas

    matches = find_similar_ideas(form.title, all_ideas())
    duplicate_warning = (
        {"of_id": matches[0]["of_id"],
         "of_key": matches[0]["of_key"],
         "of_title": matches[0]["of_title"]}
        if matches else None
    )
    return {"ok": True, "item": saved_item,
            "duplicate_warning": duplicate_warning}

The save happens regardless. The warning rides along in the response;
the page can show it without ever refusing an idea the user meant to
keep. Items are read leniently - legacy JSON rows ({id, title, done})
and SQLite rows ({key, id, title, column/status}) both work, and any
field an item lacks simply comes back as None in the match.
"""

import re
from difflib import SequenceMatcher

# Either threshold alone triggers a match. Tunable here and nowhere else.
WORD_RUN_FOR_WARNING = 4
SIMILARITY_FOR_WARNING = 0.75


def _words(text):
    """Lowercase words of a title, punctuation stripped."""
    return re.findall(r"[a-z0-9]+", str(text).lower())


def _longest_shared_word_run(words_a, words_b):
    """Length of the longest run of consecutive words the two share."""
    best = 0
    for i in range(len(words_a)):
        for j in range(len(words_b)):
            run = 0
            while (i + run < len(words_a) and j + run < len(words_b)
                   and words_a[i + run] == words_b[j + run]):
                run += 1
            best = max(best, run)
    return best


def _is_open(item):
    """True when the item is not marked done, whichever shape it uses."""
    if bool(item.get("done")):
        return False
    where_it_lives = str(
        item.get("status") or item.get("column") or ""
    ).lower()
    return "done" not in where_it_lives


def find_similar_ideas(title, items):
    """Return existing OPEN ideas whose title resembles `title`.

    Pure function - takes the new title and a list of idea dictionaries,
    gives back matches sorted best-first (never raises on odd input,
    never touches a file, never calls a model). Empty list means nothing
    on the open board looked close enough to mention.
    """
    new_words = _words(title)
    if not new_words:
        return []

    matches = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        existing_title = item.get("title") or ""
        if not existing_title.strip():
            continue
        if not _is_open(item):
            continue

        old_words = _words(existing_title)
        shared_run = _longest_shared_word_run(new_words, old_words)
        ratio = SequenceMatcher(
            None, " ".join(new_words), " ".join(old_words)
        ).ratio()

        if shared_run >= WORD_RUN_FOR_WARNING:
            matches.append({
                "of_id": item.get("id"),
                "of_key": item.get("key"),
                "of_title": existing_title,
                "reason": (f"shares {shared_run} consecutive words "
                           f"(warn at {WORD_RUN_FOR_WARNING})"),
                "_score": shared_run,
            })
        elif ratio >= SIMILARITY_FOR_WARNING:
            matches.append({
                "of_id": item.get("id"),
                "of_key": item.get("key"),
                "of_title": existing_title,
                "reason": f"title similarity {ratio:.2f} "
                          f"(warn at {SIMILARITY_FOR_WARNING})",
                "_score": ratio,
            })

    matches.sort(key=lambda m: m["_score"], reverse=True)
    for match in matches:
        del match["_score"]
    return matches
