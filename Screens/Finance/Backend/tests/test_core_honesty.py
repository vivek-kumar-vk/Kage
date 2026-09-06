"""K-17: finance honesty — NULL is None, unpriced excluded, no advice
verbs, reads never fetch (EV-MONEY-02, EV-MONEY-03, EV-MONEY-05)."""

import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from services.calculations import core  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
SCHEMA = BACKEND / "app" / "scripts" / "schema.sql"
BANNED = re.compile(r"\b(pay|buy|sell|switch|raise|rebalance)\b", re.IGNORECASE)


@pytest.fixture
def conn(tmp_path):
    db = sqlite3.connect(tmp_path / "finance.db")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    db.execute("INSERT INTO accounts (name, type) VALUES ('Test', 'broking')")
    account_id = db.execute("SELECT id FROM accounts").fetchone()[0]
    db.execute(
        "INSERT INTO holdings (account_id, symbol, name, type, units, avg_cost) "
        "VALUES (?, 'A', 'Fund A', 'mutual_fund', 10, 100)", (account_id,))
    db.execute(
        "INSERT INTO holdings (account_id, symbol, name, type, units, avg_cost) "
        "VALUES (?, 'B', 'Fund B', 'mutual_fund', 5, 200)", (account_id,))
    db.execute(
        "INSERT INTO price_history (symbol, date, price, source, currency) "
        "VALUES ('A', '2026-09-01', 120.0, 'mfapi', 'INR')")
    db.execute(
        "INSERT INTO debts (lender, type, outstanding, interest_rate, emi, status) "
        "VALUES ('HDFC', 'credit_card', 50000, 36, 5000, 'active')")
    db.commit()
    yield db
    db.close()


def test_ev_money_02_unpriced_excluded_and_listed(conn):
    nw = core.net_worth(conn)
    assert nw["assets"] == 1200.0  # A only: 10 units x 120
    assert nw["unpriced"] == ["B"]
    pulse = core.portfolio_pulse(conn)
    assert pulse["unpriced"] == ["B"]
    assert pulse["total_value"] == 1200.0


def test_ev_money_03_no_salary_is_none_not_zero(conn):
    # salary table is empty
    allocation = core.surplus_allocation(conn)
    assert allocation["surplus"] is None
    assert allocation["allocation"] == []
    assert allocation["note"] == "no salary recorded"
    assert core.emergency_fund(conn)["eta_date"] is None
    assert core.net_worth(conn)["projection"] == []


def test_ev_money_05_observations_are_facts_not_advice(conn):
    result = core.top_actions(conn)
    observations = result["observations"]
    by_flag = {o["flag"]: o for o in observations}
    assert by_flag["debt_apr"]["severity"] == "flag"
    assert by_flag["debt_apr"]["detail"] == "HDFC at 36% APR (threshold 20%)"
    for observation in observations:
        assert not BANNED.search(observation["detail"])
    assert "title" not in observations[0] and "urgent" not in observations[0]


def test_scalar_absent_is_none(conn):
    assert core._scalar(conn, "SELECT monthly_net FROM salary LIMIT 1") is None
    assert core._scalar(conn, "SELECT SUM(amount) FROM transactions") is None
