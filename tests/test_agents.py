from ninetyninety.agents import (
    TOOL_CALLS, BatchCalls, RowCall, batch_task, line_guidance, rule_is_grounded,
)
from ninetyninety.ledger import Transaction


def _tx(row, desc, amount):
    return Transaction(date="2025-03-04", description=desc, amount=amount, source_row=row)


def test_line_guidance_tool_returns_irs_text_and_counts_calls():
    before = TOOL_CALLS["line_guidance"]
    text = line_guidance("13")
    assert "independent contractors" in text
    assert "expense" in text
    assert TOOL_CALLS["line_guidance"] == before + 1


def test_line_guidance_tool_rejects_a_line_not_on_the_form():
    assert "No such line" in line_guidance("99")


def test_batch_task_lists_rows_with_direction_and_source_row():
    task = batch_task([_tx(2, "STRIPE PAYOUT", 1250), _tx(3, "RENT", -1450)])
    assert "row 2 | MONEY IN" in task
    assert "row 3 | MONEY OUT" in task
    assert "1450" in task and "-1450" not in task


def test_rule_is_grounded_accepts_a_quote_and_rejects_an_invention():
    assert rule_is_grounded("13", "Payments to people and firms who are not employees")
    assert not rule_is_grounded("13", "Rent paid to the landlord for office space")


def test_batchcalls_schema_round_trips():
    calls = BatchCalls(calls=[RowCall(row=2, line="1", rule="r", why="w", confidence="high")])
    assert calls.calls[0].line == "1"
