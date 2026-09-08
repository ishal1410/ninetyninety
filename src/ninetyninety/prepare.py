"""Turn a ledger into a Form 990-EZ Part I with one Strands graph per batch.

`assemble` is pure and deterministic. Totals come from formmath, never from a
model. Disagreements are recorded with all three opinions; nothing is hidden.
"""
import re
import time
from dataclasses import dataclass, field

from .agents import (
    TOOL_CALLS, BatchCalls, ReviewGraph, RowCall, Verdict, batch_task,
    rule_is_grounded,
)
from .config import build_model, model_ids, provider_label
from .formmath import excess_or_deficit, total_expenses, total_revenue
from .ledger import Transaction
from .lines import ALL_LINE_NUMBERS, line_by_number


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
    ungrounded: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)


class ProviderExhausted(RuntimeError):
    """A provider kept answering 429 or 5xx after every retry."""


NO_ANSWER = "no answer from the Preparer"


def _valid(call: RowCall | None) -> RowCall | None:
    return call if call is not None and call.line in ALL_LINE_NUMBERS else None


def assemble(rows: list[tuple[Transaction, RowCall | None, RowCall | None]],
             verdicts: dict[int, Verdict]) -> Form990EZ:
    form = Form990EZ()
    for transaction, preparer, reviewer in rows:
        row = transaction.source_row
        single_opinion = None
        if preparer is None and reviewer is not None:
            # Only the Reviewer answered: use it, but say so. Never silent.
            preparer, reviewer, single_opinion = reviewer, None, "only the Reviewer answered"
        if preparer is None:
            form.unclassified.append({
                "source_row": row, "description": transaction.description,
                "amount": transaction.amount, "error": NO_ANSWER})
            continue
        # An agent that names a line not on the form has answered, wrongly:
        # report that, and let the other agent's valid line win the dispute.
        if _valid(preparer) is None and _valid(reviewer) is None:
            form.unclassified.append({
                "source_row": row, "description": transaction.description,
                "amount": transaction.amount,
                "error": f"line {preparer.line} is not on Form 990-EZ Part I"})
            continue
        if reviewer is None:
            form.unreviewed.append({"source_row": row, "description": transaction.description,
                                    "line": preparer.line,
                                    "note": single_opinion or "only the Preparer answered"})

        default = preparer if _valid(preparer) else reviewer
        chosen, rule, why = default.line, default.rule, default.why
        verdict = None
        disputed = reviewer is not None and reviewer.line != preparer.line
        if disputed:
            verdict = verdicts.get(row)
            # The Referee may only pick one of the two disputed lines.
            if (verdict is not None and verdict.line in ALL_LINE_NUMBERS
                    and verdict.line in (preparer.line, reviewer.line)):
                chosen, rule, why = verdict.line, verdict.reason, "referee's verdict"
            else:
                verdict = None
            form.disagreements.append({
                "source_row": row, "description": transaction.description,
                "preparer": preparer.line, "preparer_rule": preparer.rule,
                "reviewer": reviewer.line, "reviewer_rule": reviewer.rule,
                "referee": verdict.line if verdict else None,
                "referee_reason": verdict.reason if verdict else None,
                "used": chosen,
            })
        # The Referee's reason is a quoted rule too; it gets the same check.
        if not rule_is_grounded(chosen, rule):
            form.ungrounded.append({"source_row": row, "description": transaction.description,
                                    "line": chosen, "rule": rule})

        result = form.lines.setdefault(chosen, LineResult(chosen))
        # Revenue lines carry money-in as positive; expense lines carry
        # money-out as positive. A refund therefore NETS against its line.
        revenue = line_by_number(chosen).kind == "revenue"
        signed = transaction.amount if revenue else -transaction.amount
        result.amount += signed
        result.transactions.append({
            "source_row": row, "date": transaction.date,
            "description": transaction.description, "amount": transaction.amount,
            "rule": rule, "why": why,
        })
        low = "low" in (preparer.confidence.lower(),
                        reviewer.confidence.lower() if reviewer else "")
        if not disputed and (low or signed < 0):
            form.low_confidence.append({
                "source_row": row, "description": transaction.description, "line": chosen,
                "note": ("money flows against this line; netted as a refund"
                         if signed < 0 else "low confidence"),
            })

    amounts = {number: result.amount for number, result in form.lines.items()}
    form.totals = {"line9": total_revenue(amounts), "line17": total_expenses(amounts),
                   "line18": excess_or_deficit(amounts)}
    return form


_DELAY = re.compile(r'retryDelay"?\s*:\s*"?(\d+(?:\.\d+)?)s|retry in (\d+(?:\.\d+)?)s', re.I)


_TRANSIENT = (429, 500, 502, 503, 504)


# botocore names these in the error code; the openai client and Strands in the class name.
_TRANSIENT_WORDS = re.compile(
    r"Throttl|RateLimit|TooManyRequests|ServiceUnavailable|InternalServer|ModelNotReady|Overloaded", re.I)
# A status code stands alone ("429 RESOURCE_EXHAUSTED", "Error code: 503 - {"),
# never glued to "=", "$" or digits the way an echoed amount in a
# validation error is ("input_value=500 is not a str").
_STATUS = re.compile(r"(?<![=$\d.])\b(429|50[0234])\b(?=\s*(?:[A-Z(\-:]|$))")


def _is_transient(error: Exception) -> bool:
    """Rate limits and provider-side outages: retry, then give up on the batch."""
    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    if code in _TRANSIENT:
        return True
    response = getattr(error, "response", None)  # botocore ClientError
    if isinstance(response, dict):
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") in _TRANSIENT:
            return True
        if _TRANSIENT_WORDS.search(str(response.get("Error", {}).get("Code", ""))):
            return True
    if _TRANSIENT_WORDS.search(type(error).__name__):
        return True
    return _STATUS.search(str(error)) is not None


def _delay_seconds(error: Exception) -> float:
    match = _DELAY.search(str(error))
    if match:
        return float(match.group(1) or match.group(2))
    return 20.0


def run_graph(review_graph, task: str, sleep=time.sleep):
    """Run one batch, sleeping the provider's advertised delay on a 429 or
    a 5xx, then handing the batch to the next provider."""
    for attempt in range(3):
        try:
            return review_graph.run(task)
        except Exception as error:  # noqa: BLE001 - classify, then re-raise or retry
            if not _is_transient(error):
                raise
            if attempt == 2:
                raise ProviderExhausted(str(error)[:200]) from error
            sleep(_delay_seconds(error))
    raise ProviderExhausted("unreachable")


def _calls_by_row(calls: BatchCalls | None) -> dict[int, RowCall]:
    return {c.row: c for c in calls.calls} if calls else {}


def prepare_ledger(transactions: list[Transaction], model=None, progress=None,
                   batch_size: int = 12) -> Form990EZ:
    """Classify the ledger batch by batch through the Strands graph on
    Gemini. `model` pins one model (tests); otherwise the ids in
    `model_ids()` are tried in order, moving to the next when one is
    rate-limited out, because the free tier's daily cap is per model.
    `progress(done, total)` is called after each batch if given.

    A batch no model can answer even after backoff is recorded as
    unclassified with the error text; the run continues and nothing
    already classified is lost.
    """
    candidates = [model] if model is not None else model_ids()
    models: list = []
    graphs: list[ReviewGraph] = []
    retired: set[int] = set()  # model ids whose daily cap is gone for this run

    def graph_at(i: int) -> ReviewGraph:
        while len(graphs) <= i:
            c = candidates[len(graphs)]
            models.append(c if model is not None else build_model(c))
            graphs.append(ReviewGraph(models[-1]))
        return graphs[i]

    rows: list[tuple[Transaction, RowCall | None, RowCall | None]] = []
    verdicts: dict[int, Verdict] = {}
    trace: list[dict] = []
    failed_rows: dict[int, str] = {}
    batches = [transactions[i:i + batch_size] for i in range(0, len(transactions), batch_size)]
    error = None  # the last failure; once every model is out, later batches inherit it
    for index, batch in enumerate(batches, start=1):
        task = batch_task(batch)
        result, graph, provider = None, None, None
        started = time.time()
        for i in range(len(candidates)):
            if i in retired:
                continue
            graph = graph_at(i)
            provider = provider_label(models[i])
            TOOL_CALLS["line_guidance"] = 0
            try:
                result = run_graph(graph, task)
                break
            except ProviderExhausted as exhausted:
                error = f"{provider} exhausted: {exhausted}"
                retired.add(i)
            except Exception as failure:  # noqa: BLE001 - a 404 model id or a malformed
                # structured answer costs this batch on this model only; the next
                # model gets the batch and this model stays available for the next
                error = f"{provider} failed: {type(failure).__name__}: {str(failure)[:200]}"
        if result is None:
            for tx in batch:
                rows.append((tx, None, None))
                failed_rows[tx.source_row] = error
            trace.append({"batch": index, "rows": len(batch), "provider": provider,
                          "error": error, "seconds": round(time.time() - started, 1)})
        else:
            prep = _calls_by_row(graph.calls(result, "preparer"))
            rev = _calls_by_row(graph.calls(result, "reviewer"))
            batch_verdicts = graph.verdicts(result)
            for verdict in (batch_verdicts.verdicts if batch_verdicts else []):
                verdicts[verdict.row] = verdict
            for tx in batch:
                rows.append((tx, prep.get(tx.source_row), rev.get(tx.source_row)))
            order = [node.node_id for node in result.execution_order]
            trace.append({
                "batch": index, "rows": len(batch), "provider": provider,
                "nodes": order, "referee_ran": "referee" in order,
                "tool_calls": TOOL_CALLS["line_guidance"],
                "node_ms": {n: getattr(result.results[n], "execution_time", None) for n in order},
                "seconds": round(time.time() - started, 1),
            })
        if progress:
            progress(index, len(batches))

    form = assemble(rows, verdicts)
    for item in form.unclassified:
        if item["source_row"] in failed_rows:
            item["error"] = failed_rows[item["source_row"]]
    form.trace = trace
    return form
