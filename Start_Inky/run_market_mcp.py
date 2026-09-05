"""Starts the market-data MCP server — the one tool seam the Agent Deck
research agents (and any MCP client) use for this repo's real portfolio
and market numbers.

WHAT IT RUNS
    A Streamable-HTTP MCP server (official `mcp` SDK) on 127.0.0.1:3101,
    endpoint /mcp. Every tool is a thin proxy onto the finance-os backend
    (127.0.0.1:8002, direct-run port 8002) — the SAME seam the Finance
    tabs read — so agents see exactly what the user sees, honest pending
    states included. Nothing here touches the LLM gateway (omni.py stays
    the one LLM seam, D12.1).

TOOLS
    portfolio_overview          hero numbers, XIRR, value series
    portfolio_section(section)  lookthrough | overlap | behaviour |
                                allocation | cost-tax | actions
    holdings                    the ledger with values and weights
    fund_sheet(holding_id)      one fund's full reference deep-dive
    stock_sheet(symbol)         one stock's sheet
    watchlist / ipo_calendar / global_planner   the Trade Desk segments

IDEMPOTENT
    If something already listens on 3101 this prints that and exits —
    safe to run twice (the run_omniroute.py pattern).

RUN IT
    cd <repo root>
    python Start_Inky\\run_market_mcp.py

    Or double-click Start_Inky\\Start_Everything.bat, which starts this
    in its own window before the screens.
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MCP_HOST = "127.0.0.1"
MCP_PORT = 3101
FINANCE_PORTS = (8002,)          # served port (screen and direct-run share it now)


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((MCP_HOST, port)) == 0


def _finance_base() -> str:
    """The finance-os backend that actually answers, probed once."""
    for port in FINANCE_PORTS:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/finance/health", timeout=3) as r:
                if r.status == 200:
                    return f"http://127.0.0.1:{port}"
        except Exception:  # noqa: BLE001
            continue
    # default to the served port; tools will report the honest failure
    return f"http://127.0.0.1:{FINANCE_PORTS[0]}"


BASE = _finance_base()


def _get(path: str) -> str:
    """One JSON GET against the finance backend. Errors surface as the
    tool result text — an agent reading 'gateway unreachable' is better
    informed than one reading a fabricated number."""
    try:
        with urllib.request.urlopen(f"{BASE}/api/finance{path}", timeout=60) as r:
            return r.read().decode("utf-8")
    except Exception as e:  # noqa: BLE001
        return json.dumps({"state": "pending",
                           "reason": f"finance backend unreachable at {BASE}: {e}"})


def _bound(data, depth: int = 0, max_list: int = 40):
    """Cap list sizes (keeping valid JSON) so one tool call cannot flood
    a context. Trims are marked, never silent."""
    if isinstance(data, list):
        trimmed = [_bound(x, depth + 1, max_list) for x in data[:max_list]]
        if len(data) > max_list:
            trimmed.append({"_truncated": True,
                            "_note": f"{len(data) - max_list} more rows omitted"})
        return trimmed
    if isinstance(data, dict):
        return {k: _bound(v, depth + 1, max_list) for k, v in data.items()}
    return data


def _json(text: str) -> str:
    try:
        data = json.loads(text)
    except ValueError:
        return json.dumps({"state": "pending",
                           "reason": "upstream sent something that was not JSON",
                           "raw_head": text[:400]})
    return json.dumps(_bound(data), ensure_ascii=False, indent=1)


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("inky-market-data", host=MCP_HOST, port=MCP_PORT)

    @mcp.tool()
    def portfolio_overview() -> str:
        """Hero numbers for the user's investment portfolio: total value,
        invested, gain, XIRR, x-ray coverage, and the daily value series."""
        return _json(_get("/analysis/overview"))

    @mcp.tool()
    def portfolio_section(section: str) -> str:
        """One section of the whole-portfolio review. section: lookthrough
        (what companies you really own + HHI), overlap (pair overlap
        matrix), behaviour (risk ratios vs NIFTY 50), allocation (split vs
        targets + drift), cost-tax (blended TER + CG buckets), actions
        (fact-based observations)."""
        allowed = {"lookthrough", "overlap", "behaviour", "allocation",
                   "cost-tax", "actions"}
        if section not in allowed:
            return json.dumps({"error": f"section must be one of {sorted(allowed)}"})
        return _json(_get(f"/analysis/{section}"))

    @mcp.tool()
    def holdings() -> str:
        """Every active holding: units, avg cost, invested, current value,
        gain, weight, plan (direct/regular)."""
        return _json(_get("/investments/holdings"))

    @mcp.tool()
    def fund_sheet(holding_id: int) -> str:
        """Full deep-dive on one mutual-fund holding by its ledger id:
        facts (TER, AUM, managers), published portfolio with weights,
        return buckets, risk ratios, peers, pros/cons."""
        return _json(_get(f"/investments/analyse/{holding_id}"))

    @mcp.tool()
    def stock_sheet(symbol: str) -> str:
        """Full sheet on one stock by NSE symbol: price, 52-week range,
        fundamentals, returns, risk ratios vs NIFTY 50."""
        return _json(_get(f"/investments/analyse/stock/{symbol}"))

    @mcp.tool()
    def watchlist() -> str:
        """The user's stock watchlist with live prices."""
        return _json(_get("/tradedesk/watchlist"))

    @mcp.tool()
    def ipo_calendar() -> str:
        """India's IPO calendar: open now, upcoming, recently closed —
        as published (information, never application advice)."""
        return _json(_get("/tradedesk/ipo"))

    @mcp.tool()
    def global_planner(planned_inr: float = 0) -> str:
        """LRS/TCS math for a planned overseas investment. Pass
        planned_inr (rupees) to get USD equivalent, TCS payable, and the
        LRS headroom check."""
        q = f"?planned_inr={planned_inr}" if planned_inr else ""
        return _json(_get(f"/tradedesk/global{q}"))

    return mcp


def main() -> None:
    if port_in_use(MCP_PORT):
        print(f"  market MCP already running at http://{MCP_HOST}:{MCP_PORT}/mcp"
              " - leaving it alone")
        return
    print(f"  finance backend seam: {BASE}")
    print(f"  market-data MCP -> http://{MCP_HOST}:{MCP_PORT}/mcp"
          "  (Streamable HTTP, official mcp SDK)")
    mcp = build_server()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
