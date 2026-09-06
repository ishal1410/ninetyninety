# src/ninetyninety/formmath.py
"""Deterministic Form 990-EZ Part I arithmetic.

No model output ever reaches this module. Totals are computed here and only
here, so the accuracy rate published by the validation harness describes
exactly the same code path that fills a user's form.
"""
from .lines import EXPENSE_LINES, REVENUE_LINES

_REVENUE_NUMBERS = [line.number for line in REVENUE_LINES]
_EXPENSE_NUMBERS = [line.number for line in EXPENSE_LINES]


def total_revenue(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 9 = sum of lines 1 through 8."""
    return sum(int(amounts.get(number, 0)) for number in _REVENUE_NUMBERS)


def total_expenses(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 17 = sum of lines 10 through 16."""
    return sum(int(amounts.get(number, 0)) for number in _EXPENSE_NUMBERS)


def excess_or_deficit(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 18 = line 9 minus line 17."""
    return total_revenue(amounts) - total_expenses(amounts)


def check_identities(amounts: dict[str, int],
                     filed: dict[str, int]) -> dict[str, bool]:
    """Compare our reconstruction against a filed return's own stated totals."""
    return {
        "line9": total_revenue(amounts) == filed.get("line9"),
        "line17": total_expenses(amounts) == filed.get("line17"),
        "line18": excess_or_deficit(amounts) == filed.get("line18"),
    }
