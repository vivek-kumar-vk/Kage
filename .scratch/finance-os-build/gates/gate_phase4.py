"""Phase 4 gate — Debt. /debt/simulate returns sane months/interest saved."""
from _util import must, ok, die, fresh_db, backend_server, get, post
from check_backend_hygiene import check as _be_hygiene
_be_hygiene()

db = fresh_db()
with backend_server(db) as base:
    s, _ = post(base, "/api/finance/import/manual", {
        "entity": "debt", "lender": "HDFC CC", "type": "credit_card",
        "outstanding": 200000, "interest_rate": 42, "emi": 8000, "remaining_months": 40})
    must(s in (200, 201), f"create debt -> {s}")

    s, ov = get(base, "/api/finance/debt/overview")
    must(s == 200, f"/debt/overview -> {s}")

    s, sim = get(base, "/api/finance/debt/payoff-plan")
    must(s == 200, f"/debt/payoff-plan -> {s}")

    s, sim = post(base, "/api/finance/debt/simulate",
                  {"extra_payment": 5000, "salary_increase": 0, "bonus": 0})
    must(s == 200, f"/debt/simulate -> {s}: {sim}")
    ms = sim.get("months_saved", sim.get("monthsSaved"))
    isv = sim.get("interest_saved", sim.get("interestSaved"))
    must(ms is not None and 0 <= float(ms) <= 40, f"months_saved sane: {ms}")
    must(isv is not None and float(isv) >= 0, f"interest_saved sane: {isv}")

    s, sim0 = post(base, "/api/finance/debt/simulate",
                   {"extra_payment": 0, "salary_increase": 0, "bonus": 0})
    must(s == 200 and float(sim0.get("months_saved", sim0.get("monthsSaved", 0))) == 0,
         "zero extra payment => zero months saved")

ok("phase 4 debt")
