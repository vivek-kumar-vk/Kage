"""B-03: structure-docs router — never state, regenerate, three reads."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    import server_for_storage  # noqa: F401
    from services import structure

    monkeypatch.setattr(structure, "_STRUCTURE_DIR", tmp_path / "structure")
    return TestClient(server_for_storage.app)


def test_missing_file_is_never_not_empty(client):
    r = client.get("/api/storage/structure/code")
    assert r.status_code == 200
    assert r.json() == {"state": "never", "problem": "not generated yet"}


def test_regenerate_then_all_three_docs_read(client):
    r = client.post("/api/storage/structure/regenerate")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "ok"
    assert body["generated_at"] and isinstance(body["seconds"], (int, float))

    for path in ("code", "agents", "data"):
        doc = client.get(f"/api/storage/structure/{path}").json()
        assert doc["generator_version"] == 1
        assert doc["generated_at"].endswith("+05:30")
