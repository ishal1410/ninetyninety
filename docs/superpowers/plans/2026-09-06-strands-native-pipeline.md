# Strands-Native Pipeline (v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the per-row, prompt-only agents with one Strands graph per batch: two blind parallel entry agents with a real tool and structured output, a conditional referee, rate-limit backoff with provider failover, and a judge-visible trace.

**Architecture:** `agents.py` owns the tool, the pydantic schemas, the three agents and a `ReviewGraph` that builds a fresh `GraphBuilder` graph per run. `prepare.py` batches the ledger, runs the graph with 429 backoff and provider failover, and assembles Part I with the resolution rule. Totals stay in `formmath.py`.

**Tech Stack:** Python 3.12, strands-agents 1.54 (`Agent`, `tool`, `GraphBuilder`), pydantic, Gemini 3.6 Flash (free) with OpenRouter free failover.

## Global Constraints
- The model never does arithmetic. Totals only in `formmath.py`.
- Output is a DRAFT, never a filing. Every screen, PDF and the video say so.
- Never claim a capability that is not implemented.
- Name "Strands Agents" explicitly in README, description, video.
- Zero budget: free tiers only.
- Run tests with `PYTHONPATH=src python -m pytest` (bare `pytest` is a broken shim on this box).
- Spec: `docs/superpowers/specs/2026-09-06-strands-native-pipeline-design.md`.

---

## File Structure
- Rewrite `src/ninetyninety/agents.py`: tool, schemas, prompts, agent builders, `ReviewGraph`, `batch_task`, `rule_is_grounded`, `TOOL_CALLS` counter.
- Rewrite `src/ninetyninety/prepare.py`: `assemble(rows, verdicts)`, `run_graph`, `prepare_ledger` with batching, backoff, failover, trace.
- Modify `src/ninetyninety/config.py`: add `providers_in_order(env)`.
- Modify `cli.py`, `app.py`: referee notes, trace, grounding flags.
- Rewrite `tests/test_agents.py`, `tests/test_prepare.py`; add `tests/test_live.py`.
- Modify `README.md`, regenerate `docs/architecture.png`.

---

### Task 1: agents.py v2 (tool, schemas, graph)

**Files:**
- Rewrite: `src/ninetyninety/agents.py`
- Rewrite: `tests/test_agents.py`

**Interfaces:**
- Consumes: `lines.ALL_LINE_NUMBERS`, `lines.line_by_number`, `lines.REVENUE_LINES/EXPENSE_LINES`, `ledger.Transaction`.
- Produces: `line_guidance` (Strands tool), `TOOL_CALLS: dict`, `RowCall`, `BatchCalls`, `Verdict`, `Verdicts`, `batch_task(rows) -> str`, `rule_is_grounded(line_number, rule) -> bool`, `build_preparer/build_reviewer/build_referee(model) -> Agent`, `ReviewGraph(model)` with `.run(task) -> GraphResult`, `.calls(result, node_id) -> BatchCalls | None`, `.verdicts(result) -> Verdicts | None`.

- [ ] **Step 1: Write the failing tests** (`tests/test_agents.py`): tool returns IRS text containing "independent contractors" and "expense" for "13" and increments `TOOL_CALLS`; tool returns "No such line" for "99"; `batch_task` prints `row 2 | MONEY IN` / `row 3 | MONEY OUT` and never a negative amount; `rule_is_grounded("13", "Payments to people and firms who are not employees")` is True and `rule_is_grounded("13", "Rent paid to the landlord for office space")` is False; `BatchCalls(calls=[RowCall(...)])` round-trips.
- [ ] **Step 2: Run** `PYTHONPATH=src python -m pytest tests/test_agents.py -q` → ImportError.
- [ ] **Step 3: Implement** `src/ninetyninety/agents.py`: module docstring with the graph diagram; `TOOL_CALLS = {"line_guidance": 0}`; `@tool line_guidance(line_number: str) -> str` (counts, validates, returns `Line N (kind): label. guidance`); pydantic `RowCall{row:int,line:str,rule:str,why:str,confidence:str}`, `BatchCalls{calls}`, `Verdict{row,line,reason}`, `Verdicts{verdicts}`; `_RULES` prompt with the line menu (number, label, kind), the direction rule, "call line_guidance for every line you intend to use and copy the deciding sentence into `rule`", "never invent a line", "never compute totals", "exactly one entry per row"; `PREPARER_PROMPT`, `REVIEWER_PROMPT` (has NOT seen anyone else's opinion), `REFEREE_PROMPT` (call line_guidance on BOTH candidate lines, verdicts only for disputed rows); `build_preparer/reviewer/referee(model)` = `Agent(model, system_prompt, tools=[line_guidance], structured_output_model=BatchCalls|Verdicts, callback_handler=None, name=...)`; `batch_task(rows)` = header + `row {n} | MONEY IN /OUT | date | description | abs(amount)`; `rule_is_grounded(line, rule)`: ≥60% of the rule's 3+-letter words appear in label+guidance of that line; `_structured(result, node_id)` reads `result.results[node_id].get_agent_results()[0].structured_output`; `_they_disagree(state)` compares `{row: line}` maps of preparer vs reviewer from `state.results`; `ReviewGraph(model)` dataclass building the three agents in `__post_init__`, `run(task)` resets every agent's `messages`, builds a fresh `GraphBuilder` (two entry points, two conditional edges into referee, `set_max_node_executions(3)`) and invokes it; static `calls(result, node_id)` and `verdicts(result)`.
- [ ] **Step 4: Run** → 5 passed.
- [ ] **Step 5: Commit** `feat: Strands graph with line_guidance tool, structured output and conditional referee`.

---

### Task 2: prepare.py v2 (batching, backoff, failover, trace)

**Files:**
- Rewrite: `src/ninetyninety/prepare.py`; modify `src/ninetyninety/config.py`; rewrite `tests/test_prepare.py`; add one test to `tests/test_config.py`.

**Interfaces:**
- Consumes: Task 1 names; `formmath`; `ledger.Transaction`; `lines`; `config.build_model`.
- Produces: `Form990EZ{lines, totals, disagreements, low_confidence, unclassified, unreviewed, ungrounded, trace}`, `LineResult`, `assemble(rows, verdicts) -> Form990EZ` with rows `(Transaction, RowCall|None, RowCall|None)` and `verdicts: dict[int, Verdict]`, `ProviderExhausted`, `run_graph(review_graph, task, sleep=time.sleep)`, `prepare_ledger(transactions, model=None, progress=None, batch_size=12, providers=None) -> Form990EZ`, `config.providers_in_order(env) -> list[str]`.

- [ ] **Step 1: Failing tests** (`tests/test_prepare.py`): agreed rows sum; expense positive; disagreement with verdict uses referee line and records preparer/reviewer/referee/referee_reason/used; disagreement without verdict uses preparer and `referee is None`; missing preparer → `unclassified` with `error`, missing reviewer → `unreviewed`; low confidence and refunds flagged, refund netted (`lines["1"].amount == -250`); ungrounded rule flagged but still counted; `run_graph` sleeps 7.0 on `'429 ... "retryDelay": "7s"'` then returns; gives up with `ProviderExhausted` after 3×429; re-raises `ValueError` immediately; `prepare_ledger` with a fake `ReviewGraph` (monkeypatched on the module) batches 6 rows at `batch_size=4`, fails over from provider "gemini" to "openrouter" on `ProviderExhausted`, records `trace[*]["provider"]` and `referee_ran`; every provider failing → rows `unclassified` with "exhausted" in `error`. `tests/test_config.py`: `providers_in_order` returns `["gemini","openrouter"]`, `["openrouter"]`, `[]`.
- [ ] **Step 2: Run** → ImportError.
- [ ] **Step 3: Implement.** `config.providers_in_order(env)`: gemini if `GOOGLE_API_KEY`, then openrouter if `OPENROUTER_API_KEY`. `prepare.py`: dataclasses; `ProviderExhausted(RuntimeError)`; `_valid(call)` drops lines not in `ALL_LINE_NUMBERS`; `assemble` implements the resolution rule from the spec §5 plus signed netting by line kind, `low_confidence` notes, `ungrounded` via `rule_is_grounded` (verdict rows exempt); `_is_rate_limit(error)` = `code==429 or status_code==429 or "429" in str`; `_delay_seconds` regex on `retryDelay": "Ns"` or `retry in Ns`, default 20; `run_graph` 3 attempts; `prepare_ledger` builds `ReviewGraph` lazily per provider, splits batches, `TOOL_CALLS` reset per batch, on `ProviderExhausted` advances to the next provider and retries the same batch, on total failure appends `(tx, None, None)` and a trace entry with `error`, otherwise maps calls by row, collects verdicts, appends a trace entry `{batch, rows, provider, nodes, referee_ran, tool_calls, node_ms, seconds}`; after `assemble`, replaces the generic "no answer" error on rows from failed batches with the batch's error text.
- [ ] **Step 4: Run** `tests/test_prepare.py tests/test_config.py` → all pass. **Step 5:** full suite passes.
- [ ] **Step 6: Commit** `feat: batch the ledger through the Strands graph with 429 backoff, failover and a trace`.

---

### Task 3: CLI and app show the referee, the trace and grounding flags

- [ ] `cli.py`: drop `build_model`; call `prepare_ledger(transactions, progress=...)` printing `batch d/t done`; summary line adds `Ungrounded rules`; each disagreement prints `preparer X vs reviewer Y -> referee Z|did not rule; used line U` and the referee reason; unclassified prints `error`; a `STRANDS TRACE` block prints one line per batch (`rows via provider in Ns; nodes a->b->c; tool calls N; referee ran|skipped`).
- [ ] `app.py`: drop `build_model`; progress text "Batch d/t through the Strands graph"; disagreement warning shows all three opinions and "On the form: line U"; new "Rule not found in IRS guidance" section from `form.ungrounded`; an expander "Strands trace · N graph runs" with a caption explaining entry nodes/conditional edge/tool calls and `st.table` of trace rows minus `node_ms`; unclassified shows `error`.
- [ ] Parse check both files; headless Streamlit boot → health 200. Commit `feat: show referee verdicts, grounding flags and the Strands trace`.

---

### Task 4: Live smoke test and the first real end-to-end run

- [ ] `tests/test_live.py`: skipped unless `NN_LIVE=1` and a key; sends the 4 spike rows through `prepare_ledger(rows, batch_size=4)`; asserts a provider in `trace[0]`, `tool_calls >= 1`, identity `line9 - line17 == line18`, no unclassified.
- [ ] Run `NN_LIVE=1 PYTHONPATH=src python -m pytest tests/test_live.py -q` → 1 passed.
- [ ] Run `PYTHONPATH=src python cli.py fixtures/demo_ledger.csv`; expect 4 batches, totals, ≥1 disagreement, trace block. Record wall time, disagreement count, tool calls in `.superpowers/sdd/progress.md`.
- [ ] Commit `test: opt-in live smoke through the Strands graph; record first end-to-end run`.

---

### Task 5: README, diagram, ledger, push

- [ ] README "How it works" step 2 → the graph (two blind parallel entry nodes, real `line_guidance` tool, structured output, conditional Referee, all three opinions shown); step 3 → Python grounding check + formmath. Add "Model providers" (Gemini free first, OpenRouter free failover, 429 backoff honouring the advertised delay, batch-level failover). Add "Disclosure" (public IRS `f990ez.pdf`, public IRS 990 e-file XML, Strands Agents SDK; all code written in the submission period; validation output lists EINs/org names exactly as the IRS publishes them).
- [ ] Diagram: three agent boxes (Preparer/Reviewer "entry node, blind; tool: line_guidance; structured output", Referee "conditional edge, only on disagreement; verdict"); model line "Gemini 3.6 Flash (free) / OpenRouter free failover". Re-render, view.
- [ ] Ledger entry with hashes and live numbers. Commit `docs: describe the Strands graph, tool, referee and provider failover`; `git push origin master`.
