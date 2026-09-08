"""Opt-in live smoke test: NN_LIVE=1 and GOOGLE_API_KEY.

Sends one 4-row batch through the real Strands graph (two blind entry
agents, the line_guidance tool, structured output, conditional referee).
"""
import os

import pytest
from dotenv import load_dotenv

load_dotenv()
pytestmark = pytest.mark.skipif(
    os.environ.get("NN_LIVE") != "1"
    or not os.environ.get("GOOGLE_API_KEY"),
    reason="set NN_LIVE=1 and GOOGLE_API_KEY")


def test_one_batch_through_the_real_graph():
    from ninetyninety.ledger import Transaction
    from ninetyninety.prepare import prepare_ledger

    rows = [Transaction("2025-01-08", "ONLINE DONATION STRIPE PAYOUT BATCH 4471", 1250, 2),
            Transaction("2025-02-03", "ACH PAYROLL ADP RUN 0203", -3120, 6),
            Transaction("2025-02-04", "VENMO J MARTINEZ SAT WORKSHOP INSTRUCTION", -600, 7),
            Transaction("2025-04-09", "ZELLE FROM R PATEL", 500, 40)]
    form = prepare_ledger(rows, batch_size=4)
    assert form.trace and form.trace[0]["provider"]
    assert form.trace[0]["tool_calls"] >= 1
    assert form.totals["line9"] - form.totals["line17"] == form.totals["line18"]
    assert len(form.unclassified) == 0
