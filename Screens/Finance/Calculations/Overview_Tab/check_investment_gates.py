"""The four checks that decide whether you can invest this month.

WHAT A GATE IS
    A yes/no question with a reason attached. Nothing more.

        G1  Is there any money left over at all?
        G2  Is the emergency fund big enough?
        G3  Have you borrowed against your investments?
        G4  Is the amount you want to put in too big?

HOW THEY RUN
    In order, and it STOPS at the first "no".

    If G1 says there is no money, G2 through G4 never run. Their answers
    would be noise — the state of your emergency fund does not matter
    when there is nothing to invest either way. A short list of results
    is the point: it shows exactly where things halted.

WHAT THIS FILE WILL NEVER DO
    Tell you what to buy. It says whether you may invest and how much.
    Choosing the fund is your decision, and later the Market module's
    job to display. The part that says "you have X available" must never
    be the part that says "buy Y".

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Overview_Tab\\check_investment_gates.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple

# This file sits at  Screens/<Screen>/Calculations/<this file>.py
HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))   # so this screen's own files import by name

# The rupee sign is not in the old Windows console codepage. Without this
# line, printing a single figure crashes with a UnicodeEncodeError - which
# looks like a bug in the maths and is not.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from Shared_By_All_Screens.read_and_write_numbers import read_state          # noqa: E402
from Shared_By_All_Screens.format_indian_money import format_inr       # noqa: E402


class GateResult(NamedTuple):
    """The answer from one gate.

    The first two fields are always `passed` and `reason`, in that order.
    Everything after them is extra detail the screen can use. Keeping
    those two first means any gate can be read the same simple way:

        passed, reason = result[0], result[1]
    """

    passed: bool
    reason: str
    gate: str = ""
    tier: str | None = None        # G2 only: highest buffer tier reached
    next_tier: str | None = None   # G2 only: the tier being worked toward
    distance: int | None = None    # G2 only: rupees to the next tier
    partial: bool = False          # passed, but not at full unlock


# =====================================================================
# G1 — IS THERE ANY MONEY?
# =====================================================================

def g1_capital(surplus: int) -> GateResult:
    """Fails when there is nothing left over.

    Zero counts as a failure, not a pass. Zero left over means nothing to
    invest, so treating it as "fine" would be wrong. The line is drawn at
    `<= 0`.

    Right now surplus is -₹1,700, so this fails and everything below it
    stops. That is the correct answer, not a bug.
    """
    if surplus <= 0:
        return GateResult(False, "NO CAPITAL. MARKET ROUTE SUPPRESSED.", "G1")
    return GateResult(True, f"Capital available: {format_inr(surplus)}", "G1")


# =====================================================================
# G2 — IS THE EMERGENCY FUND BIG ENOUGH?
#
# This one is not a simple yes/no. A single ₹65,000 target would stay
# shut for about two years, and a check that says the same thing for two
# years stops being read. So it has two levels:
#
#     T1  ₹28,000   clears the credit line once. Partial investing OK
#     T2  ₹65,000   fully unlocked
#
# Now it has something new to report every month.
# =====================================================================

def buffer_tiers(state: dict) -> list[tuple[str, int, str]]:
    return [
        ("T1", state["buffer_tier_1"], "Clears the revolving line once. Partial deploy allowed"),
        ("T2", state["buffer_tier_2"], "Full unlock"),
    ]


def g2_buffer(emergency_fund: int, state: dict) -> GateResult:
    """Which buffer level has been reached, and how far to the next one.

    Below T1   shut. All spare money goes to the emergency fund
    T1 to T2   open, but partial. G4 still caps the size
    T2 upwards open, fully

    Returns the level reached AND the distance to the next one, so the
    screen can show progress rather than just a red light.
    """
    tiers = buffer_tiers(state)
    reached = None
    for name, amount, _ in tiers:
        if emergency_fund >= amount:
            reached = name

    nxt = next(((n, a) for n, a, _ in tiers if emergency_fund < a), None)
    distance = (nxt[1] - emergency_fund) if nxt else None
    next_name = nxt[0] if nxt else None

    if reached is None:
        return GateResult(
            False,
            "BUFFER GATE. Surplus routes to emergency fund.",
            "G2", None, next_name, distance, False,
        )

    if reached == "T2":
        return GateResult(
            True, "Buffer at T2. Full unlock.", "G2", "T2", None, None, False
        )

    return GateResult(
        True,
        "Buffer at T1. Partial deploy allowed. Sizing still capped by G4.",
        "G2", "T1", next_name, distance, True,
    )


# =====================================================================
# G3 — HAVE YOU BORROWED AGAINST YOUR INVESTMENTS?
#
# If money has been drawn against pledged holdings, that debt gets
# cleared before anything new goes in. Borrowing to invest while already
# borrowed against investments is how people get into trouble.
# =====================================================================

def g3_pledge(lamf_drawn: int) -> GateResult:
    if lamf_drawn > 0:
        return GateResult(
            False, "DEBT DRAWN. No new deployment until cleared.", "G3"
        )
    return GateResult(True, "No pledge drawn.", "G3")


# =====================================================================
# G4 — IS THE AMOUNT TOO BIG?
#
# The only gate that needs you to name a figure first. With no figure it
# just reports the ceiling instead of judging a number nobody asked
# about.
# =====================================================================

def g4_sizing(request: int | None, deployable: int) -> GateResult:
    """Only meaningful against a specific request.

    With no request there is nothing to size, so this reports the ceiling
    rather than passing judgement on a number nobody asked about.
    """
    if request is None:
        return GateResult(True, f"Max deployable: {format_inr(deployable)}", "G4")
    if request > deployable:
        return GateResult(
            False, f"OVER-SIZED. Max = {format_inr(deployable)}.", "G4"
        )
    return GateResult(True, f"Within size. Max = {format_inr(deployable)}.", "G4")


# =====================================================================
# THE CHAIN — run them in order, stop at the first failure
# =====================================================================

def evaluate(surplus: int, deployable: int, state: dict,
             request: int | None = None) -> list[GateResult]:
    """Run G1-G4 in order, stopping at the first failure.

    Returns only the gates actually evaluated. A short list is the point:
    it shows where the chain stopped.
    """
    results = [g1_capital(surplus)]
    if not results[-1].passed:
        return results

    results.append(g2_buffer(state["emergency_fund"], state))
    if not results[-1].passed:
        return results

    results.append(g3_pledge(state["lamf_drawn"]))
    if not results[-1].passed:
        return results

    results.append(g4_sizing(request, deployable))
    return results


# =====================================================================
# PREVIEW — what a gate that has not run yet would say if it did
#
# Added 2026-08-22 at the owner's request: the page shows a
# `not_reached` gate as "would pass, in transition" (green, marked with
# a ! and a hover reason) when this preview says it would - never as an
# actual PASS. `evaluate()` above is completely untouched and is still
# the only thing that decides what is really blocked; this never feeds
# a decision, only a label on something that has not been decided yet.
# =====================================================================

def preview(gate_name: str, surplus: int, deployable: int, state: dict) -> GateResult:
    """What one gate would say, called on its own, regardless of chain
    order. Every gate function here is pure and cheap, so calling one
    out of turn costs nothing and changes nothing - it just answers a
    "what if" instead of "what actually happens next"."""
    if gate_name == "G1":
        return g1_capital(surplus)
    if gate_name == "G2":
        return g2_buffer(state["emergency_fund"], state)
    if gate_name == "G3":
        return g3_pledge(state["lamf_drawn"])
    if gate_name == "G4":
        return g4_sizing(None, deployable)
    raise ValueError(f"no such gate: {gate_name}")


def blocked_by(results: list[GateResult]) -> GateResult | None:
    """The first failing gate, or None if the chain is clear."""
    return next((r for r in results if not r.passed), None)


def main() -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from calculate_surplus import compute

    state = read_state()
    s = compute(state)
    results = evaluate(s.surplus, s.deployable, state)

    print("GATES")
    print()
    for r in results:
        print(f"  {r.gate}  {'PASS' if r.passed else 'FAIL'}  {r.reason}")

    evaluated = {r.gate for r in results}
    for name in ("G1", "G2", "G3", "G4"):
        if name not in evaluated:
            print(f"  {name}  ----  not evaluated, chain stopped earlier")

    print()
    b = blocked_by(results)
    print(f"  BLOCKED AT {b.gate}" if b else "  ALL GATES OPEN")


if __name__ == "__main__":
    main()
