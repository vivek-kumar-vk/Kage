"""K-08: the one LLM seam — chain resolution, one attempt per rung, schema
repair, llm_call spine event, no silent model (EV-ROUTE-01..06)."""

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_for_agents as cfg  # noqa: E402
from services import omni  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
SCHEMA = {"type": "object", "required": ["why"],
          "properties": {"why": {"type": "string", "maxLength": 400}}}


def _reply(content):
    return {"choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10}}


@pytest.fixture
def spine_dir(tmp_path, monkeypatch):
    target = tmp_path / "spine"
    target.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(target))
    shutil_target = BACKEND / "routing_default.json"
    (target / "_routing.json").write_text(shutil_target.read_text(encoding="utf-8"),
                                          encoding="utf-8")
    monkeypatch.setattr(cfg, "OMNIROUTE_MODEL", None)
    monkeypatch.setattr(cfg, "GATEWAY_API_KEY", None)
    return target


def _events(spine_dir):
    files = sorted(spine_dir.glob("events_*.jsonl"))
    assert len(files) == 1
    return [json.loads(line)
            for line in files[0].read_text(encoding="utf-8").splitlines()]


def _mock(handler):
    transport = httpx.MockTransport(handler)
    return lambda: httpx.AsyncClient(transport=transport)


def test_ev_route_01_falls_down_the_chain_and_emits_one_event(spine_dir, monkeypatch):
    seen_models = []

    def handler(request):
        body = json.loads(request.content)
        seen_models.append(body["model"])
        if body["model"] == "glm-5.3-flash":
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json=_reply('{"why": "x"}'))

    monkeypatch.setattr(omni, "_make_client", _mock(handler))
    result = await_call(omni.ask_omni_detailed(
        "system", "prompt", response_schema=SCHEMA, agent_id="arbiter_why"))

    assert seen_models == ["glm-5.3-flash", "opencode/glm-5.2"]
    assert result["rung_used"] == "opencode/glm-5.2"
    assert result["object"] == {"why": "x"}
    assert result["degraded"] is True
    assert result["chain"] == ["glm-5.3-flash", "opencode/glm-5.2"]

    events = _events(spine_dir)
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["task_class"] == "narrate"
    assert payload["tier"] == "T1"
    assert payload["rung_used"] == "opencode/glm-5.2"
    assert payload["chain"] == ["glm-5.3-flash", "opencode/glm-5.2"]
    assert payload["schema_valid"] is True
    assert isinstance(payload["latency_ms"], int)
    assert payload["degraded"] is True
    assert payload["unresolved_tokens"] == []


def test_ev_route_02_all_rungs_failing_raises_and_emits_none(spine_dir, monkeypatch):
    def handler(request):
        return httpx.Response(429, json={"error": "rate limited"})

    monkeypatch.setattr(omni, "_make_client", _mock(handler))
    with pytest.raises(omni.OmniError):
        await_call(omni.ask_omni_detailed("system", "prompt"))
    events = _events(spine_dir)
    assert len(events) == 1
    assert events[0]["payload"]["rung_used"] == "none"
    assert events[0]["payload"]["schema_valid"] is False


def test_ev_route_03_disabled_model_arg_raises_before_http(spine_dir, monkeypatch):
    def handler(request):  # must never be reached
        raise AssertionError("HTTP attempted for a disabled model")

    monkeypatch.setattr(omni, "_make_client", _mock(handler))
    with pytest.raises(omni.OmniError):
        await_call(omni.ask_omni_detailed("system", "prompt", model="local-7b"))
    assert _events(spine_dir)[0]["payload"]["rung_used"] == "none"
    assert _events(spine_dir)[0]["payload"]["chain"] == []


def test_ev_route_04_schema_repair_once_then_success(spine_dir, monkeypatch):
    calls = {"n": 0}

    def handler(request):
        body = json.loads(request.content)
        calls["n"] += 1
        if len(body["messages"]) == 2:  # first attempt: prose, no repair message
            return httpx.Response(200, json=_reply("hello"))
        assert body["messages"][-1]["content"].startswith(
            "Return only the JSON object; errors:")
        return httpx.Response(200, json=_reply('{"why": "fixed"}'))

    monkeypatch.setattr(omni, "_make_client", _mock(handler))
    result = await_call(omni.ask_omni_detailed(
        "system", "prompt", response_schema=SCHEMA))
    assert result["object"] == {"why": "fixed"}
    assert calls["n"] == 2
    assert _events(spine_dir)[0]["payload"]["schema_valid"] is True


def test_ev_route_05_no_hardcoded_model_name(spine_dir):
    source = (BACKEND / "services" / "omni.py").read_text(encoding="utf-8")
    assert "gpt-4o-mini" not in source


def test_ev_route_06_request_shape_schema_in_system_only(spine_dir, monkeypatch):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=_reply('{"why": "x"}'))

    monkeypatch.setattr(omni, "_make_client", _mock(handler))
    await_call(omni.ask_omni_detailed("be brief", "why now?",
                                      response_schema=SCHEMA, max_tokens=123))
    body = bodies[0]
    assert body["model"] == "glm-5.3-flash"
    assert body["max_tokens"] == 123
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][0]["content"].startswith("be brief")
    assert "Respond with exactly one JSON object matching this schema:" \
        in body["messages"][0]["content"]
    assert json.dumps(SCHEMA, sort_keys=True, separators=(",", ":")) \
        in body["messages"][0]["content"]
    assert body["messages"][1] == {"role": "user", "content": "why now?"}


def await_call(coroutine):
    import asyncio
    return asyncio.run(coroutine)
