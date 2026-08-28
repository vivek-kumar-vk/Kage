"""Tools for finding real material online. No API key, no signup -
same keyless-first rule as fetch_fund_facts.py's mfapi.in/mfdata.in:
a paid key is added later, deliberately, if a free tier stops being
enough, never assumed up front.

Importing this module registers its tools - nothing else is needed.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent           # Shared_By_All_Agents/Tools
sys.path.insert(0, str(HERE))

from the_tool_registry import a_tool                                  # noqa: E402

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 20.0


@a_tool(
    name="search_the_web",
    what_it_does="Searches the public web for a query and returns real results with URLs - no key needed.",
    gives_back="has_data, results (title, url, snippet), and where_from.",
)
def search_the_web(project_root, query, most_results=8):
    """Tavily's keyless mode: no account, no key, rate-limited for
    light use. If it stops answering, an actual Tavily key would go in
    Secrets_Keys/my_api_keys_and_passwords.md the same way every other
    provider's does - this function does not change, only whether a
    key gets attached to the request.
    """
    body = json.dumps({
        "query": query, "max_results": max(1, min(int(most_results), 20)),
    }).encode("utf-8")
    request = urllib.request.Request(
        TAVILY_SEARCH_URL, data=body,
        headers={"Content-Type": "application/json",
                "X-Tavily-Access-Mode": "keyless"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"has_data": False, "note": f"the search answered HTTP {e.code} "
               "- keyless mode may be rate-limited right now", "where_from": "tavily"}
    except Exception as e:                                            # noqa: BLE001
        return {"has_data": False, "note": f"could not reach the search service: {e}",
               "where_from": "tavily"}

    results = [
        {"title": r.get("title", ""), "url": r.get("url", ""),
         "snippet": (r.get("content") or "")[:500]}
        for r in (data.get("results") or [])
        if r.get("url")
    ]
    return {"has_data": bool(results), "results": results, "where_from": "tavily",
           "note": None if results else "the search answered but found nothing"}


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: the_research_tools.py <search query>")
        return
    result = search_the_web(None, " ".join(sys.argv[1:]))
    print("WEB SEARCH")
    print()
    if not result["has_data"]:
        print(f"  {result['note']}")
        return
    for r in result["results"]:
        print(f"  {r['title']}")
        print(f"    {r['url']}")
        print(f"    {r['snippet'][:120]}")
        print()


if __name__ == "__main__":
    main()
