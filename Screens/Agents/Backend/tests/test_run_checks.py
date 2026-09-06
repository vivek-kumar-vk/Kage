"""EV-CHECKS-01: run_checks.py reports SKIP visibly and covers every screen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "Start_Inky"))

import run_checks


def test_missing_tests_dir_is_skip(tmp_path):
    assert run_checks.run_screen_pytest(tmp_path, "ghost pytest") == ("ghost pytest", "SKIP", 0)


def test_summary_prints_three_statuses(capsys):
    run_checks.print_summary([("a", "PASS", 0), ("b", "SKIP", 0), ("c", "FAIL", 1)])
    out = capsys.readouterr().out
    assert "[PASS] a" in out
    assert "[SKIP] b" in out
    assert "[FAIL] c" in out
    assert out.index("[PASS] a") < out.index("[SKIP] b") < out.index("[FAIL] c")


def test_run_checks_covers_every_screen_and_live_gate_paths():
    source = (
        Path(__file__).resolve().parents[4] / "Start_Inky" / "run_checks.py"
    ).read_text(encoding="utf-8")
    assert "Storage" in source
    assert "Finance" in source
    assert "Main_Menu" in source
    assert "check_backend_hygiene.py" in source
    assert ".scratch" not in source
