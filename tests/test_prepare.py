import pytest

from ninetyninety.agents import BatchCalls, RowCall, Verdict, Verdicts
from ninetyninety.ledger import Transaction
from ninetyninety.prepare import ProviderExhausted, assemble, prepare_ledger, run_graph


def tx(row, description, amount):
    return Transaction(date="2025-01-01", description=description,
                       amount=amount, source_row=row)


def call(row, line, confidence="high",
         rule="Voluntary transfers where the donor receives nothing of comparable value"):
    return RowCall(row=row, line=line, rule=rule, why="w", confidence=confidence)


def test_agreed_rows_are_summed_onto_their_line():
    form = assemble([(tx(2, "DONATION", 1000), call(2, "1"), call(2, "1")),
                     (tx(3, "DONATION", 250), call(3, "1"), call(3, "1"))], {})
    assert form.lines["1"].amount == 1250
    assert form.totals["line9"] == 1250
    assert form.disagreements == []


def test_expense_rows_are_stored_as_positive_amounts():
    form = assemble([(tx(2, "RENT", -1450), call(2, "14"), call(2, "14"))], {})
    assert form.lines["14"].amount == 1450
    assert form.totals["line17"] == 1450
    assert form.totals["line18"] == -1450


def test_disagreement_with_verdict_uses_referee_line_and_records_all_three():
    form = assemble([(tx(4, "VENMO INSTRUCTOR", -600), call(4, "12"), call(4, "13"))],
                    {4: Verdict(row=4, line="13", reason="not an employee")})
    assert form.lines["13"].amount == 600
    assert "12" not in form.lines
    item = form.disagreements[0]
    assert (item["preparer"], item["reviewer"], item["referee"]) == ("12", "13", "13")
    assert item["referee_reason"] == "not an employee"
    assert item["used"] == "13"


def test_disagreement_without_verdict_uses_preparer_and_says_so():
    form = assemble([(tx(4, "X", -600), call(4, "12"), call(4, "13"))], {})
    assert form.lines["12"].amount == 600
    assert form.disagreements[0]["referee"] is None


def test_single_opinion_rows_are_counted_but_flagged_and_no_answer_is_unclassified():
    form = assemble([(tx(5, "A", 10), None, call(5, "1")),
                     (tx(6, "B", 20), call(6, "1"), None),
                     (tx(7, "C", 30), None, None)], {})
    assert form.lines["1"].amount == 30
    assert {i["source_row"]: i["note"] for i in form.unreviewed} == {
        5: "only the Reviewer answered", 6: "only the Preparer answered"}
    assert form.unclassified[0]["source_row"] == 7


def test_low_confidence_and_refunds_are_flagged():
    form = assemble([(tx(5, "MISC", 40), call(5, "8", "low"), call(5, "8", "low")),
                     (tx(6, "SPONSOR REFUND", -250), call(6, "1"), call(6, "1"))], {})
    assert {i["source_row"] for i in form.low_confidence} == {5, 6}
    assert form.lines["1"].amount == -250


def test_ungrounded_rule_is_flagged_but_row_still_counted():
    form = assemble([(tx(7, "RENT", -1450),
                      call(7, "14", rule="Because I said so"), call(7, "14"))], {})
    assert form.lines["14"].amount == 1450
    assert form.ungrounded[0]["source_row"] == 7


class _Err(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.code = 429


class _Graph:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def run(self, task):
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def test_run_graph_sleeps_the_advertised_delay_then_succeeds():
    slept = []
    graph = _Graph([_Err('429 ... "retryDelay": "7s"'), "ok"])
    assert run_graph(graph, "t", sleep=slept.append) == "ok"
    assert slept == [7.0]


def test_run_graph_gives_up_after_three_rate_limits():
    graph = _Graph([_Err("429"), _Err("429"), _Err("429")])
    with pytest.raises(ProviderExhausted):
        run_graph(graph, "t", sleep=lambda s: None)


def test_run_graph_treats_503_as_transient():
    class _Down(Exception):
        code = 503
    slept = []
    graph = _Graph([_Down("503 Service Unavailable. high demand"), "ok"])
    assert run_graph(graph, "t", sleep=slept.append) == "ok"
    assert slept == [20.0]


def test_run_graph_reraises_other_errors_immediately():
    graph = _Graph([ValueError("boom")])
    with pytest.raises(ValueError):
        run_graph(graph, "t", sleep=lambda s: None)


class _Node:
    def __init__(self, node_id):
        self.node_id = node_id


class _NodeResult:
    execution_time = 5


class _Result:
    """Mimics the parts of strands GraphResult that prepare.py reads."""
    def __init__(self, prep, rev, verdicts=None):
        self.prep, self.rev, self.verd = prep, rev, verdicts
        ids = ["preparer", "reviewer"] + (["referee"] if verdicts else [])
        self.execution_order = [_Node(n) for n in ids]
        self.results = {n: _NodeResult() for n in ids}


def _fake_graph_factory(outcomes, made):
    class FakeReviewGraph:
        def __init__(self, model):
            made.append(model)

        def run(self, task):
            out = outcomes.pop(0)
            if isinstance(out, Exception):
                raise out
            return out

        @staticmethod
        def calls(result, node_id):
            return result.prep if node_id == "preparer" else result.rev

        @staticmethod
        def verdicts(result):
            return result.verd
    return FakeReviewGraph


def test_prepare_ledger_batches_and_fails_over_to_next_provider(monkeypatch):
    import ninetyninety.prepare as prepare
    rows = [tx(i, f"ROW {i}", 10) for i in range(2, 8)]  # 6 rows, batch 4 -> 2 batches
    first = _Result(BatchCalls(calls=[call(i, "1") for i in range(2, 6)]),
                    BatchCalls(calls=[call(i, "1") for i in range(2, 6)]))
    second = _Result(BatchCalls(calls=[call(6, "1"), call(7, "2")]),
                     BatchCalls(calls=[call(6, "1"), call(7, "1")]),
                     Verdicts(verdicts=[Verdict(row=7, line="2", reason="fees")]))
    made = []
    # provider gemini: batch 1 ok, batch 2 exhausted; provider openrouter: batch 2 ok
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([first, ProviderExhausted("gemini"), second], made))
    monkeypatch.setattr(prepare, "build_model", lambda provider: provider)
    form = prepare_ledger(rows, batch_size=4, providers=["gemini", "openrouter"])
    assert made == ["gemini", "openrouter"]
    assert form.totals["line9"] == 60
    assert form.disagreements[0]["referee"] == "2"
    assert [t["provider"] for t in form.trace] == ["gemini", "openrouter"]
    assert form.trace[1]["referee_ran"] is True


def test_prepare_ledger_marks_a_batch_unclassified_when_every_provider_fails(monkeypatch):
    import ninetyninety.prepare as prepare
    made = []
    monkeypatch.setattr(prepare, "ReviewGraph", _fake_graph_factory(
        [ProviderExhausted("a"), ProviderExhausted("b")], made))
    monkeypatch.setattr(prepare, "build_model", lambda provider: provider)
    form = prepare_ledger([tx(2, "X", 5)], providers=["a", "b"])
    assert form.unclassified[0]["source_row"] == 2
    assert "exhausted" in form.unclassified[0]["error"]
