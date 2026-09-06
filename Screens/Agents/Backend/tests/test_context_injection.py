"""Context injection (2026-09-06, ARCHITECTURE §4.1): office.json
`data_sources` — loopback-only, few — fetched and inlined by the ask path.
Offline: the real validators and block builder; no live fleet needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services import office  # noqa: E402
from services.agents import MAX_SOURCE_CHARS, _current_data_block, _fetch_source  # noqa: E402


def _agent_with_sources(urls):
    return {"name": "T", "data_sources": urls}


def test_data_sources_valid_loopback_list_passes():
    assert office._clean_data_sources(
        ["http://127.0.0.1:8004/api/agents/context-engine/latest"]
    ) == ["http://127.0.0.1:8004/api/agents/context-engine/latest"]


def test_data_sources_offbox_url_is_dropped_wholesale():
    # One off-box URL poisons the list — nothing partial is fetched.
    assert office._clean_data_sources(
        ["http://127.0.0.1:8009/api/storage/status", "https://example.com/x"]
    ) is None


def test_data_sources_too_many_or_dupes_or_nonstring_dropped():
    four = [f"http://127.0.0.1:{p}/x" for p in (8001, 8002, 8003, 8009)]
    assert office._clean_data_sources(four + ["http://127.0.0.1:8000/x"]) is None
    assert office._clean_data_sources(four[:2] + [four[0]]) is None
    assert office._clean_data_sources([1]) is None
    assert office._clean_data_sources([]) is None


def test_read_office_roundtrip(tmp_path):
    import json

    (tmp_path / "office.json").write_text(
        json.dumps(
            {
                "department": "deck",
                "tier": "sub",
                "data_sources": ["http://localhost:8004/api/agents/context-engine/latest"],
            }
        ),
        encoding="utf-8",
    )
    meta = office.read_office(tmp_path)
    assert meta["data_sources"] == [
        "http://localhost:8004/api/agents/context-engine/latest"
    ]
    # and a dir with no office.json at all stays clean
    assert office.read_office(tmp_path / "nope")["data_sources"] is None


def test_fetch_source_unreachable_is_honest_not_raised():
    body = _fetch_source("http://127.0.0.1:1/nope")  # nothing listens on port 1
    assert body.startswith("[state: unreachable")
    assert "ConnectionRefused" in body or "refused" in body.lower()


async def test_current_data_block_absent_when_no_sources():
    assert await _current_data_block({"name": "T"}) == ""


async def test_current_data_block_inlines_fetched(monkeypatch):
    def fake_fetch(url):
        return f"body-of-{url}"

    monkeypatch.setattr(
        sys.modules["services.agents"], "_fetch_source", fake_fetch
    )
    agent = _agent_with_sources(
        ["http://127.0.0.1:8004/a", "http://127.0.0.1:8009/b"]
    )
    block = await _current_data_block(agent)
    assert "Current data, fetched at" in block
    assert "### http://127.0.0.1:8004/a" in block
    assert "body-of-http://127.0.0.1:8009/b" in block


async def test_current_data_block_truncates_oversized(monkeypatch):
    monkeypatch.setattr(
        sys.modules["services.agents"], "_fetch_source", lambda url: "x" * 99999
    )
    block = await _current_data_block(_agent_with_sources(["http://127.0.0.1:9/x"]))
    assert f"truncated at {MAX_SOURCE_CHARS} chars" in block
    assert len(block) < 99999
