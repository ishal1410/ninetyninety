# NinetyNinety v2: Strands-native classification pipeline

**Date:** 2026-09-06
**Why:** Judging criterion 1 asks *"How thoroughly and skillfully does the project use Strands Agents?"* and is the tie-breaker. v1 used two `Agent` objects with a system prompt and nothing else. The first live run also hit Gemini's free-tier limit (5 requests/minute) at row 3 of 48, because v1 made one model call per row per agent. v2 fixes both with one design.

Spike evidence (2026-09-06, Gemini 3.6 Flash through Strands 1.54): a two-entry `GraphBuilder` graph ran Preparer and Reviewer blind and in parallel in 9.5s for a 4-row batch, made 6 real `@tool` calls, returned pydantic structured output from both, and skipped the conditional fan-in node because the two agreed.

## What changes

### 1. Batches, not rows
`prepare_ledger` splits the ledger into batches of `batch_size` rows (default 12). One graph invocation per batch. 48 rows = 4 graph runs = 8 to 12 model calls instead of 96.

### 2. One Strands graph per batch
```
            +-- preparer (entry, blind) --+
task -------+                             +-- referee (only if they disagree)
            +-- reviewer (entry, blind) --+
```
- **Preparer** and **Reviewer** are both entry points. Strands feeds entry nodes only the task text, so the Reviewer never sees the Preparer (verified in `strands/multiagent/graph.py::_build_node_input`). They execute concurrently.
- **Referee** hangs off both with a `condition` edge: it runs only when the two structured outputs differ on at least one row. It receives both opinions, must call `line_guidance` on every candidate line, and returns a `Verdict` per disputed row. It never touches totals.
- Agents get `callback_handler=None` (no stdout streaming) and their messages are reset before every graph run (`reset_on_revisit` covers revisits inside one run, not across runs).

### 3. A real tool
`@tool line_guidance(line_number: str) -> str` returns the IRS instruction text for a Part I line from `lines.py`. Agents are told to call it for every line they use and copy the deciding sentence into `rule`. Deterministic post-check in Python: `rule` must share at least 60% of its words with that line's guidance, otherwise the row is flagged `rule not grounded`. The model cannot invent a rule that passes.

### 4. Structured output
`Agent(structured_output_model=BatchCalls)` replaces the regex parser. Schemas:
- `RowCall {row: int, line: str, rule: str, why: str, confidence: "high"|"medium"|"low"}`
- `BatchCalls {calls: list[RowCall]}`
- `Verdict {row: int, line: str, reason: str}`; `Verdicts {verdicts: list[Verdict]}`
Rows missing from an agent's output, or with a line not in `ALL_LINE_NUMBERS`, are treated as "no answer" for that agent. `parse_classification` and the LINE/RULE/WHY text format are deleted.

### 5. Resolution rule
- Both agree: Preparer's line, and the row is corroborated.
- Disagree and Referee returned a verdict for the row: Referee's line goes on the form; the row is recorded under `disagreements` with all three opinions and the Referee's reason. Nothing is hidden.
- Disagree and no verdict: Preparer's line, recorded under `disagreements` with `referee: none`.
- Preparer gave no answer: row goes to `unclassified`. Reviewer gave no answer: `unreviewed`.
Totals stay in `formmath.py`. Signed netting by line kind stays.

### 6. Rate limits and failover
`run_graph(graph, task)` retries on a 429 up to 3 times, sleeping the provider's `retryDelay` when present (else 20s). After that it raises `ProviderExhausted`; `prepare_ledger` then rebuilds the graph on the next provider from `config.providers_in_order` and retries the same batch once. If every provider fails the batch's rows go to `unclassified` with the error text, and the run continues.

### 7. Trace, shown to the judge
Per batch: node execution order, per-node milliseconds, tool-call count, whether the referee ran. `Form990EZ.trace: list[dict]`. CLI prints one line per batch; the app shows a "Strands trace" expander. This is the visible proof of criterion 1.

## Interfaces
- `agents.py`: `line_guidance`, `RowCall`, `BatchCalls`, `Verdict`, `Verdicts`, `build_preparer(model)`, `build_reviewer(model)`, `build_referee(model)`, `build_review_graph(model) -> ReviewGraph` (holds the graph and the three agents), `batch_task(rows: list[Transaction]) -> str`, `rule_is_grounded(line, rule) -> bool`.
- `prepare.py`: `assemble(rows, verdicts)` where rows are `(Transaction, RowCall|None, RowCall|None)`; `run_graph(review_graph, task) -> GraphResult`; `prepare_ledger(transactions, model=None, progress=None, batch_size=12) -> Form990EZ`.
- `config.py`: unchanged API; `providers_in_order(env) -> list[str]` added.

## Testing
- Unit (no network): batching splits; `assemble` resolution rule for all five cases; grounding check; 429 retry honours delay and gives up; provider failover order; trace shape. Fake graph objects via monkeypatching `build_review_graph`.
- Live smoke (skipped unless `GOOGLE_API_KEY` and `NN_LIVE=1`): one 4-row batch through the real graph, asserts structured output and at least one tool call.
- Existing formmath/xmlparse/validate/pdffill tests untouched.

## Out of scope
Swarm, AgentCore deployment, session persistence, Parts II-VI, any model arithmetic.
