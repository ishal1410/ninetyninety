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


def assemble(
    rows: list[tuple[Transaction, Classification, Classification]],
) -> Form990EZ:
    form = Form990EZ()
    for transaction, preparer, reviewer in rows:
        chosen = preparer.line_number
        result = form.lines.setdefault(chosen, LineResult(chosen))
        result.amount += abs(transaction.amount)
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
        elif "low" in (preparer.confidence, reviewer.confidence):
            form.low_confidence.append({
                "source_row": transaction.source_row,
                "description": transaction.description,
                "line": chosen,
            })

    amounts = {number: result.amount for number, result in form.lines.items()}
    form.totals = {
        "line9": total_revenue(amounts),
        "line17": total_expenses(amounts),
        "line18": excess_or_deficit(amounts),
    }
    return form


def _ask(agent, transaction: Transaction) -> Classification | None:
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
    for index, transaction in enumerate(transactions, start=1):
        first = _ask(preparer, transaction)
        if first is None:
            skipped.append({"source_row": transaction.source_row,
                            "description": transaction.description,
                            "amount": transaction.amount})
        else:
            rows.append((transaction, first, _ask(reviewer, transaction) or first))
        if progress:
            progress(index, len(transactions))
    form = assemble(rows)
    form.unclassified = skipped
    return form
