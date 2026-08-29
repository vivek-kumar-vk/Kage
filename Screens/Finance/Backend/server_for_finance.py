"""Backend for the Finance UI.

WHAT THIS FILE DOES
    Turns the numbers computed in this screen's Calculations folder
    into JSON that
    the Finance page can fetch.

WHAT THIS FILE MUST NEVER DO
    Any arithmetic. Not one subtraction. If a figure were worked out here
    as well as in the scripts folder, there would be two answers to the
    same question and no way to know which is right. This file only
    fetches, formats and hands over.

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    python Screens\\Finance\\Backend\\server_for_finance.py
    then open http://127.0.0.1:8001
"""

# =====================================================================
# SETUP - make this screen's own files importable
# =====================================================================
import sys
from pathlib import Path

# This file sits at  Screens/Finance/Backend/server_for_finance.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Finance folder
PROJECT_ROOT = HERE.parents[2]              # the inky folder

sys.path.insert(0, str(PROJECT_ROOT))       # for Shared_By_All_Screens
sys.path.insert(0, str(HERE))               # for this screen's settings
sys.path.insert(0, str(SCREEN / "Calculations"))   # for this screen's maths
for _group in (SCREEN / "Calculations").iterdir():   # tab-mirrored groups
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":
        sys.path.insert(0, str(_group))

from fastapi import Body, FastAPI                                    # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles                          # noqa: E402

import settings_for_finance as cfg                                   # noqa: E402

# The maths lives in this screen's own Calculations folder. This file
# only reads from it - it works nothing out for itself.
import calculate_debt_dates as debt_engine                           # noqa: E402
import check_investment_gates as gates                               # noqa: E402
from calculate_surplus import compute                                # noqa: E402
import fetch_fund_facts                                              # noqa: E402
import find_the_overlap                                              # noqa: E402
import read_portfolio_holdings as portfolio_holdings                 # noqa: E402
import read_what_i_own                                               # noqa: E402
import track_assets_and_liabilities as assets_and_liabilities        # noqa: E402
import score_financial_health as health_score                        # noqa: E402
import write_the_finance_report as finance_report                    # noqa: E402
import track_the_nav_ledger                                          # noqa: E402
import compute_the_xirr                                              # noqa: E402
import build_the_sector_map                                          # noqa: E402
import analyse_a_fund                                                # noqa: E402
import build_the_portfolio_review                                    # noqa: E402
import run_the_daily_pull                                            # noqa: E402

# The model gateway, for the two "Ask INKY" strips (Investments ask,
# Portfolio ask - the Chat tab itself was removed by ADR-102). Finance is
# Tier 0 by design (ADR-040) - every other endpoint on this screen calls
# nothing. An ask strip is the one place a person can ask a question, and
# it is reached over HTTP, never by import (C8) - a screen may not put
# another screen's folder on its import path, the gateway included.
# The "finance" chain is empty until a provider is cleared (Rule 5), so
# today every message comes back as an honest refusal, never a silent
# answer.
import json
import csv
import re
import time
import urllib.error
import urllib.request                                                 # noqa: E402

from Shared_By_All_Screens.format_indian_money import format_inr, format_signed  # noqa: E402
from Shared_By_All_Screens.read_and_write_numbers import read_state   # noqa: E402
from Shared_By_All_Screens.show_not_built_yet import page_html        # noqa: E402
from Shared_By_All_Screens.trace_every_action import (             # noqa: E402
    new_correlation_id, trace,
)


app = FastAPI(title=cfg.SCREEN_LABEL)

# Liveness + dependency probe (Phase-1 W1.3): /health answers
# process=alive plus each data source as ok/down/stale - never a green
# light over an empty filing cabinet.
from Shared_By_All_Screens import health_check                          # noqa: E402
health_check.register(app, "finance", saved_records=lambda: cfg.SAVED_RECORDS)


# =====================================================================
# THE TRACE LEDGER - every served request and every page click lands in
# Shared_By_All_Screens/Trace_Ledger/, so the nightly local-model
# reflection sees the whole day. Static assets are not traced: a CSS
# fetch is noise, a person's action is signal.
# =====================================================================
@app.middleware("http")
async def _trace_api_requests(request, call_next):
    started = time.time()
    # Phase-1 CS-1: one correlation id per request - honoured from an
    # inbound X-Correlation-Id header when present, minted when not,
    # echoed back so the caller can chain the next hop.
    cid = request.headers.get("x-correlation-id") or new_correlation_id()
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    path = request.url.path
    # "/dev" is excluded on purpose - it hosts the 30-second auto-refresh
    # poll, and tracing that poll would be noise, not signal.
    if not path.startswith(("/shared", "/page", "/fonts", "/docs", "/redoc",
                            "/openapi.json", "/dev")):
        trace("finance", "api", f"{request.method} {path}",
              target=path.split("/")[-1] or "/",
              detail={"status": response.status_code},
              outcome="ok" if response.status_code < 400 else "fail",
              duration_ms=int((time.time() - started) * 1000),
              correlation_id=cid)
    return response


@app.post(cfg.API_PREFIX + "/trace")
def receive_page_trace(event: dict = Body(...)):
    """Receive one UI event from the page's own tracer.

    The page sends clicks and tab opens; this only relays them into the
    ledger. Untrusted by design: fields are length-capped and kind-checked
    inside trace(), so a malformed event degrades to a dropped line,
    never an error the page has to handle.
    """
    written = trace(
        actor=event.get("actor") or "you",
        kind=event.get("kind") or "click",
        action=event.get("action") or "unknown",
        target=event.get("target") or "",
        detail=event.get("detail"),
        outcome=event.get("outcome") or "ok",
        duration_ms=event.get("duration_ms"),
        correlation_id=event.get("correlation_id"),
    )
    return {"ok": written}


@app.get("/dev/changed-since")
def dev_changed_since(token: str = ""):
    """Has any code file behind this page moved since it was loaded?

    Fixed path, not under API_PREFIX - every screen serves this at the
    same relative URL so one shared JS can poll it without knowing that
    screen's prefix. An empty token only establishes the baseline and
    can never say "changed" - otherwise every fresh page would reload
    in a loop the moment it opened.
    """
    from Shared_By_All_Screens.code_change_monitor import (
        has_changed, is_enabled,
    )
    result = has_changed(token, cfg.WATCHED_FOLDERS)
    if not is_enabled():
        return {"changed": False, "fingerprint": result["fingerprint"],
                "latest_file": "", "latest_at": ""}
    if result["changed"] and token:
        trace("finance", "ledger", "file_changed",
              target=result["latest_file"],
              detail={"latest_at": result["latest_at"]})
    return result



# =====================================================================
# HELPERS
# =====================================================================
def _money(value):
    """One dict describing one figure, so the page never formats numbers.

    Every amount is sent three ways:
      raw    - the plain number, for maths or sorting in the browser
      text   - already formatted the Indian way, e.g. "₹1,60,764"
      signed - with a + or - in front, used for surplus

    The page just prints `text`. If formatting lived in JavaScript there
    would be two sets of rules for how a rupee looks.
    """
    if value is None:
        return {"raw": None, "text": "—", "signed": "—", "known": False}
    return {
        "raw": value,
        "text": format_inr(value),
        "signed": format_signed(value),
        "known": True,
    }


# =====================================================================
# THE PAGE ITSELF
# =====================================================================
@app.get("/")
def page():
    """Send this screen's page, or say plainly that it is not written yet."""
    # The Next.js rebuild (Phase 12.4): same guard as every other screen
    # that has gone through this - only when the flag is on AND the
    # static export actually exists does it take over the root route. A
    # flag on with no build falls through to the vanilla page instead of
    # a blank screen - honest beats broken.
    if getattr(cfg, "USE_NEXT_UI", False):
        index = getattr(cfg, "NEXT_DIST", None)
        if index is not None and (index / "index.html").exists():
            return FileResponse(index / "index.html")
    if cfg.PAGE.exists():
        return FileResponse(cfg.PAGE)

    return HTMLResponse(page_html(
        cfg.SCREEN_LABEL,
        cfg.PAGE,
        [f"{cfg.API_PREFIX}/command",
         f"{cfg.API_PREFIX}/money",
         f"{cfg.API_PREFIX}/debt",
         f"{cfg.API_PREFIX}/ledgers"],
    ))


# =====================================================================
# TAB 1 — COMMAND
# The "am I OK" screen. Surplus, the four gates, buffer, countdowns.
# =====================================================================
@app.get(cfg.API_PREFIX + "/command")
def command():
    state = read_state()
    surplus = compute(state)

    # Run the gate chain. It stops at the first failure on purpose, so a
    # short list here is meaningful - it shows where things halted.
    results = gates.evaluate(surplus.surplus, surplus.deployable, state)
    blocker = gates.blocked_by(results)
    evaluated = {r.gate for r in results}

    # Gates that never ran are reported as "not reached", never as passed.
    # A not-reached gate also carries a `preview` - what it would say if
    # called on its own right now (gates.preview(), added 2026-08-22).
    # The page uses this to mark a gate that would clear as "in
    # transition" (green with a ! and the reason on hover) rather than
    # leaving it a plain grey dash - without ever claiming it actually
    # ran. `evaluate()` above, and `blocked_at` below, are untouched:
    # this is a label, never a decision.
    gate_rows = []
    for name in ("G1", "G2", "G3", "G4"):
        hit = next((r for r in results if r.gate == name), None)
        if hit is None:
            prev = gates.preview(name, surplus.surplus, surplus.deployable, state)
            gate_rows.append({
                "gate": name, "state": "not_reached", "reason": "",
                "preview": {"passed": prev.passed, "reason": prev.reason},
            })
        elif not hit.passed:
            gate_rows.append({"gate": name, "state": "fail", "reason": hit.reason})
        elif getattr(hit, "partial", False):
            gate_rows.append({"gate": name, "state": "partial", "reason": hit.reason})
        else:
            gate_rows.append({"gate": name, "state": "pass", "reason": hit.reason})

    # Buffer progress, in tiers rather than one distant target.
    buffer = gates.g2_buffer(state["emergency_fund"], state)

    # The two countdowns. The personal debt one is the important number.
    personal = debt_engine.flat_countdown(state["uncle_remaining"],
                                          state["uncle_monthly"])
    step = debt_engine.surplus_step_change(surplus.surplus, personal)
    loan = debt_engine.amortise(state["edu_loan_outstanding"],
                                state["edu_loan_rate"],
                                state["edu_loan_emi"])

    return {
        "surplus": _money(surplus.surplus),
        "deployable": _money(surplus.deployable),
        "blocked_at": blocker.gate if blocker else None,
        "blocked_reason": blocker.reason if blocker else None,
        "gates": gate_rows,
        "buffer": {
            "fund": _money(state["emergency_fund"]),
            "tier_reached": buffer.tier,
            "next_tier": buffer.next_tier,
            "distance": _money(buffer.distance),
            # The tier amount itself (₹28,000 or ₹65,000), so the page can
            # draw a real fill-bar (fund / this) without reformatting a
            # rupee figure in JavaScript - the one thing this project
            # keeps server-side on purpose. None once T2 is reached, same
            # as next_tier and distance.
            "next_tier_target": _money(
                state["buffer_tier_1"] if buffer.next_tier == "T1"
                else state["buffer_tier_2"] if buffer.next_tier == "T2"
                else None
            ),
        },
        "countdowns": {
            # The date that changes the whole picture. It used to also
            # show as a gauge on the main menu; ADR-049 removed that, so
            # this screen is now the only place it appears.
            "personal_debt": {
                "clears": personal.clear_label,
                "months_left": personal.months_left,
                "surplus_before": _money(step.before),
                "surplus_after": _money(step.after),
            },
            "education_loan": {
                "clears": loan.payoff_label,
                "months_left": loan.months,
                "interest_remaining": _money(loan.total_interest),
            },
        },
        # Owned by the Market module, which does not exist yet. Passed
        # through the noticeboard, because no screen may import another.
        "portfolio_total": _money(state["portfolio_total"]),
    }


# =====================================================================
# STILL TAB 1 — THE HEALTH SCORE
#
# This sits on Overview rather than on a tab of its own - the score is
# computed entirely from figures the Overview tab already shows, so it
# was never worth a tab of its own, and the five-tab ceiling (CLAUDE.md)
# stays comfortably clear now that Chat is gone (ADR-102).
# =====================================================================
@app.get(cfg.API_PREFIX + "/health-score")
def health():
    """The composite score and its five parts.

    Every category reports whether it could be measured at all. A
    category with no data comes back with `scored: null` and the reason,
    never with a middling default that would look like a measurement.
    """
    result = health_score.compute()

    return {
        "score": result.score_out_of_100,
        "grade": result.grade,
        "signal": result.signal,
        "points_possible": result.points_possible,
        "points_total": sum(c.weight for c in result.categories),
        "coverage_pct": result.coverage_pct,
        "weakest": result.weakest.name if result.weakest else None,
        "categories": [
            {
                "name": c.name,
                "weight": c.weight,
                "scored": c.scored,
                "pct": c.pct,
                "measured": c.measured,
                "could_not_measure": c.could_not_measure,
            }
            for c in result.categories
        ],
    }


@app.post(cfg.API_PREFIX + "/health-score/report")
def write_report():
    """Write the full report to Saved_Records/Reports/ and say where.

    A POST because it writes a file. The page never renders the report
    itself - it is a note meant to be opened in Obsidian alongside the
    rest of the vault, which is the whole reason it is Markdown and not
    a PDF.
    """
    path = finance_report.write()
    return {
        "written_to": str(path.relative_to(cfg.PROJECT_ROOT)),
        "lines": len(path.read_text(encoding="utf-8").splitlines()),
    }


# =====================================================================
# TAB 2 — MONEY
# The surplus formula, one line per input, so the total can be checked.
# =====================================================================
@app.get(cfg.API_PREFIX + "/money")
def money():
    s = compute(read_state())
    return {
        "lines": [
            {"label": label, "amount": _money(amount)}
            for label, amount, _ in s.lines()
        ],
        "surplus": _money(s.surplus),
        "emergency_contribution": _money(s.emergency_contribution),
        "deployable": _money(s.deployable),
        # A second, separate figure, added 2026-08-22 at the owner's
        # request: bills, debt and SIPs only, before the Slice refill.
        # Shown next to surplus, never merged into it (see
        # calculate_surplus.py for why the two must stay apart).
        "before_slice_refill": _money(s.before_slice_refill),
    }


# =====================================================================
# TAB 3 — DEBT
# ?extra=2000 answers "what if I pay 2000 more every month".
# =====================================================================
@app.get(cfg.API_PREFIX + "/debt")
def debt(extra: int = 0):
    state = read_state()

    effect = debt_engine.extra_payment_effect(
        state["edu_loan_outstanding"],
        state["edu_loan_rate"],
        state["edu_loan_emi"],
        extra,
    )
    personal = debt_engine.flat_countdown(state["uncle_remaining"],
                                          state["uncle_monthly"])

    return {
        "education_loan": {
            "outstanding": _money(state["edu_loan_outstanding"]),
            "rate_pct": state["edu_loan_rate"],
            "emi": _money(state["edu_loan_emi"]),
            "payoff_now": effect["base"].payoff_label,
            "payoff_with_extra": effect["with_extra"].payoff_label,
            "months_saved": effect["months_saved"],
            "interest_saved": _money(effect["interest_saved"]),
            # The full monthly amortisation. It feeds the payoff chart on
            # the Debt tab's Loans sub-tab - balance line plus the
            # principal/interest split of every payment.
            "schedule": effect["base"].rows,
        },
        "personal_debt": {
            "remaining": _money(personal.remaining),
            "monthly": _money(personal.monthly),
            "months_left": personal.months_left,
            "clears": personal.clear_label,
        },
    }


# =====================================================================
# TAB 4 — LEDGERS
# The CSV files as-is. Read only. No editing from the browser.
# =====================================================================
@app.get(cfg.API_PREFIX + "/ledgers")
def ledgers():
    import csv

    folder = cfg.SAVED_RECORDS
    out = {}

    for path in sorted(folder.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Read the column names from the reader, NOT from the first
            # row. Most of these files are headers only, and asking an
            # empty list for row[0] is how this crashed the first time.
            columns = list(reader.fieldnames or [])
            rows = list(reader)

        out[path.stem] = {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            # An empty ledger says it is empty. It is never padded with
            # sample rows to make the screen look busy.
            "empty": len(rows) == 0,
        }

    return out


# =====================================================================
# TAB 5 — INVESTMENTS
# Two real sources, never merged into one number silently:
#   portfolio_holdings.csv   a snapshot - invested/current stated
#                            directly, editable from this tab
#   my_investments.csv       a transaction log - holdings derived by
#                            adding up buys and sells, NAV fetched live
# A fund only ever needs to live in one of the two. Both are shown so
# nothing typed into either file goes unseen.
# =====================================================================
@app.get(cfg.API_PREFIX + "/investments")
def investments():
    read_what_i_own.start_the_records_if_missing()
    portfolio_holdings.start_the_records_if_missing()

    snapshot = portfolio_holdings.a_summary_for_the_screen()
    logged = read_what_i_own.what_i_hold_now()
    logged_summary = read_what_i_own.a_summary_for_the_screen()

    logged_rows = []
    for h in logged:
        row = {**h, "amount_invested": _money(h["amount_invested"])}
        if h["kind"] == "mutual_fund":
            nav = fetch_fund_facts.latest_nav(h["identifier"])
            row["nav"] = _money(nav.get("nav")) if nav.get("has_data") else _money(None)
            row["nav_date"] = nav.get("nav_date")
            row["nav_source"] = nav.get("where_from") if nav.get("has_data") else None
        else:
            row["nav"] = _money(None)
            row["nav_date"] = None
            row["nav_source"] = None
        logged_rows.append(row)

    snapshot_rows = []
    if snapshot["has_data"]:
        for h in snapshot["holdings"]:
            snapshot_rows.append({
                **h,
                "invested": _money(h["invested"]), "current": _money(h["current"]),
                "pl_abs": _money(h["pl_abs"]),
            })

    return {
        "has_snapshot": snapshot["has_data"],
        "snapshot_note": snapshot.get("note"),
        "snapshot_total_invested": _money(snapshot.get("total_invested")),
        "snapshot_total_current": _money(snapshot.get("total_current")),
        "snapshot_total_pl": _money(snapshot.get("total_pl")),
        "snapshot_holdings": snapshot_rows,

        "has_logged_data": logged_summary["has_data"],
        "logged_note": logged_summary.get("note"),
        "logged_total_invested": _money(logged_summary.get("total_invested")),
        "how_many_funds": logged_summary.get("how_many_funds"),
        "how_many_shares": logged_summary.get("how_many_shares"),
        "months_investing": logged_summary.get("months_investing"),
        "monthly_habit": read_what_i_own.how_much_i_put_in_each_month(),
        "logged_holdings": logged_rows,
    }


@app.post(cfg.API_PREFIX + "/investments/holdings")
def add_holding(body: dict = Body(...)):
    try:
        row = portfolio_holdings.add_holding(
            body.get("scheme_name"), amfi_code=body.get("amfi_code", ""),
            category=body.get("category", "mutual_fund"), units=body.get("units"),
            invested=body.get("invested"), current=body.get("current"),
            source=body.get("source") or "added by hand",
        )
    except (ValueError, portfolio_holdings.TheRecordsAreWrong) as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "holding": row}


@app.put(cfg.API_PREFIX + "/investments/holdings")
def edit_holding(body: dict = Body(...)):
    scheme_name = body.get("scheme_name")
    amfi_code = body.get("amfi_code", "")
    changes = {k: v for k, v in body.items() if k not in ("scheme_name", "amfi_code")}
    try:
        row = portfolio_holdings.update_holding(scheme_name, amfi_code, changes)
    except KeyError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except (ValueError, portfolio_holdings.TheRecordsAreWrong) as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "holding": row}


@app.delete(cfg.API_PREFIX + "/investments/holdings")
def remove_holding(scheme_name: str, amfi_code: str = ""):
    removed = portfolio_holdings.delete_holding(scheme_name, amfi_code)
    if not removed:
        return JSONResponse({"ok": False, "problem": "no such holding"}, status_code=404)
    return {"ok": True}


# =====================================================================
# TAB 5b — FUND HOLDINGS ANALYSIS (the button on each fund row)
# The full picture of one fund: the holdings ledger (name, sector,
# instrument, assets), the Equity/Debt/Cash split, the market-cap
# split, sector allocation, weighted P/E / P/B and the advanced ratios.
# Served from the stored profile; a fund never analysed is analysed on
# first ask, which can take a few seconds of honest web fetching.
# =====================================================================
def _my_position_for(amfi_code: str) -> dict:
    """The user's own holding in this one fund, from the snapshot CSV -
    what the modal's 'My Investment Summary' card shows. No arithmetic
    here: invested and current go out as the money dicts they arrived
    as, and the page works out the return it displays."""
    try:
        rows = portfolio_holdings.read_every_holding()
    except Exception:                                                 # noqa: BLE001
        return {"has_position": False}
    for h in rows:
        if (h.get("category") == "mutual_fund"
                and (h.get("amfi_code") or "") == amfi_code):
            return {
                "has_position": True,
                "scheme_name": h.get("scheme_name"),
                "units": h.get("units"),
                "invested": h.get("invested"),
                "current": h.get("current"),
            }
    return {"has_position": False}


@app.get(cfg.API_PREFIX + "/investments/fund-analysis/{amfi_code}")
def fund_analysis(amfi_code: str):
    """One fund's full analysis, served from its stored profile.

    This endpoint never fetches the web itself - a browser request that
    blocks for minutes while volunteer APIs crawl is worse than an
    honest "not analysed yet". The daily pull (server start, the
    5-hourly retry, or the refresh button) is what creates profiles.
    """
    profile = analyse_a_fund.read_profile(amfi_code)
    if profile is None:
        return JSONResponse(
            {"ok": False, "amfi_code": amfi_code, "has_data": False,
             "needs_pull": True,
             "note": ("This fund has not been analysed yet. Press "
                      "'pull fund data now' above, wait a moment, and "
                      "open this again.")})
    return {"ok": bool(profile.get("has_data")), **profile,
            "my_investment": _my_position_for(amfi_code)}


@app.get(cfg.API_PREFIX + "/investments/fund-analysis-ledger")
def fund_analysis_ledger():
    """The analysis ledger as written - history across days, for review."""
    rows = analyse_a_fund.read_the_ledger()
    return {
        "has_data": bool(rows),
        "columns": analyse_a_fund.COLUMNS,
        "rows": rows,
        "note": None if rows else ("No fund has been analysed yet - "
                                   "open any fund's analysis once."),
    }


@app.post(cfg.API_PREFIX + "/investments/fund-analysis/refresh")
def refresh_fund_analysis():
    """The daily pull, now. NAV ledger first, then every tracked fund.

    A second call the same day is a no-op that says so - run_if_due's
    state file decides, not hope.
    """
    return run_the_daily_pull.run_if_due()


# =====================================================================
# TAB 6b — THE WHOLE-PORTFOLIO REVIEW
# What a portfolio manager reads: look-through concentration (HHI,
# effective number of stocks, top-10 share), money-weighted asset /
# cap / sector splits, a per-fund scorecard (value, P/L, XIRR, expense,
# behaviour ratios) and threshold-based observations. Served from the
# stored snapshot written by build_the_portfolio_review; rebuilt on
# demand when it is missing, which needs no holdings source.
# =====================================================================
@app.get(cfg.API_PREFIX + "/portfolio-analysis/review")
def portfolio_review():
    stored = build_the_portfolio_review.read_review()
    if stored is not None:
        return {"ok": True, **stored}
    try:
        review = build_the_portfolio_review.build_review()
    except Exception as e:                                            # noqa: BLE001
        return JSONResponse({"ok": False,
                             "note": f"the review could not be built: {e}"},
                            status_code=502)
    return {"ok": bool(review.get("has_data")), **review}


# =====================================================================
# MARKET EXTRAS - IPO calendar, G-Sec yield notes, equity price ledger
# Assembled from Saved_Records files written by the daily pull. This
# endpoint reads local files only and touches no network, so a slow
# external site can never block a page render. A missing or unreadable
# file becomes an honest has_data:false with a note - never a crash,
# never an invented row.
# =====================================================================
def _read_json_file(path):
    """The file's JSON, or None when it is not there / not readable."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except Exception:                                                 # noqa: BLE001
        return None


@app.get(cfg.API_PREFIX + "/market/extras")
def market_extras():
    saved = cfg.SAVED_RECORDS

    # --- IPO calendar (fetch_india_ipo_list writes it via the pull) ---
    ipo_raw = _read_json_file(saved / "ipo_calendar.json")
    if isinstance(ipo_raw, dict):
        meta = ipo_raw.get("_meta") or {}
        ipo_has_rows = bool(ipo_raw.get("open") or ipo_raw.get("upcoming")
                            or ipo_raw.get("closed"))
        # An empty-but-present file says so plainly; the unverified
        # comment belongs next to rows, not in place of them.
        ipo_note = (meta.get("comment") if ipo_has_rows
                    else "The calendar file on record holds no rows - "
                         "the last pull found nothing open or upcoming.")
        ipo_calendar = {
            "has_data": ipo_has_rows,
            "open": ipo_raw.get("open") or [],
            "upcoming": ipo_raw.get("upcoming") or [],
            "closed": ipo_raw.get("closed") or [],
            "verified_by_a_person": bool(meta.get("verified_by_a_person", False)),
            "note": ipo_note,
        }
    else:
        ipo_calendar = {
            "has_data": False, "open": [], "upcoming": [], "closed": [],
            "verified_by_a_person": False,
            "note": ("No IPO calendar on file yet - the daily pull writes "
                     "Saved_Records/ipo_calendar.json."),
        }

    # --- G-Sec yield notes (a future pull product; honest gap today) ---
    gsec_raw = _read_json_file(saved / "gsec_yield_notes.json")
    if isinstance(gsec_raw, dict):
        gsec_notes = {"has_data": bool(gsec_raw.get("has_data", True)), **gsec_raw}
    else:
        gsec_notes = {"has_data": False,
                      "note": "G-Sec yield notes are not built yet."}

    # --- equity price ledger summary (frozen contract v13 columns) ---
    try:
        with open(saved / "equity_price_ledger.csv", newline="",
                  encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            ledger_rows = list(reader)
        equity_price_ledger_summary = {
            "has_data": bool(ledger_rows),
            "columns": reader.fieldnames or [],
            "rows": ledger_rows,
            "how_many": len(ledger_rows),
        }
    except FileNotFoundError:
        equity_price_ledger_summary = {
            "has_data": False, "columns": [], "rows": [], "how_many": 0,
            "note": "No equity price ledger on file yet.",
        }

    return {
        "ok": True,
        "ipo_calendar": ipo_calendar,
        "gsec_notes": gsec_notes,
        "equity_price_ledger_summary": equity_price_ledger_summary,
    }


# =====================================================================
# TAB 6 — PORTFOLIO ANALYSIS
# Overlap between funds, and whole-portfolio concentration. Arithmetic
# only (Tier 0) - no model is ever asked to do this (ADR-056's argument
# for why this is the highest-value screen in Finance).
# =====================================================================
@app.get(cfg.API_PREFIX + "/portfolio-analysis")
def portfolio_analysis():
    # Prefer the snapshot ledger - it is the one that is actually
    # populated - and fall back to the transaction log so this keeps
    # working once someone starts logging individual buys instead.
    snapshot = portfolio_holdings.read_every_holding()
    funds = [{"name": h["scheme_name"], "identifier": h["amfi_code"],
             "amount_invested": h["invested"]}
            for h in snapshot if h["category"] == "mutual_fund" and h["amfi_code"]]
    shares = []

    if not funds:
        logged = read_what_i_own.what_i_hold_now()
        funds = [{"name": h["name"], "identifier": h["identifier"], "amount_invested": h["amount_invested"]}
                for h in logged if h["kind"] == "mutual_fund"]
        shares = [{"name": h["name"], "amount_invested": h["amount_invested"]}
                 for h in logged if h["kind"] == "share"]

    if not funds:
        return {"has_data": False, "note": (
            "There are no mutual funds with a known AMFI code yet - in "
            "Saved_Records/portfolio_holdings.csv or my_investments.csv - so "
            "there is nothing to compare."
        )}

    with_holdings, missing = [], []
    for fund in funds:
        facts = fetch_fund_facts.holdings(fund["identifier"])
        if facts.get("has_data"):
            with_holdings.append({"name": fund["name"], "amount_invested": fund["amount_invested"],
                                  "holdings": facts["holdings"], "as_of": facts.get("as_of", "unknown")})
        else:
            missing.append({"name": fund["name"], "why": facts.get("note", "no portfolio published")})

    if not with_holdings:
        return {"has_data": False, "could_not_get": missing, "note": (
            "No fund's portfolio could be fetched right now, so no overlap "
            "can be shown. A dash is the honest answer, not a zero."
        )}

    concentration = find_the_overlap.look_through_the_whole_portfolio(
        with_holdings,
        [{"stock_name": s["name"], "amount_invested": s["amount_invested"]} for s in shares],
    )

    pairs = []
    for i in range(len(with_holdings)):
        for j in range(i + 1, len(with_holdings)):
            a, b = with_holdings[i], with_holdings[j]
            result = find_the_overlap.overlap_between(a["holdings"], b["holdings"])
            pairs.append({"first_fund": a["name"], "second_fund": b["name"],
                         "overlap_percent": result["overlap_percent"],
                         "shared_stocks": result["shared_stocks"],
                         "in_plain_words": result["in_plain_words"],
                         "as_of": f"{a['as_of']} and {b['as_of']}"})
    pairs.sort(key=lambda r: r["overlap_percent"], reverse=True)

    return {
        "has_data": True,
        "whole_portfolio": concentration,
        "pairs": pairs,
        "could_not_get": missing,
        "how_it_was_worked_out": (
            "Arithmetic over published holdings. No model was asked anything."
        ),
    }


@app.get(cfg.API_PREFIX + "/portfolio-analysis/sectors")
def portfolio_sectors():
    """Money-weighted sector map over every MF whose holdings fetched.

    Sectors come from Reference_Data/sector_for_stocks.json, which is
    hand-curated and NOT yet verified by a person - so the answer says
    so, loudly, rather than presenting a guess as law.
    """
    try:
        snapshot = portfolio_holdings.read_every_holding()
    except portfolio_holdings.TheRecordsAreWrong as e:
        return {"has_data": False, "note": str(e)}
    funds = [{"scheme_name": h["scheme_name"], "amfi_code": h["amfi_code"],
              "value": h["current"] or 0}
             for h in snapshot if h["category"] == "mutual_fund"]
    answer = build_the_sector_map.sector_breakdown(funds)
    if not answer["verified_by_a_person"]:
        answer["unverified_warning"] = (
            "Sector names are matched by a hand-curated reference file "
            "that no person has verified yet - treat every percentage "
            "here as [UNVERIFIED]."
        )
    return answer


@app.get(cfg.API_PREFIX + "/investments/nav-ledger")
def get_nav_ledger():
    """The recorded NAV per fund, each with an honest freshness badge."""
    return track_the_nav_ledger.a_summary_for_the_screen()


@app.post(cfg.API_PREFIX + "/investments/nav-ledger/update")
def update_nav_ledger():
    """Fetch the current NAV for every tracked fund and write it down.

    Talks to mfapi.in, so this is the one investments endpoint that can
    take a few seconds; the page shows a working state while it waits.
    """
    result = track_the_nav_ledger.update_the_ledger()
    summary = track_the_nav_ledger.a_summary_for_the_screen()
    return {**result, **summary}


@app.get(cfg.API_PREFIX + "/investments/xirr")
def investments_xirr():
    """True annualised return per transaction-logged holding."""
    values = compute_the_xirr.snapshot_current_values()
    return compute_the_xirr.per_holding_xirr(latest_values=values)


# =====================================================================
# TAB 7 — DEBT & LIABILITIES
# The existing debt maths, plus the assets/liabilities ledger.
# =====================================================================
@app.get(cfg.API_PREFIX + "/liabilities")
def liabilities():
    assets_and_liabilities.start_the_records_if_missing()
    summary = assets_and_liabilities.a_summary_for_the_screen()
    assets_and_liabilities.publish_to_noticeboard(summary)
    if not summary["has_data"]:
        return summary

    def _row(r):
        return {**r, "monthly_amount": _money(r["monthly_amount"]), "value": _money(r["value"])}

    return {
        **summary,
        "net_worth": {**summary["net_worth"], "value": _money(summary["net_worth"]["value"])},
        "total_assets": _money(summary["total_assets"]),
        "total_liabilities": _money(summary["total_liabilities"]),
        "monthly_recurring_liabilities": _money(summary["monthly_recurring_liabilities"]),
        "debt_split": {
            **summary["debt_split"],
            "borrowed_total": _money(summary["debt_split"]["borrowed_total"]),
            "other_total": _money(summary["debt_split"]["other_total"]),
        },
        "assets": [_row(r) for r in summary["assets"]],
        "liabilities": [_row(r) for r in summary["liabilities"]],
    }


# =====================================================================
# THE ASK STRIPS
# Talks to an OpenAI-compatible model gateway (OmniRoute or similar) over
# HTTP, never by import (C8). The raw chat completion does NOT run the old
# double-agreement/escalation checks (working rule 7) or a per-call
# finance_allowed lookup (working rule 5) - those lived in do_one_task.py.
# What still holds by construction: the model wired in here is fully local
# via llama.cpp - the owner's own private financial figures never leave
# this laptop, which is the strongest form working rule 5 asks for.
# =====================================================================
GATEWAY_URL = "http://127.0.0.1:8003/v1/chat/completions"
GATEWAY_MODEL = "qwen2.5-coder-7b-instruct"


def _strip_thinking(text: str | None) -> str | None:
    """Remove <think>…</think> reasoning blocks a reasoning model leaves
    inside its own answer text. An UNCLOSED think tag is treated the
    same way - everything from the opening tag to the end of the reply
    is scratchpad, and gpt-oss has been observed never closing it."""
    if not text:
        return text
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
    return text.strip()


def _ask_the_router(prompt: str) -> dict:
    """One shared door to the model gateway. Over HTTP, never by import
    (C8). Every Finance question - either "Ask INKY" strip (Investments,
    Portfolio) - goes through here, straight to Model A via the gateway.
    """
    payload = json.dumps({
        "model": GATEWAY_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode("utf-8")

    try:
        request = urllib.request.Request(
            GATEWAY_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as e:
        return {"ok": False, "problem": (
            f"Could not reach the model gateway at {GATEWAY_URL} ({e}). "
            f"Start OmniRoute (or your model gateway), then try again."
        )}

    choice = (result.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content"))
    if text is None:
        return {"ok": False, "problem": f"Gateway answered with no content: {result}"}

    return {
        "ok": True,
        "outcome": "ok",
        # Reasoning models (gpt-oss et al) put their chain of thought in
        # <think> tags inside the answer itself. A person asked a chat
        # question wants the answer, not the scratchpad - stripped here,
        # once, at the door every Finance question comes through.
        "reply": _strip_thinking(text),
        "escalated": False,
        "reason": None,
        "note": None,
    }


@app.post(cfg.API_PREFIX + "/investments/ask")
def investments_ask(body: dict = Body(...)):
    """Ask about YOUR holdings. The question travels with a compact,
    factual snapshot of what this screen already computed - the model
    reasons over it; it does not fetch, guess or invent anything."""
    message = (body.get("message") or "").strip()
    if not message:
        return JSONResponse({"ok": False, "problem": "'message' is required"}, status_code=400)

    lines = ["You are answering questions about the user's own investment holdings."]
    try:
        summary = portfolio_holdings.a_summary_for_the_screen()
        if summary.get("has_data"):
            lines.append(
                f"Snapshot totals: invested Rs {summary['total_invested']}, "
                f"current Rs {summary['total_current']}, P/L Rs {summary['total_pl']} "
                f"across {summary['how_many_holdings']} holdings:")
            for h in summary["holdings"]:
                lines.append(f"- {h['scheme_name']}: invested {h['invested']}, "
                             f"current {h['current']}, {h['pl_pct']}%, units {h['units']}")
        xirr = compute_the_xirr.per_holding_xirr(
            latest_values=compute_the_xirr.snapshot_current_values())
        if xirr.get("has_data"):
            lines.append("Annualised return (XIRR) per fund:")
            for h in xirr["holdings"]:
                lines.append(f"- {h['name']}: {h['xirr_pct']}% a year")
        navs = track_the_nav_ledger.a_summary_for_the_screen()
        if navs.get("has_data"):
            fresh = sum(1 for r in navs["rows"] if r["state"] == "fresh")
            stale = sum(1 for r in navs["rows"] if r["state"] == "stale")
            lines.append(f"NAV ledger: {fresh} fresh, {stale} stale.")
    except Exception as e:                                            # noqa: BLE001
        lines.append(f"(a data section could not be read: {e})")
    lines.append(f"The question: {message}")
    lines.append("Answer in plain text. If something is not in the data above, say so.")
    return _ask_the_router("\n".join(lines))


@app.post(cfg.API_PREFIX + "/portfolio-analysis/ask")
def portfolio_ask(body: dict = Body(...)):
    """Ask about overlap, concentration and sector spread. Same rule as
    the Investments ask: the numbers travel with the question."""
    message = (body.get("message") or "").strip()
    if not message:
        return JSONResponse({"ok": False, "problem": "'message' is required"}, status_code=400)

    lines = ["You are answering questions about the user's mutual-fund portfolio structure."]
    try:
        snapshot = portfolio_holdings.read_every_holding()
        holdings = [h for h in snapshot if h["category"] == "mutual_fund"]
        # A blank current value stays blank - it is never read as zero.
        funds = [{"scheme_name": h["scheme_name"], "amfi_code": h["amfi_code"],
                  "value": h["current"]}
                 for h in holdings if h["current"] is not None]
        without_value = len(holdings) - len(funds)
        sectors = build_the_sector_map.sector_breakdown(funds)
        if sectors.get("funds_used"):
            flagged = " (UNVERIFIED sector map)" if not sectors["verified_by_a_person"] else ""
            lines.append(f"Sector spread, money-weighted{flagged}:")
            if without_value:
                lines.append(f"- {without_value} holding(s) have no recorded "
                             "value yet, so they are left out of that spread")
            for row in sectors["sectors"][:8]:
                lines.append(f"- {row['name']}: {row['percent_of_portfolio']}%")
            lines.append("Top stocks across funds: "
                         + ", ".join(f"{r['name']} ({r['percent_of_portfolio']}%)"
                                     for r in sectors["top_stocks"][:8]))
        analysis = portfolio_analysis()
        if analysis.get("has_data"):
            wp = analysis["whole_portfolio"]
            lines.append(f"Concentration: {wp['companies_you_own']} companies owned, "
                         f"top 10 = {wp['top_ten_percent']}% of everything.")
            for pair in analysis["pairs"][:5]:
                lines.append(f"- Overlap {pair['first_fund']} vs {pair['second_fund']}: "
                             f"{pair['overlap_percent']}% ({pair['in_plain_words']})")
    except Exception as e:                                            # noqa: BLE001
        lines.append(f"(a data section could not be read: {e})")
    lines.append(f"The question: {message}")
    lines.append("Answer in plain text. If something is not in the data above, say so.")
    return _ask_the_router("\n".join(lines))


# =====================================================================
# THE DAILY PULL - when this server wakes up, a missed day closes
# itself. run_if_due() does nothing if today already pulled, so the
# server can start ten times a day and the web pays exactly once.
# Daemon thread: a slow source never delays the page.
#
# And the periodic retry (ADR-075, 2026-08-22): a second daemon thread
# sleeps PULL_INTERVAL_HOURS (5) and re-pulls with force=True, on repeat
# - not anchored to a clock time. mfdata.in is a volunteer service and
# goes down sometimes; retrying every 5 hours means whichever hour it
# comes back, the next attempt is at most 5 hours away, not up to a full
# day. Both threads cost nothing to run - no paid scheduler, no cloud cron.
# =====================================================================
import threading                                                      # noqa: E402

def _pull_todays_fund_data_once() -> None:
    try:
        result = run_the_daily_pull.run_if_due()
        trace("finance", "daily_pull", "fund-analysis",
              detail=f"ran={result['ran']} ok={result.get('analyses_ok')}",
              outcome="ok")
    except Exception as problem:                                      # noqa: BLE001
        trace("finance", "daily_pull", "fund-analysis",
              detail=str(problem)[:200], outcome="fail")


threading.Thread(target=_pull_todays_fund_data_once, daemon=True,
                 name="daily-fund-pull").start()
threading.Thread(target=run_the_daily_pull.run_every_few_hours,
                 daemon=True, name="periodic-fund-pull").start()


# =====================================================================
# STATIC FILES - the look every screen shares
# =====================================================================
if cfg.FONTS_DIR.exists():
    app.mount("/fonts", StaticFiles(directory=cfg.FONTS_DIR), name="fonts")

app.mount("/shared", StaticFiles(directory=cfg.LOOK_AND_FEEL), name="shared")
app.mount("/page", StaticFiles(directory=cfg.PAGE.parent), name="page")


# =====================================================================
# LIVE SSE (Phase 12.2 - strictly additive)
#     GET /api/finance/live streams this screen's own trace-ledger rows
#     as they land. Tails Shared_By_All_Screens/Trace_Ledger/
#     traces_<date>.jsonl via tail_the_trace_ledger.py.
# =====================================================================
from fastapi.responses import StreamingResponse                          # noqa: E402
from Shared_By_All_Screens.tail_the_trace_ledger import (                # noqa: E402
    stream_screen_events,
)


@app.get(cfg.API_PREFIX + "/live")
async def stream_live_events():
    """Server-Sent Events: finance's own traces, as they happen."""
    return StreamingResponse(stream_screen_events("finance"),
                             media_type="text/event-stream")


# =====================================================================
# THE NEXT.JS REBUILD'S STATIC EXPORT (Phase 12.4) - mounted LAST, after
# every API route above (including /live just above) has already been
# registered. A root mount matches before anything registered after it,
# so putting this earlier would 404 every /api/finance/... route the
# moment USE_NEXT_UI goes live - exactly the bug Enhancement's Phase
# 12.4 fork found and fixed. Flag off, or no out/index.html yet, means
# this block never runs and nothing about the screen changes.
# =====================================================================
if getattr(cfg, "USE_NEXT_UI", False):
    _next_dist = getattr(cfg, "NEXT_DIST", None)
    if _next_dist is not None and (_next_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=_next_dist, html=True),
                 name="next_ui")


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)

