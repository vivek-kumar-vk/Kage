"""Money-weighted annual return (K-16): bracketed bisection on
(ISO date, amount) flows — buys negative, the current value positive.
Floats only; the module never mutates global Decimal precision. Pure."""

from datetime import datetime


def xirr(flows: list[tuple[str, float]]) -> float | None:
    """Annualised percent rounded to 2 dp, or None when the flows are
    empty, carry any unparsable date (the whole call, not the flow), are
    single-signed, or cannot bracket a root in [-0.99, 10.0]."""
    if not flows:
        return None
    days: list[tuple[float, float]] = []
    try:
        t0 = min(datetime.strptime(d, "%Y-%m-%d").date().toordinal() for d, _ in flows)
    except (ValueError, TypeError):
        return None
    for d, amt in flows:
        try:
            t = (datetime.strptime(d, "%Y-%m-%d").date().toordinal() - t0) / 365.0
        except (ValueError, TypeError):
            return None
        days.append((t, float(amt)))
    if not (any(a > 0 for _, a in days) and any(a < 0 for _, a in days)):
        return None

    def pv(rate: float) -> float:
        return sum(amt / ((1.0 + rate) ** t) for t, amt in days)

    lo, hi = -0.99, 10.0
    flo = pv(lo)
    if flo * pv(hi) > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2.0
        fm = pv(mid)
        if abs(fm) < 0.005:
            return round(mid * 100, 2)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return round(((lo + hi) / 2.0) * 100, 2)
