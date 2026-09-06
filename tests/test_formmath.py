# tests/test_formmath.py
from ninetyninety.formmath import (
    check_identities, excess_or_deficit, total_expenses, total_revenue,
)


def test_total_revenue_sums_lines_1_to_8():
    assert total_revenue({"1": 33456, "4": 9, "6d": 3495}) == 36960


def test_totals_ignore_the_other_side_of_the_form():
    amounts = {"1": 1000, "12": 500}
    assert total_revenue(amounts) == 1000
    assert total_expenses(amounts) == 500


def test_negative_net_lines_are_allowed():
    assert total_revenue({"1": 5000, "7c": -800}) == 4200


def test_missing_lines_count_as_zero():
    assert total_revenue({}) == 0
    assert total_expenses({}) == 0


def test_excess_or_deficit_is_revenue_minus_expenses():
    assert excess_or_deficit({"1": 10000, "12": 4000}) == 6000


def test_check_identities_reports_each_line_separately():
    result = check_identities({"1": 100, "12": 40},
                              {"line9": 100, "line17": 40, "line18": 60})
    assert result == {"line9": True, "line17": True, "line18": True}


def test_check_identities_flags_only_the_wrong_one():
    result = check_identities({"1": 100, "12": 40},
                              {"line9": 100, "line17": 40, "line18": 59})
    assert result["line18"] is False
    assert result["line9"] is True
