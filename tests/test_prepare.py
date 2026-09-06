from ninetyninety.agents import Classification
from ninetyninety.ledger import Transaction
from ninetyninety.prepare import assemble


def tx(row, description, amount):
    return Transaction(date="2025-01-01", description=description,
                       amount=amount, source_row=row)


def cls(row, line, confidence="high"):
    return Classification(source_row=row, line_number=line, rationale="r",
                          rule="rule", confidence=confidence)


def test_agreed_rows_are_summed_onto_their_line():
    form = assemble([
        (tx(2, "DONATION", 1000), cls(2, "1"), cls(2, "1")),
        (tx(3, "DONATION", 250), cls(3, "1"), cls(3, "1")),
    ])
    assert form.lines["1"].amount == 1250
    assert form.totals["line9"] == 1250


def test_expense_rows_are_stored_as_positive_amounts():
    form = assemble([(tx(2, "RENT", -1450), cls(2, "14"), cls(2, "14"))])
    assert form.lines["14"].amount == 1450
    assert form.totals["line17"] == 1450
    assert form.totals["line18"] == -1450


def test_disagreement_uses_preparer_and_is_recorded():
    form = assemble([(tx(4, "VENMO INSTRUCTOR", -600),
                      cls(4, "13"), cls(4, "12"))])
    assert form.lines["13"].amount == 600
    assert form.disagreements[0]["source_row"] == 4
    assert form.disagreements[0]["preparer"] == "13"
    assert form.disagreements[0]["reviewer"] == "12"


def test_low_confidence_rows_are_flagged_even_when_agreed():
    form = assemble([(tx(5, "MISC", 40), cls(5, "8", "low"), cls(5, "8", "low"))])
    assert form.low_confidence[0]["source_row"] == 5
    assert form.disagreements == []


def test_every_line_keeps_its_citing_transactions():
    form = assemble([(tx(9, "STRIPE PAYOUT", 1250), cls(9, "1"), cls(9, "1"))])
    citation = form.lines["1"].transactions[0]
    assert citation["source_row"] == 9
    assert citation["description"] == "STRIPE PAYOUT"
    assert citation["rule"] == "rule"


def test_refund_on_a_revenue_line_nets_and_is_flagged():
    form = assemble([
        (tx(2, "DONATION", 1000), cls(2, "1"), cls(2, "1")),
        (tx(3, "SPONSOR REFUND", -250), cls(3, "1"), cls(3, "1")),
    ])
    assert form.lines["1"].amount == 750
    assert form.totals["line9"] == 750
    assert form.low_confidence[0]["source_row"] == 3
    assert "refund" in form.low_confidence[0]["note"]


def test_money_in_on_an_expense_line_reduces_that_expense():
    form = assemble([
        (tx(2, "RENT", -1450), cls(2, "14"), cls(2, "14")),
        (tx(3, "RENT DEPOSIT REFUND", 1450), cls(3, "14"), cls(3, "14")),
    ])
    assert form.lines["14"].amount == 0
    assert form.totals["line17"] == 0


def test_prepare_ledger_records_reviewer_silence_as_unreviewed(monkeypatch):
    import ninetyninety.prepare as prepare

    class Fake:
        def __init__(self, reply):
            self.reply = reply
            self.messages = []

        def __call__(self, question):
            return self.reply

    monkeypatch.setattr(prepare, "build_preparer",
                        lambda model: Fake("LINE: 1\nRULE: r\nWHY: w\nCONFIDENCE: high"))
    monkeypatch.setattr(prepare, "build_reviewer", lambda model: Fake("no idea"))
    form = prepare.prepare_ledger([tx(2, "DONATION", 100)], model=None)
    assert form.lines["1"].amount == 100
    assert form.disagreements == []
    assert form.unreviewed[0]["source_row"] == 2
