"""B-02: the demo generator is gone — the stage feed has real producers only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_demo_generator_surface_is_gone():
    import services.events as events

    for name in (
        "start_demo",
        "stop_demo",
        "_demo_loop",
        "_demo_burst",
        "_demo_roster",
        "DEMO_ACTIONS",
    ):
        assert not hasattr(events, name), f"demo machinery still present: events.{name}"


def test_server_no_longer_schedules_demo():
    server_src = (
        Path(__file__).resolve().parent.parent / "server_for_agents.py"
    ).read_text(encoding="utf-8")
    assert "start_demo" not in server_src
    assert "stop_demo" not in server_src
