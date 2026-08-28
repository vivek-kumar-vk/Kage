"""the_hermes_team - INKY's Bot Mode group `inky-team`, as code.

Phase H step 5.1 (owner spec, Hermes_Wrap_Source_Notes_From_Owner.md
"Step 4: Bot Mode"): the ten Hermes bot profiles are wrapped; this file is
the piece INKY itself owns - the GROUP definition and the handoff rules a
group chat obeys, written down where tests can hold them:

    Group name      inky-team
    Max bots        6        (stay in the Smart Zone: < 100k tokens)
    Max rounds      3 serial rounds per group conversation
    Handoff         @mention routes into that bot's persistent
                    "Agent Inbox" conversation - a real CLI call,
                    never an in-process import

The roster is exactly the six bots the owner named for the group:
orchestrator, teacher, qa, ui_steward, models_quota_warden, evolution.
The other profiles stay single-bot workers outside the group.

Every send is one hermes CLI invocation in its non-interactive form.
Nothing here starts a daemon, carries a key, or names a model - each bot's
model is pinned in its own Hermes profile, and this file must stay ignorant
of model names (same rule the fallback chain obeys).

Tier 0 first, always: parsing mentions, planning rounds and building argv
are pure functions. Only send_handoff touches the CLI, and it degrades to
an honest (False, reason) instead of raising.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # Shared_By_All_Agents
_PROJECT_ROOT = _HERE.parent                    # the inky folder
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

GROUP_NAME = "inky-team"
MAX_BOTS = 6
MAX_SERIAL_ROUNDS = 3
SMART_ZONE_TOKEN_CEILING = 100_000              # owner's Smart Zone bound
INBOX_CONVERSATION = "Agent Inbox"

# The six seats of the group, in handoff-friendly order (the seat first,
# the validators last). Each entry: what the bot is FOR - the SOUL.md in
# its Hermes profile carries the full role text.
ROSTER = {
    "orchestrator": "plans missions, generates Validation Contracts, hands off",
    "teacher": "answers codebase questions from its index, learns error+fix",
    "qa": "runs E2E after green pytest, waits for data-fresh, Empty beats fake",
    "ui_steward": "discovers screens, updates Main_Menu, checks liveness",
    "models_quota_warden": "tracks provider quotas, switches providers",
    "evolution": "triages the ideas board into DAG tickets",
}

_HERMES_PROFILES_DIR = (Path.home() / "AppData" / "Local" / "hermes"
                        / "profiles")

_MENTION = re.compile(r"@([a-z_]+)")


def parse_mentions(text: str) -> tuple[list[str], list[str]]:
    """Split @mentions into (valid roster bots in first-mention order,
    unknown names). Unknown mentions are reported, never silently dropped -
    data honesty applies to routing too."""
    seen_valid: list[str] = []
    unknown: list[str] = []
    for name in _MENTION.findall(text or ""):
        if name in ROSTER:
            if name not in seen_valid:
                seen_valid.append(name)
        elif name not in unknown:
            unknown.append(name)
    return seen_valid, unknown


def build_round_plan(mentioned_bots: list[str]) -> tuple[list[list[str]], str]:
    """Deal the mentioned bots into serial rounds, at most MAX_SERIAL_ROUNDS.

    Returns (rounds, "") on success or ([], reason) when the plan would
    break the group's own rules. A round is one pass through the group
    chat; every mention in a round is answered before the next round opens.
    """
    unique: list[str] = []
    for bot in mentioned_bots:
        if bot in ROSTER and bot not in unique:
            unique.append(bot)
    if not unique:
        return [], "no valid bot mentioned - nothing to plan"
    if len(unique) > MAX_BOTS:
        return [], (f"{len(unique)} bots mentioned, the group holds at "
                    f"most {MAX_BOTS} (Smart Zone)")
    rounds: list[list[str]] = [unique[i:i + MAX_BOTS]
                               for i in range(0, len(unique), MAX_BOTS)]
    if len(rounds) > MAX_SERIAL_ROUNDS:
        return [], (f"{len(rounds)} serial rounds needed, the group allows "
                    f"at most {MAX_SERIAL_ROUNDS}")
    return rounds, ""


def profile_exists(bot: str) -> bool:
    """True when the bot's Hermes profile folder exists on this machine."""
    return bot in ROSTER and (_HERMES_PROFILES_DIR / bot).is_dir()


def group_status() -> tuple[list[str], list[str]]:
    """(bots whose Hermes profile exists, bots missing one). A missing
    profile is reported, never faked."""
    present = [b for b in ROSTER if (_HERMES_PROFILES_DIR / b).is_dir()]
    return present, [b for b in ROSTER if b not in present]


def handoff_command(bot: str, message: str) -> tuple[list[str], str]:
    """The exact argv for one headless handoff into `bot`'s Agent Inbox,
    or ([], reason). Pure - builds nothing, runs nothing."""
    if bot not in ROSTER:
        return [], f"'{bot}' is not in the {GROUP_NAME} roster"
    text = (message or "").strip()
    if not text:
        return [], "empty handoff message refused"
    # --continue + --create-if-missing: the persistent Agent Inbox
    # conversation, created on first touch. -Q keeps programmatic output
    # to the reply alone.
    argv = ["hermes", "-p", bot, "chat",
            "--continue", INBOX_CONVERSATION, "--create-if-missing",
            "-Q", "-q", text]
    lowered = " ".join(argv).lower()
    for banned in ("daemon", "--api-key", "api_key", "credentials"):
        if banned in lowered:
            return [], f"refusing to build argv containing '{banned}'"
    return argv, ""


def _trace(subject: str, outcome: str, target: str, detail: dict,
           correlation_id: str, duration_ms: int | None = None) -> None:
    """One row in the trace ledger per handoff attempt. The ledger must
    never be the thing that breaks a handoff."""
    try:
        from Shared_By_All_Screens.trace_every_action import trace
        trace("the_hermes_team", "skill", subject, target=target,
              outcome=outcome, detail=str(detail)[:160], duration_ms=duration_ms,
              correlation_id=correlation_id)
    except Exception:                                          # noqa: BLE001
        pass


def send_handoff(bot: str, message: str, correlation_id: str | None = None,
                 timeout_s: int = 900) -> tuple[bool, str, str]:
    """One real handoff into a bot's Agent Inbox. Returns (ok, reply_text,
    detail). Traced under one correlation_id like every other walk. Never
    raises - a dead bot is an honest False, not an exception in the caller."""
    if correlation_id is None:
        try:
            from Shared_By_All_Screens.trace_every_action import (
                new_correlation_id)
            correlation_id = new_correlation_id()
        except Exception:                                      # noqa: BLE001
            correlation_id = "untraced"
    argv, reason = handoff_command(bot, message)
    if not argv:
        _trace("handoff_refused", "refused", bot, {"reason": reason},
               correlation_id)
        return False, "", reason
    started = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _trace("handoff_timeout", "timeout", bot,
               {"timeout_s": timeout_s}, correlation_id)
        return False, "", f"{bot} did not answer within {timeout_s}s"
    except OSError as exc:
        _trace("handoff_error", "error", bot, {"error": str(exc)[:120]},
               correlation_id)
        return False, "", f"could not start hermes for {bot}: {exc}"
    duration_ms = int((time.monotonic() - started) * 1000)
    ok = done.returncode == 0 and bool(done.stdout.strip())
    reply = done.stdout.strip() if ok else ""
    detail = (f"reply_chars={len(reply)}" if ok else
              f"exit={done.returncode} stderr={done.stderr.strip()[:200]}")
    _trace("handoff_to_inbox", "ok" if ok else "failed", bot,
           {"detail": detail}, correlation_id, duration_ms=duration_ms)
    return ok, reply, detail


def _trace(subject: str, outcome: str, target: str, detail: dict,
           correlation_id: str, duration_ms: int | None = None) -> None:
    """One row in the trace ledger per handoff attempt. The ledger must
    never be the thing that breaks a handoff."""
    try:
        from Shared_By_All_Screens.trace_every_action import trace
        trace("the_hermes_team", "skill", subject, target=target,
              outcome=outcome, detail=str(detail)[:160], duration_ms=duration_ms,
              correlation_id=correlation_id)
    except Exception:                                          # noqa: BLE001
        pass


def send_handoff(bot: str, message: str, correlation_id: str | None = None,
                 timeout_s: int = 900) -> tuple[bool, str, str]:
    """One real handoff into a bot's Agent Inbox. Returns (ok, reply_text,
    detail). Traced under one correlation_id like every other walk. Never
    raises - a dead bot is an honest False, not an exception in the caller."""
    if correlation_id is None:
        try:
            from Shared_By_All_Screens.trace_every_action import (
                new_correlation_id)
            correlation_id = new_correlation_id()
        except Exception:                                      # noqa: BLE001
            correlation_id = "untraced"
    argv, reason = handoff_command(bot, message)
    if not argv:
        _trace("handoff_refused", "refused", bot, {"reason": reason},
               correlation_id)
        return False, "", reason
    started = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _trace("handoff_timeout", "timeout", bot,
               {"timeout_s": timeout_s}, correlation_id)
        return False, "", f"{bot} did not answer within {timeout_s}s"
    except OSError as exc:
        _trace("handoff_error", "error", bot, {"error": str(exc)[:120]},
               correlation_id)
        return False, "", f"could not start hermes for {bot}: {exc}"
    duration_ms = int((time.monotonic() - started) * 1000)
    ok = done.returncode == 0 and bool(done.stdout.strip())
    reply = done.stdout.strip() if ok else ""
    detail = (f"reply_chars={len(reply)}" if ok else
              f"exit={done.returncode} stderr={done.stderr.strip()[:200]}")
    _trace("handoff_to_inbox", "ok" if ok else "failed", bot,
           {"detail": detail}, correlation_id, duration_ms=duration_ms)
    return ok, reply, detail

    present = [b for b in ROSTER if (_HERMES_PROFILES_DIR / b).is_dir()]
    return present, [b for b in ROSTER if b not in present]


def handoff_command(bot: str, message: str) -> tuple[list[str], str]:
    """The exact argv for one headless handoff into `bot`'s Agent Inbox,
    or ([], reason). Pure - builds nothing, runs nothing."""
    if bot not in ROSTER:
        return [], f"'{bot}' is not in the {GROUP_NAME} roster"
    text = (message or "").strip()
    if not text:
        return [], "empty handoff message refused"
    # --continue + --create-if-missing: the persistent Agent Inbox
    # conversation, created on first touch. -Q keeps programmatic output
    # to the reply alone.
    argv = ["hermes", "-p", bot, "chat",
            "--continue", INBOX_CONVERSATION, "--create-if-missing",
            "-Q", "-q", text]
    lowered = " ".join(argv).lower()
    for banned in ("daemon", "--api-key", "api_key", "credentials"):
        if banned in lowered:
            return [], f"refusing to build argv containing '{banned}'"
    return argv, ""
