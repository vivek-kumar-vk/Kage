"""The Email card's brain (D22): short-lived `claude -p` runs - one batch
in, JSON/text out, session over.

The owner chose the Claude Code CLI as the categorizer: it is already
logged in on this machine under his Pro plan, and every task is one
print-mode invocation that ends when it answers - no daemon, no key in
.env. The binary is resolved on PATH at call time (shutil.which), so a
box without it reports "brain offline" honestly instead of erroring the
whole card. Only sender, subject and snippet are sent - the same data
the card itself shows.
"""

import json
import shutil
import subprocess

import settings_for_main_menu as cfg

CATEGORIES = ("newsletters", "finance", "jobs", "priority", "other")

CATEGORY_RULES = """- newsletters: subscriptions and publications he follows. He reads
  these to LEARN, not as spam: engineering blogs, AI/DevOps digests,
  tutorials, course and newsletter issues.
- finance: banks, brokers, cards, payments, bills, tax, markets,
  statements, anything money-related.
- jobs: recruiters, job applications, application updates, interview
  invites, hiring - even when urgent they stay here, not in priority.
- priority: needs HIM to act today and fits nothing above: deadlines,
  security alerts, appointments, accounts, replies he is waiting on.
- other: everything else."""


def claude_path():
    return shutil.which("claude")


def brain_state():
    path = claude_path()
    if not path:
        return {"state": "missing", "model": cfg.EMAIL_BRAIN_MODEL,
                "detail": "the claude CLI is not on PATH"}
    return {"state": "ok", "model": cfg.EMAIL_BRAIN_MODEL, "detail": ""}


def _run(prompt):
    path = claude_path()
    if not path:
        raise RuntimeError("the claude CLI is not on PATH")
    result = subprocess.run(
        [path, "-p", "--model", cfg.EMAIL_BRAIN_MODEL],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=cfg.EMAIL_CLAUDE_TIMEOUT,
    )
    text = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or not text:
        detail = result.stderr.decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"claude -p failed: {detail or 'empty answer'}")
    return text


def _extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the brain's answer")
    return json.loads(text[start:end + 1])


def categorize(items):
    """items: rows with gmail_id / sender_email / sender_name / subject /
    snippet. Returns gmail_id -> (category, reason); anything the brain
    answers invalidly is left out, so it stays honestly uncategorized."""
    if not items:
        return {}
    listing = "\n".join(
        f'[{r["gmail_id"]}] from {(r["sender_name"] or r["sender_email"] or "?")}'
        f' <{r["sender_email"] or "?"}> - {r["subject"] or "(no subject)"}'
        f' - {(r["snippet"] or "")[:160]}'
        for r in items
    )
    prompt = f"""You are an email triage agent. File every email into EXACTLY ONE category:

{CATEGORY_RULES}

Answer with ONLY a JSON object, no prose before or after:
{{"results":[{{"id":"<the id in brackets>","category":"<category>","reason":"<why, max 6 words>"}}]}}

Emails:
{listing}"""
    data = _extract_json(_run(prompt))
    out = {}
    for row in data.get("results", []):
        gmail_id, category = row.get("id"), str(row.get("category", "")).lower()
        if gmail_id in {r["gmail_id"] for r in items} and category in CATEGORIES:
            out[gmail_id] = (category, str(row.get("reason", ""))[:120])
    return out


def summarize(items):
    """Newsletter digest text for the Agent Deck. Honest input: the card
    stores metadata and snippets, never bodies - the summary says only
    what those snippets support."""
    listing = "\n".join(
        f'- [{(r["sender_name"] or r["sender_email"])}] {r["subject"]}'
        f' - {(r["snippet"] or "")[:200]}'
        for r in items
    )
    prompt = f"""These are newsletter issues a reader subscribed to on purpose -
he reads them to LEARN. Write him a digest in plain text, no markdown
headers, under 1600 characters:

- one bullet per issue: what it actually teaches or announces, in one
  line (skip marketing adjectives)
- group by sender when a sender sent more than one
- if the snippets are too thin to summarise an issue, say "subject only"

Issues:
{listing}"""
    return _run(prompt).strip()
