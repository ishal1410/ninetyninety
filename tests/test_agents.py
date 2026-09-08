from ninetyninety.agents import (
    BatchCalls, RowCall, batch_task, line_guidance, rule_is_grounded,
)
from strands.hooks import AfterModelCallEvent, BeforeToolCallEvent

from ninetyninety.ledger import Transaction


def _tx(row, desc, amount):
    return Transaction(date="2025-03-04", description=desc, amount=amount, source_row=row)


def test_line_guidance_tool_returns_irs_text():
    text = line_guidance("13")
    assert "independent contractors" in text
    assert "expense" in text


def test_trace_hooks_count_tool_and_model_calls_per_agent():
    from ninetyninety.agents import TraceHooks

    hooks = TraceHooks()
    agent = type("A", (), {"name": "preparer"})()
    hooks.on_tool(BeforeToolCallEvent(
        agent=agent, selected_tool=None, invocation_state={},
        tool_use={"name": "line_guidance", "input": {"line_number": "13"}, "toolUseId": "t1"}))
    hooks.on_model(AfterModelCallEvent(agent=agent))
    hooks.on_model(AfterModelCallEvent(agent=agent))
    assert hooks.tool_calls == {"preparer": 1}
    assert hooks.model_calls == {"preparer": 2}
    assert hooks.lines_looked_up == {"preparer": ["13"]}
    hooks.reset()
    assert hooks.tool_calls == {} and hooks.model_calls == {}


def test_review_graph_registers_the_same_hooks_on_all_three_agents():
    from ninetyninety.agents import ReviewGraph, TraceHooks

    class Model:
        config = {"model_id": "fake"}
        stateful = False
    graph = ReviewGraph(Model())
    assert isinstance(graph.hooks, TraceHooks)
    for agent in (graph.preparer, graph.reviewer, graph.referee):
        assert any(cb.__self__ is graph.hooks
                   for cb in agent.hooks.get_callbacks_for(BeforeToolCallEvent(
                       agent=agent, selected_tool=None, invocation_state={},
                       tool_use={"name": "x", "input": {}, "toolUseId": "t"})))


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


def test_rule_is_grounded_needs_the_instruction_text_not_just_the_label():
    from ninetyninety.agents import rule_is_grounded
    assert not rule_is_grounded("16", "other expenses line")
    assert not rule_is_grounded("1", "contributions gifts grants line")
    assert rule_is_grounded("16", "insurance, software subscriptions, bank fees, supplies")


def test_they_disagree_is_false_not_a_crash_when_a_node_has_no_agent_results():
    from ninetyninety.agents import _they_disagree

    class Node:
        def get_agent_results(self):
            return []

    class State:
        results = {"preparer": Node(), "reviewer": Node()}
    assert _they_disagree(State()) is False
