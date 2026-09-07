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


class _FakeModel:
    config = {"model_id": "fake-model"}

    def __str__(self):
        return "fake"


def _fake_graph_factory(outcomes, made):
    class FakeReviewGraph:
        def __init__(self, model):
            made.append(str(model))

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


def test_prepare_ledger_batches_through_one_bedrock_graph(monkeypatch):
    import ninetyninety.prepare as prepare
    rows = [tx(i, f"ROW {i}", 10) for i in range(2, 8)]  # 6 rows, batch 4 -> 2 batches
    first = _Result(BatchCalls(calls=[call(i, "1") for i in range(2, 6)]),
                    BatchCalls(calls=[call(i, "1") for i in range(2, 6)]))
    second = _Result(BatchCalls(calls=[call(6, "1"), call(7, "2")]),
                     BatchCalls(calls=[call(6, "1"), call(7, "1")]),
                     Verdicts(verdicts=[Verdict(row=7, line="2", reason="fees")]))
    made = []
    monkeypatch.setattr(prepare, "ReviewGraph", _fake_graph_factory([first, second], made))
    form = prepare_ledger(rows, model=_FakeModel(), batch_size=4)
    assert made == ["fake"]  # one graph, reused for every batch
    assert form.totals["line9"] == 60
    assert form.disagreements[0]["referee"] == "2"
    assert [t["provider"] for t in form.trace] == ["bedrock:fake-model"] * 2
    assert form.trace[1]["referee_ran"] is True


def test_an_exhausted_batch_is_unclassified_with_the_error_and_the_run_continues(monkeypatch):
    import ninetyninety.prepare as prepare
    good = _Result(BatchCalls(calls=[call(3, "1")]), BatchCalls(calls=[call(3, "1")]))
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([ProviderExhausted("throttled"), good], []))
    form = prepare_ledger([tx(2, "X", 5), tx(3, "Y", 7)], model=_FakeModel(), batch_size=1)
    assert form.unclassified[0]["source_row"] == 2
    assert form.unclassified[0]["error"] == "bedrock:fake-model exhausted: throttled"
    assert form.trace[0]["error"] and "seconds" in form.trace[0]
    assert form.totals["line9"] == 7  # batch 2 still classified


def test_a_non_transient_error_does_not_discard_finished_batches(monkeypatch):
    import ninetyninety.prepare as prepare
    good = _Result(BatchCalls(calls=[call(2, "1")]), BatchCalls(calls=[call(2, "1")]))
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([good, ValueError("malformed answer")], []))
    form = prepare_ledger([tx(2, "A", 10), tx(3, "B", 10)], model=_FakeModel(), batch_size=1)
    assert form.totals["line9"] == 10
    assert form.unclassified[0]["error"].startswith("bedrock:fake-model failed: ValueError")


def test_referee_may_only_pick_one_of_the_two_disputed_lines():
    verdict = Verdict(row=2, line="8", reason="neither")
    form = assemble([(tx(2, "GALA SPONSOR", 500), call(2, "1"), call(2, "6d"))], {2: verdict})
    assert form.disagreements[0]["referee"] is None
    assert form.disagreements[0]["used"] == "1"
    assert "8" not in form.lines


# --- code-review fixes (2026-09-07) ---

def test_off_menu_line_from_both_agents_is_reported_not_called_no_answer():
    form = assemble([(tx(2, "X", 10), call(2, "9"), call(2, "9"))], {})
    assert form.unclassified[0]["error"] == "line 9 is not on Form 990-EZ Part I"


def test_off_menu_line_versus_valid_line_is_a_disagreement_using_the_valid_line():
    form = assemble([(tx(2, "X", 10), call(2, "9"), call(2, "1"))], {})
    assert form.disagreements[0]["preparer"] == "9"
    assert form.disagreements[0]["used"] == "1"
    assert form.unreviewed == [] and form.unclassified == []
    assert form.lines["1"].amount == 10


def test_is_transient_ignores_status_like_numbers_inside_validation_errors():
    from ninetyninety.prepare import _is_transient
    assert not _is_transient(ValueError("1 validation error: input_value=500 is not a str"))
    assert not _is_transient(ValueError("amount $503 rejected"))
    assert _is_transient(RuntimeError("429 RESOURCE_EXHAUSTED. retryDelay: 20s"))
    assert _is_transient(RuntimeError("Error code: 503 - {'error': 'overloaded'}"))


def test_is_transient_recognises_throttling_exception_classes():
    from ninetyninety.prepare import _is_transient

    class ModelThrottledException(Exception):
        pass
    assert _is_transient(ModelThrottledException("An error occurred (ThrottlingException)"))


def test_every_batch_failing_reports_each_error(monkeypatch):
    import ninetyninety.prepare as prepare
    monkeypatch.setattr(prepare, "ReviewGraph", _fake_graph_factory(
        [ProviderExhausted("quota"), ProviderExhausted("quota")], []))
    form = prepare_ledger([tx(2, "A", 1), tx(3, "B", 1)], model=_FakeModel(), batch_size=1)
    assert [t["error"] for t in form.trace] == ["bedrock:fake-model exhausted: quota"] * 2
    assert form.unclassified[1]["error"] == "bedrock:fake-model exhausted: quota"


