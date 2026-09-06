"""K-09: budget gate and cost — spend from the spine files, no-price
refusal, caps in order, honest null cost (EV-BUDGET-01..04)."""

import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_for_agents as cfg  # noqa: E402
from services import omni  # noqa: E402
from Shared_By_All_Screens import spine  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent

PRICES_WITH_GLM = [
    {"model": "glm-5.3-flash", "provider": "zai",
     "usd_per_1k_in": 0.0002, "usd_per_1k_out": 0.0006},
    {"model": "opencode/glm-5.2", "provider": "opencode",
     "usd_per_1k_in": 0.0, "usd_per_1k_out": 0.0},
]
PRICES_WITHOUT_GLM = [PRICES_WITH_GLM[1]]


def _llm_call_line(cost, agent="finance_analyst"):
    ts = datetime.now(spine.IST).replace(hour=10, minute=0, second=0,
                                         microsecond=0).isoformat()
    return json.dumps({
        "v": 1, "id": uuid.uuid4().hex, "ts": ts, "producer": "agents",
        "type": "llm_call", "subject": agent,
        "payload": {"task_class": "narrate", "tier": "T1",
                    "rung_used": "glm-5.3-flash", "chain": ["glm-5.3-flash"],
                    "schema_valid": True, "latency_ms": 500, "degraded": False,
                    "unresolved_tokens": []},
        "model": "glm-5.3-flash", "tokens_in": 1000, "tokens_out": 500,
        "cost_usd": cost, "correlation_id": None,
    }, ensure_ascii=False, separators=(",", ":"))


@pytest.fixture
def spine_dir(tmp_path, monkeypatch):
    target = tmp_path / "spine"
    target.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(target))
    monkeypatch.setattr(cfg, "OMNIROUTE_MODEL", None)
    monkeypatch.setattr(cfg, "GATEWAY_API_KEY", None)
    (target / "_routing.json").write_text(
        (BACKEND / "routing_default.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    return target


def _write_events(spine_dir, count, cost=0.01):
    month = datetime.now(spine.IST).strftime("%Y-%m")
    lines = "\n".join(_llm_call_line(cost) for _ in range(count)) + "\n"
    (spine_dir / f"events_{month}.jsonl").write_text(lines, encoding="utf-8")


def test_ev_budget_01_spend_today_and_day_cap(spine_dir):
    (spine_dir / "_model_prices.json").write_text(
        json.dumps(PRICES_WITH_GLM), encoding="utf-8")
    _write_events(spine_dir, 29)
    spend = omni.spend_today()
    assert spend["cost_usd"] == pytest.approx(0.29)
    assert spend["calls"] == 29
    with pytest.raises(omni.OmniBudgetError, match=r"day cap 0\.3 reached at \d\d:\d\d"):
        omni._budget_check("narrate", "finance_analyst", "glm-5.3-flash", 20000)


def test_ev_budget_02_unpriced_rung_skipped_without_event(spine_dir, monkeypatch):
    (spine_dir / "_model_prices.json").write_text(
        json.dumps(PRICES_WITHOUT_GLM), encoding="utf-8")

    def handler(request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2}})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(omni, "_make_client",
                        lambda: httpx.AsyncClient(transport=transport))
    import asyncio
    result = asyncio.run(omni.ask_omni_detailed("system", "prompt"))

    assert result["rung_used"] == "opencode/glm-5.2"
    assert result["degraded"] is True
    files = sorted(spine_dir.glob("events_*.jsonl"))
    events = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
    assert len(events) == 1  # the skipped rung produced no event
    assert "glm-5.3-flash" in events[0]["payload"]["chain"]
    assert events[0]["payload"]["rung_used"] == "opencode/glm-5.2"


def test_ev_budget_03_cost_from_real_usage(spine_dir):
    (spine_dir / "_model_prices.json").write_text(
        json.dumps(PRICES_WITH_GLM), encoding="utf-8")
    cost = omni._cost_usd("glm-5.3-flash",
                          {"prompt_tokens": 1000, "completion_tokens": 500})
    assert cost == pytest.approx(0.0005)
    assert omni._cost_usd("glm-5.3-flash", None) is None
    assert omni._cost_usd("glm-5.3-flash", {"prompt_tokens": 1}) is None


def test_ev_budget_04_budget_status_degrades_at_cap(spine_dir):
    _write_events(spine_dir, 29)
    status = omni.budget_status()
    assert status["degraded"] is False
    assert status["cap_usd"] == 0.30

    _write_events(spine_dir, 30)
    status = omni.budget_status()
    assert status["degraded"] is True
    assert status["spend_usd"] == pytest.approx(0.30)
    assert status["reason"] and status["reason"].startswith("day cap 0.3 reached at")
