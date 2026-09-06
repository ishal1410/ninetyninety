"""The two Strands Agents.

Preparer classifies each transaction to a Form 990-EZ Part I line and cites
the rule. Reviewer independently classifies the SAME transaction without
seeing the Preparer's reasoning, so agreement is real corroboration and
disagreement is shown to the user rather than silently resolved.

Neither agent ever computes a total -- see formmath.py.
"""
import re
from dataclasses import dataclass

from strands import Agent

from .lines import ALL_LINE_NUMBERS, EXPENSE_LINES, REVENUE_LINES


@dataclass
class Classification:
    source_row: int
    line_number: str
    rationale: str
    rule: str
    confidence: str


def line_reference() -> str:
    parts = ["REVENUE LINES (money in):"]
    parts += [f"  Line {line.number}: {line.label}\n    {line.guidance}"
              for line in REVENUE_LINES]
    parts.append("EXPENSE LINES (money out):")
    parts += [f"  Line {line.number}: {line.label}\n    {line.guidance}"
              for line in EXPENSE_LINES]
    return "\n".join(parts)


_ANSWER_FORMAT = """Answer in exactly this format and nothing else:

LINE: <the line number, e.g. 1 or 5c or 13>
RULE: <the sentence from the line guidance that decides it>
WHY: <one sentence tying this transaction's wording to that rule>
CONFIDENCE: <high|medium|low>

Use CONFIDENCE: low when the description is genuinely ambiguous. Never invent a
line number that is not listed. Never compute totals."""


def _prompt(role: str) -> str:
    return f"""{role}

You classify one transaction from a small US nonprofit's bank ledger onto a
line of IRS Form 990-EZ Part I.

{line_reference()}

Money in must go to a revenue line; money out must go to an expense line.

{_ANSWER_FORMAT}"""


PREPARER_PROMPT = _prompt(
    "You are a bookkeeper preparing a nonprofit's Form 990-EZ.")

REVIEWER_PROMPT = _prompt(
    "You are an independent reviewer auditing a nonprofit's Form 990-EZ. You "
    "have NOT seen anyone else's opinion of this transaction. Form your own "
    "judgement from the description alone.")


def build_preparer(model) -> Agent:
    return Agent(model=model, system_prompt=PREPARER_PROMPT)


def build_reviewer(model) -> Agent:
    return Agent(model=model, system_prompt=REVIEWER_PROMPT)


def _field(text: str, name: str) -> str:
    match = re.search(rf"^{name}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_classification(text: str, source_row: int) -> Classification | None:
    number = _field(text, "LINE")
    if number not in ALL_LINE_NUMBERS:
        return None
    confidence = _field(text, "CONFIDENCE").lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    return Classification(
        source_row=source_row,
        line_number=number,
        rationale=_field(text, "WHY"),
        rule=_field(text, "RULE"),
        confidence=confidence,
    )
