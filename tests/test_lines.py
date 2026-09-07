from ninetyninety.lines import (
    ALL_LINE_NUMBERS, EXPENSE_LINES, REVENUE_LINES, line_by_number,
)


def test_revenue_has_eight_lines_and_expenses_seven():
    assert len(REVENUE_LINES) == 8
    assert len(EXPENSE_LINES) == 7


def test_element_names_match_live_irs_schema():
    names = {line.xml_element for line in REVENUE_LINES}
    assert "GainOrLossFromSaleOfAssetsAmt" in names
    assert "GrossProfitLossSlsOfInvntryAmt" in names
    assert "NetGainOrLossSaleOfAssetsAmt" not in names


def test_line_by_number_returns_the_right_line():
    assert line_by_number("1").xml_element == "ContributionsGiftsGrantsEtcAmt"
    assert line_by_number("16").kind == "expense"


def test_every_line_carries_guidance_for_the_agents():
    for line in REVENUE_LINES + EXPENSE_LINES:
        assert line.guidance.strip(), f"line {line.number} has no guidance"


def test_all_line_numbers_is_the_union():
    assert ALL_LINE_NUMBERS == {line.number for line in REVENUE_LINES + EXPENSE_LINES}


def test_form_order_keeps_5c_6d_7c_before_the_expense_lines():
    from ninetyninety.lines import form_order
    numbers = ["16", "5c", "1", "10", "6d", "8", "7c"]
    assert sorted(numbers, key=form_order) == ["1", "5c", "6d", "7c", "8", "10", "16"]
