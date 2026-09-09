import pytest

from ninetyninety.agents import BatchCalls, RowCall, TraceHooks, Verdict, Verdicts
from ninetyninety.ledger import Transaction
from ninetyninety.prepare import ProviderExhausted, assemble, prepare_ledger, run_graph


@pytest.fixture(autouse=True)
def _forget_exhausted_models():
    from ninetyninety import prepare
    prepare._EXHAUSTED.clear()
    yield
    prepare._EXHAUSTED.clear()


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
            self.hooks = TraceHooks()

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


def test_prepare_ledger_batches_through_one_graph(monkeypatch):
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
    assert [t["provider"] for t in form.trace] == ["gemini:fake-model"] * 2
    assert form.trace[1]["referee_ran"] is True
    assert form.trace[0]["model_calls"] == {} and form.trace[0]["tool_calls_by_node"] == {}


def test_an_exhausted_model_marks_that_batch_and_later_ones_unclassified(monkeypatch):
    """Exhausted = daily cap gone; with no other model id, stop calling it."""
    import ninetyninety.prepare as prepare
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([ProviderExhausted("throttled")], []))
    form = prepare_ledger([tx(2, "X", 5), tx(3, "Y", 7)], model=_FakeModel(), batch_size=1)
    assert [u["source_row"] for u in form.unclassified] == [2, 3]
    assert form.unclassified[1]["error"] == "gemini:fake-model exhausted: throttled"
    assert form.trace[0]["error"] and "seconds" in form.trace[0]
    assert form.totals["line9"] == 0


def test_a_non_transient_error_does_not_discard_finished_batches(monkeypatch):
    import ninetyninety.prepare as prepare
    good = _Result(BatchCalls(calls=[call(2, "1")]), BatchCalls(calls=[call(2, "1")]))
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([good, ValueError("malformed answer")], []))
    form = prepare_ledger([tx(2, "A", 10), tx(3, "B", 10)], model=_FakeModel(), batch_size=1)
    assert form.totals["line9"] == 10
    assert form.unclassified[0]["error"].startswith("gemini:fake-model failed: ValueError")


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
    assert [t["error"] for t in form.trace] == ["gemini:fake-model exhausted: quota"] * 2
    assert form.unclassified[1]["error"] == "gemini:fake-model exhausted: quota"




def test_is_transient_recognises_bedrock_client_errors_by_code():
    from botocore.exceptions import ClientError
    from ninetyninety.prepare import _is_transient

    def err(code, status):
        return ClientError({"Error": {"Code": code, "Message": "x"},
                            "ResponseMetadata": {"HTTPStatusCode": status}}, "ConverseStream")
    for code, status in (("ThrottlingException", 429), ("ServiceUnavailableException", 503),
                         ("InternalServerException", 500), ("ModelNotReadyException", 429)):
        assert _is_transient(err(code, status)), code
    assert not _is_transient(err("ValidationException", 400))
    assert not _is_transient(err("AccessDeniedException", 403))


def test_prepare_ledger_rotates_to_the_next_model_when_one_is_exhausted(monkeypatch):
    import ninetyninety.prepare as prepare
    rows = [tx(2, "A", 10), tx(3, "B", 10)]
    good = _Result(BatchCalls(calls=[call(2, "1"), call(3, "1")]),
                   BatchCalls(calls=[call(2, "1"), call(3, "1")]))
    made = []
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([ProviderExhausted("quota"), good], made))
    monkeypatch.setattr(prepare, "model_ids", lambda: ["m1", "m2"])
    monkeypatch.setattr(prepare, "build_model", lambda mid: type("M", (), {"config": {"model_id": mid}, "__str__": lambda self: mid})())
    form = prepare_ledger(rows, batch_size=2)
    assert made == ["m1", "m2"]
    assert form.totals["line9"] == 20 and form.unclassified == []
    assert form.trace[0]["provider"] == "gemini:m2"


def test_a_non_transient_failure_costs_one_batch_not_the_model(monkeypatch):
    """Batch 1: m1 gives a malformed answer, m2 takes it. Batch 2 goes back to m1."""
    import ninetyninety.prepare as prepare
    good = _Result(BatchCalls(calls=[call(2, "1"), call(3, "1")]),
                   BatchCalls(calls=[call(2, "1"), call(3, "1")]))
    made = []
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([ValueError("malformed"), good, good], made))
    monkeypatch.setattr(prepare, "model_ids", lambda: ["m1", "m2"])
    monkeypatch.setattr(prepare, "build_model",
                        lambda mid: type("M", (), {"config": {"model_id": mid}, "__str__": lambda self: mid})())
    form = prepare_ledger([tx(2, "A", 10), tx(3, "B", 10)], batch_size=1)
    assert made == ["m1", "m2"]
    assert [t["provider"] for t in form.trace] == ["gemini:m2", "gemini:m1"]
    assert form.unclassified == [] and form.totals["line9"] == 20


def test_referee_reason_is_grounding_checked_too():
    form = assemble([(tx(4, "VENMO INSTRUCTOR", -600), call(4, "12"), call(4, "13"))],
                    {4: Verdict(row=4, line="13", reason="Because I said so")})
    assert form.lines["13"].amount == 600
    assert [u["source_row"] for u in form.ungrounded] == [4]
    assert form.ungrounded[0]["rule"] == "Because I said so"


def test_first_call_per_row_wins_over_a_forged_duplicate():
    from ninetyninety.prepare import _calls_by_row
    calls = BatchCalls(calls=[call(4, "13"), call(4, "1")])
    assert _calls_by_row(calls)[4].line == "13"


def test_money_flowing_against_a_referee_line_is_flagged_low_confidence():
    form = assemble([(tx(4, "PAYROLL", -3000), call(4, "1"), call(4, "12"))],
                    {4: Verdict(row=4, line="1", reason="Voluntary transfers where the donor receives nothing")})
    assert form.lines["1"].amount == -3000
    assert [i["source_row"] for i in form.low_confidence] == [4]
    assert "against" in form.low_confidence[0]["note"]


def test_a_404_model_id_is_retired_for_the_run(monkeypatch):
    from ninetyninety import prepare
    made = []

    class Gone(Exception):
        code = 404
    good = _Result(BatchCalls(calls=[call(2, "1")]), BatchCalls(calls=[call(2, "1")]))
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([Gone("NOT_FOUND"), good, good], made))
    monkeypatch.setattr(prepare, "model_ids", lambda: ["dead", "alive"])
    monkeypatch.setattr(prepare, "build_model",
                        lambda mid: type("M", (), {"config": {"model_id": mid}, "__str__": lambda self: mid})())
    form = prepare_ledger([tx(2, "A", 1), tx(3, "B", 1)], batch_size=1)
    assert made == ["dead", "alive"]
    assert [t["provider"] for t in form.trace] == ["gemini:alive", "gemini:alive"]


def test_calls_for_rows_outside_the_batch_are_dropped():
    from ninetyninety.prepare import _calls_by_row
    calls = BatchCalls(calls=[call(4, "1"), call(99, "1")])
    assert set(_calls_by_row(calls, rows={4})) == {4}


def test_ledger_over_max_rows_is_refused_before_any_model_call():
    with pytest.raises(ValueError, match="60"):
        prepare_ledger([tx(i, "X", 1) for i in range(2, 64)], max_rows=60)


def test_exclusive_run_refuses_while_another_draft_holds_the_lock():
    from ninetyninety import prepare
    with prepare.RUN_LOCK:
        with pytest.raises(RuntimeError, match="another draft"):
            prepare_ledger([], exclusive=True)


def test_an_exhausted_model_id_stays_retired_for_later_runs_today(monkeypatch):
    from ninetyninety import prepare
    made = []
    good = _Result(BatchCalls(calls=[call(2, "1")]), BatchCalls(calls=[call(2, "1")]))
    monkeypatch.setattr(prepare, "ReviewGraph",
                        _fake_graph_factory([ProviderExhausted("daily cap"), good, good], made))
    monkeypatch.setattr(prepare, "model_ids", lambda: ["dead", "alive"])
    monkeypatch.setattr(prepare, "build_model",
                        lambda mid: type("M", (), {"config": {"model_id": mid}, "__str__": lambda self: mid})())
    prepare_ledger([tx(2, "A", 1)])
    prepare_ledger([tx(2, "A", 1)])
    assert made == ["dead", "alive", "alive"]


def test_trace_rows_only_suffix_ms_on_node_ms():
    from ninetyninety.prepare import trace_rows
    [row] = trace_rows([{"batch": 1, "rows": 12, "provider": "gemini:x", "nodes": ["preparer", "reviewer"],
                         "referee_ran": False, "tool_calls": 18, "tool_calls_by_node": {"preparer": 9},
                         "model_calls": {"preparer": 4}, "node_ms": {"preparer": 28173.4, "referee": None},
                         "seconds": 212.4}])
    assert row["tool calls by node"] == "preparer 9"
    assert row["model calls"] == "preparer 4"
    assert row["node ms"] == "preparer 28173ms"
    assert row["nodes"] == "preparer, reviewer"
    assert row["seconds"] == 212.4
    assert "tool_calls_by_node" not in row
