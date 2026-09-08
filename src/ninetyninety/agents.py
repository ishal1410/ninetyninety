"""The Strands Agents graph that classifies a batch of ledger rows.

            +-- preparer (entry, blind) --+
task -------+                             +-- referee (only if they disagree)
            +-- reviewer (entry, blind) --+

Strands feeds entry nodes only the task, so the Reviewer never sees the
Preparer; the two run concurrently. The Referee is reached by a conditional
edge and runs only when their structured outputs differ.

Neither agent ever computes a total -- see formmath.py.
"""
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field
from strands import Agent, tool
from strands.hooks import AfterModelCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry
from strands.multiagent import GraphBuilder

from .ledger import Transaction
from .lines import ALL_LINE_NUMBERS, EXPENSE_LINES, REVENUE_LINES, line_by_number



def _guidance_text(line_number: str) -> str:
    line = line_by_number(line_number)
    return f"Line {line.number} ({line.kind}): {line.label}. {line.guidance}"


@tool
def line_guidance(line_number: str) -> str:
    """Return the IRS Form 990-EZ instruction text for one Part I line number
    such as "1", "5c" or "13". Call it for every line you intend to use and
    copy the deciding sentence into your `rule`."""
    if line_number not in ALL_LINE_NUMBERS:
        return f"No such line: {line_number}. Valid lines: {sorted(ALL_LINE_NUMBERS)}"
    return _guidance_text(line_number)


class RowCall(BaseModel):
    row: int = Field(description="the source row number given in the task")
    line: str = Field(description="Part I line number, e.g. 1, 5c, 13")
    rule: str = Field(description="the deciding sentence copied from line_guidance")
    why: str = Field(description="one sentence tying the row's wording to the rule")
    confidence: str = Field(description="high, medium or low")


class BatchCalls(BaseModel):
    calls: list[RowCall]


class Verdict(BaseModel):
    row: int
    line: str = Field(description="the line that fits best")
    reason: str = Field(description="two sentences citing line_guidance")


class Verdicts(BaseModel):
    verdicts: list[Verdict]


def _menu() -> str:
    return "\n".join(f"  {ln.number}: {ln.label} [{ln.kind}]"
                     for ln in REVENUE_LINES + EXPENSE_LINES)


_RULES = f"""You classify bank-ledger rows of a small US nonprofit onto IRS Form 990-EZ Part I lines.

Line menu:
{_menu()}

Money in must go to a revenue line. Money out must go to an expense line.
Before answering, call line_guidance for every line you intend to use and copy
the deciding sentence into `rule`. Use confidence "low" when the description is
genuinely ambiguous. Never invent a line that is not on the menu. Never compute
totals. Return exactly one entry per row, using the row numbers given."""

PREPARER_PROMPT = "You are a bookkeeper preparing a nonprofit's Form 990-EZ.\n\n" + _RULES
REVIEWER_PROMPT = ("You are an independent reviewer auditing a nonprofit's Form 990-EZ. "
                   "You have NOT seen anyone else's opinion. Judge each row from its "
                   "description alone.\n\n" + _RULES)
REFEREE_PROMPT = """You are a referee. Two independent classifiers labelled preparer and
reviewer disagree on some rows of a nonprofit's ledger. For every row where
their `line` values differ: call line_guidance on BOTH candidate lines, then
return a verdict naming the line that fits the IRS text best and a two-sentence
reason quoting it. Only return verdicts for disputed rows. Never compute totals."""


class TraceHooks(HookProvider):
    """Strands hook provider shared by the three agents: counts model calls
    and tool calls per agent, and records which lines each one looked up.
    That is the judge-visible trace; nothing else observes the agents."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.tool_calls: dict[str, int] = {}
        self.model_calls: dict[str, int] = {}
        self.lines_looked_up: dict[str, list[str]] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.on_tool)
        registry.add_callback(AfterModelCallEvent, self.on_model)

    def on_tool(self, event: BeforeToolCallEvent):
        name = event.agent.name
        self.tool_calls[name] = self.tool_calls.get(name, 0) + 1
        line = str((event.tool_use.get("input") or {}).get("line_number", ""))
        self.lines_looked_up.setdefault(name, []).append(line)

    def on_model(self, event: AfterModelCallEvent):
        name = event.agent.name
        self.model_calls[name] = self.model_calls.get(name, 0) + 1


def build_preparer(model, hooks: TraceHooks | None = None) -> Agent:
    return Agent(model=model, system_prompt=PREPARER_PROMPT, tools=[line_guidance],
                 structured_output_model=BatchCalls, callback_handler=None, name="preparer",
                 hooks=[hooks] if hooks else None)


def build_reviewer(model, hooks: TraceHooks | None = None) -> Agent:
    return Agent(model=model, system_prompt=REVIEWER_PROMPT, tools=[line_guidance],
                 structured_output_model=BatchCalls, callback_handler=None, name="reviewer",
                 hooks=[hooks] if hooks else None)


def build_referee(model, hooks: TraceHooks | None = None) -> Agent:
    return Agent(model=model, system_prompt=REFEREE_PROMPT, tools=[line_guidance],
                 structured_output_model=Verdicts, callback_handler=None, name="referee",
                 hooks=[hooks] if hooks else None)


def batch_task(rows: list[Transaction]) -> str:
    lines = ["ROWS (one classification per row):"]
    for tx in rows:
        direction = "MONEY IN " if tx.amount >= 0 else "MONEY OUT"
        lines.append(f"row {tx.source_row} | {direction} | {tx.date} | "
                     f"{tx.description} | {abs(tx.amount)}")
    return "\n".join(lines)


_WORD = re.compile(r"[a-z]{3,}")


def rule_is_grounded(line_number: str, rule: str) -> bool:
    """True when at least 60% of the rule's words appear in that line's IRS
    guidance. Deterministic; an invented rule cannot pass."""
    if line_number not in ALL_LINE_NUMBERS:
        return False
    # Only the instruction sentence counts; the label and kind are what the
    # agent already saw on the menu, so quoting them proves nothing.
    guidance = set(_WORD.findall(line_by_number(line_number).guidance.lower()))
    words = _WORD.findall(rule.lower())
    if not words:
        return False
    return sum(1 for w in words if w in guidance) / len(words) >= 0.6


def _structured(result, node_id: str):
    node = result.results.get(node_id)
    if node is None:
        return None
    agent_results = node.get_agent_results()
    if not agent_results:
        return None
    return getattr(agent_results[0], "structured_output", None)


def _they_disagree(state) -> bool:
    picks = {}
    for node_id in ("preparer", "reviewer"):
        out = _structured(state, node_id)
        if out is None:
            return False
        picks[node_id] = {c.row: c.line for c in out.calls}
    return picks["preparer"] != picks["reviewer"]


@dataclass
class ReviewGraph:
    """Three agents plus a freshly built graph per run, so no state leaks
    between batches."""
    model: object

    def __post_init__(self):
        self.hooks = TraceHooks()
        self.preparer = build_preparer(self.model, self.hooks)
        self.reviewer = build_reviewer(self.model, self.hooks)
        self.referee = build_referee(self.model, self.hooks)

    def run(self, task: str):
        self.hooks.reset()
        for agent in (self.preparer, self.reviewer, self.referee):
            agent.messages = []
        builder = GraphBuilder()
        builder.add_node(self.preparer, "preparer")
        builder.add_node(self.reviewer, "reviewer")
        builder.add_node(self.referee, "referee")
        builder.set_entry_point("preparer")
        builder.set_entry_point("reviewer")
        builder.add_edge("preparer", "referee", condition=_they_disagree)
        builder.add_edge("reviewer", "referee", condition=_they_disagree)
        builder.set_max_node_executions(3)
        return builder.build()(task)

    @staticmethod
    def calls(result, node_id: str) -> BatchCalls | None:
        out = _structured(result, node_id)
        return out if isinstance(out, BatchCalls) else None

    @staticmethod
    def verdicts(result) -> Verdicts | None:
        out = _structured(result, "referee")
        return out if isinstance(out, Verdicts) else None
