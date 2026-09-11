# Agents for Humans: two blind agents and a referee draft a nonprofit's Form 990-EZ

Here is row 51 of the synthetic demo ledger going through NinetyNinety:

```
row 51 | MONEY IN | 2025-05-16 | ACME HARDWARE GALA TABLE SPONSOR | 1500

preparer -> line 6d  "Gross receipts from events such as galas, raffles and bingo"
reviewer -> line 1   "Voluntary transfers where the donor receives nothing of comparable value in return"
referee  -> line 6d  quoting the fundraising-event instruction
```

Two agents read the same row, never saw each other, and disagreed. A third agent was reached only because they disagreed, looked up both IRS instructions with a tool, and ruled. The row landed on line 6d, and the disagreement is printed on the draft with all three opinions. That is the whole product.

## Who it is for

Small US nonprofits with under $200k in receipts file Form 990-EZ. Most have no accountant. Someone with a shoebox of bank statements has to decide, for every transaction, which of fifteen Part I lines it belongs on. Get it wrong and the return is wrong. NinetyNinety takes the CSV export and produces a drafted 990-EZ where every line cites the rows behind it and the IRS sentence that justified each call.

It is built on Strands Agents for the AWS Agents for Humans hackathon, Good Neighbor track. Repo: https://github.com/ishal1410/ninetyninety

## The graph

Strands' `GraphBuilder` does the important part for free: entry nodes only receive the task, so two entry nodes cannot see each other.

```python
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
```

The Preparer is prompted as a bookkeeper. The Reviewer is prompted as an auditor who "has NOT seen anyone else's opinion". They run concurrently on the same batch of twelve rows. The edge condition compares their structured outputs row by row:

```python
def _they_disagree(state) -> bool:
    picks = {}
    for node_id in ("preparer", "reviewer"):
        out = state.results[node_id].get_agent_results()[0].structured_output
        picks[node_id] = {c.row: c.line for c in out.calls} if out else {}
    return picks["preparer"] != picks["reviewer"]
```

When they agree, the Referee never runs and the batch costs two model calls. In the first live run the ledger was too clean: 48 rows, zero disagreements, Referee never fired. So six borderline rows went into the demo ledger (a gala sponsorship, a Zelle reimbursement, a member dinner). Second run: 54 rows, five batches, Referee ran in one of them, two disputed rows, both resolved with a cited verdict.

## One tool, and it is not optional

Every agent has exactly one tool:

```python
@tool
def line_guidance(line_number: str) -> str:
    """Return the IRS Form 990-EZ instruction text for one Part I line number
    such as "1", "5c" or "13". Call it for every line you intend to use and
    copy the deciding sentence into your `rule`."""
```

The structured output schema forces a `rule` field per row. After the run, plain Python checks whether at least 60% of the words in that `rule` actually appear in the IRS guidance for the chosen line. An invented justification cannot pass. In the 54-row run, 92 tool calls, zero ungrounded rules.

## What the agents are not allowed to do

Compute totals. Line 9, 17 and 18 come from `formmath.py`, a module no model output ever touches. The next post covers how that module was checked against 3,632 real filed returns, drawn from the 121,299 Form 990-EZ returns in the IRS 2026 e-file index.

## Takeaways

- Blind parallel entry nodes are the cheapest way to get a second opinion; Strands gives you that isolation without any prompt trickery.
- A conditional edge means the expensive arbiter only runs when it is needed. Four of five batches needed it only because the fixtures were made harder on purpose.
- Make the citation a schema field and verify it in code. The model is not the last line of defence.

Built with Strands Agents for the AWS Agents for Humans hackathon. Repo: https://github.com/ishal1410/ninetyninety
