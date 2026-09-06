"""Turn a classified ledger into a Form 990-EZ Part I.

`assemble` is pure and deterministic. Totals come from formmath, never from a
model. Where the two agents disagree the Preparer's line is used and the row
is surfaced for a human to resolve.
"""
from dataclasses import dataclass, field

from .agents import (
    Classification, build_preparer, build_reviewer, parse_classification,
)
from .formmath import excess_or_deficit, total_expenses, total_revenue
from .ledger import Transaction
from .lines import line_by_number


@dataclass
class LineResult:
    line_number: str
    amount: int = 0
    transactions: list[dict] = field(default_factory=list)


@dataclass
class Form990EZ:
    lines: dict[str, LineResult] = field(default_factory=dict)
    totals: dict[str, int] = field(default_factory=dict)
    disagreements: list[dict] = field(default_factory=list)
    low_confidence: list[dict] = field(default_factory=list)
    unclassified: list[dict] = field(default_factory=list)
    unreviewed: list[dict] = field(default_factory=list)


def assemble(
    rows: list[tuple[Transaction, Classification, Classification]],
) -> Form990EZ:
    form = Form990EZ()
    for transaction, preparer, reviewer in rows:
        chosen = preparer.line_number
        result = form.lines.setdefault(chosen, LineResult(chosen))
        # Revenue lines carry money-in as positive; expense lines carry
        # money-out as positive. A refund therefore NETS against its line
        # instead of being added to it, and is flagged below.
        revenue = line_by_number(chosen).kind == "revenue"
        signed = transaction.amount if revenue else -transaction.amount
        result.amount += signed
        result.transactions.append({
            "source_row": transaction.source_row,
            "date": transaction.date,
            "description": transaction.description,
            "amount": transaction.amount,
            "rule": preparer.rule,
            "why": preparer.rationale,
        })
        if reviewer.line_number != chosen:
            form.disagreements.append({
                "source_row": transaction.source_row,
                "description": transaction.description,
                "preparer": chosen,
                "preparer_rule": preparer.rule,
                "reviewer": reviewer.line_number,
                "reviewer_rule": reviewer.rule,
            })
        elif "low" in (preparer.confidence, reviewer.confidence) or signed < 0:
            form.low_confidence.append({
                "source_row": transaction.source_row,
                "description": transaction.description,
                "line": chosen,
                "note": ("money flows against this line; netted as a refund"
                         if signed < 0 else "low confidence"),
            })

    amounts = {number: result.amount for number, result in form.lines.items()}
    form.totals = {
        "line9": total_revenue(amounts),
        "line17": total_expenses(amounts),
        "line18": excess_or_deficit(amounts),
    }
    return form


def _ask(agent, transaction: Transaction) -> Classification | None:
    agent.messages = []  # each transaction is judged alone, no carry-over
    direction = "MONEY IN" if transaction.amount >= 0 else "MONEY OUT"
    question = (f"{direction}\nDATE: {transaction.date}\n"
                f"DESCRIPTION: {transaction.description}\n"
                f"AMOUNT: {abs(transaction.amount)}")
    return parse_classification(str(agent(question)), transaction.source_row)


def prepare_ledger(transactions: list[Transaction], model,
                   progress=None) -> Form990EZ:
    """Classify every transaction with both agents, then assemble.

    `progress(done, total)` is called after each transaction if given.
    Rows the Preparer cannot classify are kept on `form.unclassified` so
    nothing silently vanishes from the ledger.
    """
    preparer, reviewer = build_preparer(model), build_reviewer(model)
    rows = []
    skipped = []
    unreviewed = []
    for index, transaction in enumerate(transactions, start=1):
        first = _ask(preparer, transaction)
        if first is None:
            skipped.append({"source_row": transaction.source_row,
                            "description": transaction.description,
                            "amount": transaction.amount})
        else:
            second = _ask(reviewer, transaction)
            if second is None:
                # Not an agreement: the Reviewer gave no usable answer.
                unreviewed.append({"source_row": transaction.source_row,
                                   "description": transaction.description,
                                   "line": first.line_number})
                second = first
            rows.append((transaction, first, second))
        if progress:
            progress(index, len(transactions))
    form = assemble(rows)
    form.unclassified = skipped
    form.unreviewed = unreviewed
    return form
