from decimal import Decimal, getcontext
from typing import List, Tuple
from services.db import connect
from services.agents.supervisor import sanitize_for_cloud_llm

def xirr(cashflows: List[Tuple[Decimal, Decimal]]) -> Decimal:
    getcontext().prec = 10

    def net_present_value(rate: Decimal) -> Decimal:
        return sum(amount / (1 + rate) ** (i / 365) for i, amount in cashflows)

    def xirr_newton(cashflows: List[Tuple[Decimal, Decimal]], guess: Decimal) -> Decimal:
        npv = net_present_value(guess)
        if npv == 0:
            return guess
        derivative = sum(i * amount / (1 + guess) ** ((i + 1) / 365) for i, amount in cashflows)
        return guess - npv / derivative

    def xirr_bisection(cashflows: List[Tuple[Decimal, Decimal]], low: Decimal, high: Decimal) -> Decimal:
        while high - low > Decimal('0.00001'):
            mid = (low + high) / Decimal('2')
            if net_present_value(mid) * net_present_value(low) < 0:
                high = mid
            else:
                low = mid
        return low

    low = Decimal('0.0001')
    high = Decimal('0.5')
    guess = Decimal('0.1')

    for _ in range(10):
        guess = xirr_newton(cashflows, guess)
        if abs(net_present_value(guess)) < Decimal('0.00001'):
            return guess

    return xirr_bisection(cashflows, low, high)
