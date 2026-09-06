"""K-16: one XIRR — bracketed bisection over ISO-date flows (EV-MONEY-01)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from services.calculations.xirr import xirr  # noqa: E402
from services.imports.transactions import compute_xirr  # noqa: E402

_IST = timezone(timedelta(hours=5, minutes=30))


def test_two_flow_loss():
    assert xirr([("2025-01-01", -10000.0), ("2026-01-01", 8000.0)]) == pytest.approx(-20.0, abs=0.1)


def test_two_flow_gain():
    assert xirr([("2025-01-01", -10000.0), ("2026-01-01", 11000.0)]) == pytest.approx(10.0, abs=0.1)


def test_three_flow_mix():
    # The ticket's fixture says 13.1 +/- 0.2, but the true root of
    # -1000 - 1000/(1+r)^(181/365) + 2200/(1+r) = 0 is ~13.44%, which the
    # specified algorithm (days/365, bisection, |pv| < 0.005) converges to.
    assert xirr([("2025-01-01", -1000.0), ("2025-07-01", -1000.0),
                 ("2026-01-01", 2200.0)]) == pytest.approx(13.44, abs=0.2)


def test_none_cases():
    assert xirr([]) is None
    assert xirr([("2025-01-01", -5.0)]) is None
    assert xirr([("bad", -5.0), ("2026-01-01", 6.0)]) is None


def test_compute_xirr_returns_fraction_of_xirr():
    today = datetime.now(_IST).date().isoformat()
    flows = [("2025-01-01", -10000.0), (today, 8000.0)]
    expected = xirr(flows) / 100.0
    assert compute_xirr([{"date": "2025-01-01", "amount": 10000}], 8000.0) \
        == pytest.approx(expected, abs=0.001)
