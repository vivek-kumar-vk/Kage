"""K-10: sanitisation inside the seam (EV-SAN-01..06)."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_for_agents as cfg  # noqa: E402
from Shared_By_All_Screens import sanitize  # noqa: E402
from services import omni  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def spine_dir(tmp_path, monkeypatch):
    target = tmp_path / "spine"
    target.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(target))
    monkeypatch.setattr(cfg, "OMNIROUTE_MODEL", None)
    monkeypatch.setattr(cfg, "GATEWAY_API_KEY", None)
    return target


def test_ev_san_01_patterns_and_order():
    out, mapping_id = sanitize.sanitize("PAN ABCDE1234F, phone 9876543210, mail a@b.co")
    assert out == "PAN [[PAN_1]], phone [[PHONE_1]], mail [[EMAIL_1]]"
    mapping = sanitize.load_mapping(mapping_id)
    assert mapping["[[PAN_1]]"] == "ABCDE1234F"


def test_ev_san_02_names_longest_first_case_insensitive():
    out, mapping_id = sanitize.sanitize(
        "vivek said hi to Vivek Kumar Jha",
        names=["Vivek Kumar Jha", "Vivek"])
    assert out == "[[NAME_2]] said hi to [[NAME_1]]"


def test_ev_san_03_amounts_and_dates_untouched():
    out, _ = sanitize.sanitize("₹1,23,456.78 on 2026-09-07 folio 12345678/12")
    assert out == "₹1,23,456.78 on 2026-09-07 folio [[FOLIO_1]]"


def test_ev_san_04_same_original_same_token_and_extension():
    out1, mapping_id = sanitize.sanitize("PAN ABCDE1234F again ABCDE1234F")
    assert out1 == "PAN [[PAN_1]] again [[PAN_1]]"
    out2, _ = sanitize.sanitize("PAN ABCDE1234F once more", mapping_id=mapping_id)
    assert out2 == "PAN [[PAN_1]] once more"
    out3, _ = sanitize.sanitize("mail a@b.co", mapping_id=mapping_id)
    assert out3 == "mail [[EMAIL_1]]"


def test_ev_san_05_unknown_tokens_stay_and_are_listed():
    out, unresolved = sanitize.desanitize(
        "ok [[PAN_7]] and [[pan_1]]", _with_mapping())
    assert out == "ok [[PAN_7]] and [[pan_1]]"
    assert unresolved == ["[[PAN_7]]", "[[pan_1]]"]


def test_tokens_are_never_rematched():
    out, _ = sanitize.sanitize("[[ACCT_1]]")
    assert out == "[[ACCT_1]]"


def test_ev_san_06_pan_never_leaves_the_box_and_reply_is_restored(spine_dir, monkeypatch):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "noted [[PAN_1]]"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3}})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(omni, "_make_client",
                        lambda: httpx.AsyncClient(transport=transport))
    result = asyncio.run(
        omni.ask_omni_detailed("system", "my PAN is ABCDE1234F", agent_id="adhoc"))

    sent = json.dumps(bodies[0], ensure_ascii=False)
    assert "ABCDE1234F" not in sent
    assert "[[PAN_1]]" in sent
    assert "ABCDE1234F" in result["text"]  # restored for the caller
    files = sorted(spine_dir.glob("events_*.jsonl"))
    event = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert event["payload"]["unresolved_tokens"] == []


def _with_mapping():
    mapping_id = "test-mapping"
    sanitize.store_mapping(mapping_id, {"[[PAN_1]]": "ABCDE1234F"})
    return mapping_id
