# Win-First-Prize Closing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every gap in the 2026-09-08 scorecard that a judge can see: Strands depth (criterion 1), hosted-demo robustness (1, 2), video (5), blog bonus (+0.6), Devpost text.

**Architecture:** Code work is limited to two things: a Strands `HookProvider` that replaces the global tool counter and gives the trace per-node model and tool call counts, and a recorded-run loader so the hosted Streamlit app still demos when the Gemini free quota is spent. Everything else is prose: blog 3 rewrite, video script, Devpost submission text, deploy runbook.

**Tech Stack:** Python 3.12, strands-agents 1.54.0 (`strands.hooks`), Streamlit 1.63, pytest 9.

## Global Constraints

- Deadline 2026-09-14 17:00 PDT. Blog posts must be public on builder.aws.com before that.
- Every blog title contains the literal phrase "Agents for Humans" (Manager ruling, forum 45031, Sep 8).
- Track: Good Neighbor Agents (nonprofits are named in the track text; README already says so).
- Zero spend: Google Gemini free tier is the only runtime provider. Do NOT re-add Bedrock/OpenRouter code.
- No em dashes or en dashes anywhere (`tests/test_landing_pages.py` and house style).
- Run tests with `python -m pytest` (conftest adds src). 87 pass, 1 skipped at start.
- Numbers that may be quoted: 3,632 checked returns (3,687 files), 100.00 / 99.97 / 99.94, demo run 54 rows, 5 batches, 2 disagreements, Referee ran on 1 batch, 92 tool calls, 577 s.
- Real filer EINs in `results/validation.json` are public IRS data; leave them.

---

### Task 1: Strands hooks replace the global tool counter

**Files:**
- Modify: `src/ninetyninety/agents.py:23,36,152-171`
- Modify: `src/ninetyninety/prepare.py:11,224,249-256`
- Modify: `cli.py` (trace print), `app.py` (trace render, search `tool calls`), `technical.html` (trace table, search `trace-rows`)
- Test: `tests/test_agents.py`, `tests/test_prepare.py`

**Interfaces:**
- Produces: `class TraceHooks(HookProvider)` in `agents.py` with attributes `tool_calls: dict[str, int]` (per agent name), `model_calls: dict[str, int]`, `lines_looked_up: dict[str, list[str]]`, and `reset()`. `ReviewGraph.hooks: TraceHooks`. Trace dict gains keys `model_calls` (dict) and `tool_calls_by_node` (dict); `tool_calls` (int total) stays.

- [ ] **Step 1: Failing test in `tests/test_agents.py`**

```python
from strands.hooks import BeforeToolCallEvent, AfterModelCallEvent
from ninetyninety.agents import TraceHooks


def test_trace_hooks_count_tool_and_model_calls_per_agent():
    hooks = TraceHooks()
    class A: name = "preparer"
    hooks.on_tool(BeforeToolCallEvent(agent=A(), selected_tool=None,
                                      tool_use={"name": "line_guidance", "input": {"line_number": "13"}, "toolUseId": "t1"},
                                      invocation_state={}))
    hooks.on_model(AfterModelCallEvent(agent=A()))
    hooks.on_model(AfterModelCallEvent(agent=A()))
    assert hooks.tool_calls == {"preparer": 1}
    assert hooks.model_calls == {"preparer": 2}
    assert hooks.lines_looked_up == {"preparer": ["13"]}
    hooks.reset()
    assert hooks.tool_calls == {} and hooks.model_calls == {}
```

If the event constructors need different kwargs in 1.54.0, run `python -c "import inspect, strands.hooks as h; print(inspect.signature(h.BeforeToolCallEvent))"` and adapt the test, not the production code.

- [ ] **Step 2: Run, expect ImportError on TraceHooks**

`python -m pytest tests/test_agents.py -q -k trace_hooks`

- [ ] **Step 3: Implement in `agents.py`**

```python
from strands.hooks import AfterModelCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry


class TraceHooks(HookProvider):
    """Strands hook provider: counts model and tool calls per agent for the
    judge-visible trace. One instance is shared by the three agents."""

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
        line = str(event.tool_use.get("input", {}).get("line_number", ""))
        self.lines_looked_up.setdefault(name, []).append(line)

    def on_model(self, event: AfterModelCallEvent):
        name = event.agent.name
        self.model_calls[name] = self.model_calls.get(name, 0) + 1
```

Delete `TOOL_CALLS` and the increment inside `line_guidance`. `build_preparer/reviewer/referee` gain a `hooks` parameter passed as `hooks=[hooks]`. `ReviewGraph.__post_init__` creates `self.hooks = TraceHooks()` and passes it to the three builders; `ReviewGraph.run` calls `self.hooks.reset()` first.

- [ ] **Step 4: Update `prepare.py`**

Remove `TOOL_CALLS` import and the reset at line 224. Trace entry becomes:

```python
"tool_calls": sum(graph.hooks.tool_calls.values()),
"tool_calls_by_node": dict(graph.hooks.tool_calls),
"model_calls": dict(graph.hooks.model_calls),
```

Fix the fake graph in `tests/test_prepare.py` (search `ids = ["preparer", "reviewer"]`) so it exposes `.hooks = TraceHooks()`; add one assertion that `form.trace[0]["model_calls"]` is a dict.

- [ ] **Step 5: Render it**

`cli.py` trace line: append `f"; model calls {t.get('model_calls', {})}"`. `app.py` and `technical.html`: add a "model calls" column next to "tool calls" (per-node dict printed as `preparer 3, reviewer 3, referee 1`). README "Strands trace" bullet: mention hooks (`HookProvider` on `BeforeToolCallEvent` and `AfterModelCallEvent`).

- [ ] **Step 6: `python -m pytest -q` green, then commit** `feat: Strands hooks drive the trace (per-node model and tool calls)`

---

### Task 2: Recorded-run loader for the hosted demo

**Files:**
- Create: `src/ninetyninety/recorded.py`
- Modify: `app.py` (button beside the upload; search `st.session_state["draft"]`)
- Test: `tests/test_recorded.py`

**Interfaces:**
- Produces: `load_recorded_run(path: Path) -> Form990EZ` rebuilding `LineResult` objects from `results/demo_run.json` (written by `scripts/dump_run.py` via `dataclasses.asdict`).

- [ ] **Step 1: Failing test**

```python
from pathlib import Path
from ninetyninety.recorded import load_recorded_run


def test_recorded_run_rebuilds_the_form():
    form = load_recorded_run(Path("results/demo_run.json"))
    assert form.totals["line9"] == 38919
    assert form.lines["1"].amount == 9100
    assert len(form.disagreements) == 2
    assert form.trace[0]["rows"] == 12
```

- [ ] **Step 2: Run, expect ModuleNotFoundError**

- [ ] **Step 3: Implement**

```python
"""Replay the recorded demo run when the free-tier quota is gone."""
import json
from pathlib import Path

from .prepare import Form990EZ, LineResult

KEEP = ("totals", "disagreements", "low_confidence", "unclassified",
        "unreviewed", "ungrounded", "trace")


def load_recorded_run(path: Path) -> Form990EZ:
    data = json.loads(path.read_text(encoding="utf-8"))
    form = Form990EZ(**{k: data[k] for k in KEEP if k in data})
    form.lines = {k: LineResult(**v) for k, v in data["lines"].items()}
    return form
```

- [ ] **Step 4: Wire into `app.py`**

Next to the file uploader add `st.button("Replay the recorded run (no model calls)")`. On click: `form = load_recorded_run(BASE / "results" / "demo_run.json")`, `transactions = load_ledger(BASE / "fixtures" / "demo_ledger.csv", skipped := [])`, fill the PDF exactly as the live path does, set `st.session_state["draft"]` the same way, and show a one-line note "Recorded on 2026-09-08 through Google Gemini; live runs use the same code." Also: when `prepare_ledger` returns with every batch in `form.unclassified` because of quota (`"exhausted"` in the first trace error), show the same button under the error.

- [ ] **Step 5: Verify** `python -m pytest -q` green; `streamlit run app.py` and click the button (Playwright snapshot on 8501 if available, else manual). Commit `feat: replay the recorded run when the quota is spent`.

---

### Task 3: Blog 3 rewrite (prose, subagent)

**Files:** Modify `docs/blog/03-from-20-requests-a-day-to-bedrock.md` (rename to `03-from-20-requests-a-day-to-a-rotation.md`); check titles of 01 and 02.

- [ ] Title: "Agents for Humans: I built on a 20-request-a-day free tier and shipped on a five-model rotation". Story: measured 20 req/day/model on Gemini free; Bedrock on a new Free-plan account has applied quota 0 tokens/day (re:Post threads; not a verification hold); wired Bedrock, deleted it, one-provider decision; Strands `GeminiModel`; rotation across 5 flash ids on `ProviderExhausted`; the 09-08 run numbers. Keep under 900 words, at most 3 code blocks, no dashes.
- [ ] Blog 02 title says 3,687: change to "checked against 3,632 real IRS returns" and fix body numbers.
- [ ] Every post ends with repo link and the sentence "Built with Strands Agents for the AWS Agents for Humans hackathon."
- [ ] Commit `docs: blog posts final for builder.aws`.

---

### Task 4: Video script and shot list (prose, subagent)

**Files:** Create `docs/video-script.md`.

- [ ] Structure, at most 4:30 total, timestamps per shot: 0:00 problem (volunteer treasurer, auto-revocation after 3 missed filings), 0:35 who it is for, 0:50 upload CSV in the hosted app, 1:20 Strands graph running (skeleton, then trace table: nodes, tool calls, model calls, referee), 2:20 one disagreement expanded (Preparer vs Reviewer vs Referee quote), 3:00 the filled DRAFT PDF, 3:30 the 3,632-return validation numbers, 3:55 architecture diagram with Strands named explicitly, 4:15 close: repo URL, "Agents for Humans", Good Neighbor track.
- [ ] Every spoken line written out verbatim. Screen recording tool: OBS or Windows Game Bar; upload to YouTube public.
- [ ] Commit `docs: video script`.

---

### Task 5: Devpost submission text (prose, subagent)

**Files:** Create `docs/devpost-submission.md`.

- [ ] Fields: Project name, tagline (60 chars max), track = Good Neighbor Agents with one-line rationale, description (first sentence names the problem, second sentence names Strands Agents explicitly, per Devpost "Pro tips" update), "How we built it" (GraphBuilder, two blind entry nodes, conditional Referee edge, `@tool line_guidance`, structured output, hooks trace, Python arithmetic + grounding), "Challenges" (Bedrock quota 0, free-tier rotation), "Accomplishments" (3,632 returns), "What we learned", "What's next" (Parts II to VI, e-file), testing instructions (two commands, plus hosted URL placeholder), pre-existing-work disclosure (IRS f990ez.pdf and IRS e-file XML corpus are public IRS assets, not project code), video URL placeholder, repo URL, architecture diagram path.
- [ ] Commit `docs: devpost submission text`.

---

### Task 6: Deploy runbook (prose, subagent)

**Files:** Create `docs/deploy.md`, `scripts/ec2-user-data.sh`.

- [ ] Streamlit Community Cloud steps: sign in with GitHub, pick `ishal1410/ninetyninety`, main file `app.py`, Python 3.12, Secrets = `GOOGLE_API_KEY`, note that free tier sleeps after inactivity (wake it before judging window).
- [ ] EC2 path from the $100 credit (t3.small, Amazon Linux 2023): user-data installs python3.12 + git, clones repo, writes `.env`, systemd unit `streamlit run app.py --server.port 80 --server.address 0.0.0.0`, security group port 80. Puts one AWS service in the diagram (add "Hosted on Amazon EC2" to `scripts/diagram.py` box 1 only after it is actually deployed).
- [ ] After deploy: set `STREAMLIT_URL` in `index.html:357`, run `python scripts/build_landing.py`, README line 65, push.
- [ ] Commit `docs: deploy runbook`.

---

## Self-review

Spec coverage: criterion 1 (Task 1, 6), criterion 2 (Task 2, 6), criterion 5 (Task 4), bonus (Task 3), Devpost text and track (Task 5). Human-only steps remain: recording the video, clicking deploy, publishing posts. Placeholders: none besides the URL placeholders that only the human can fill. Names: `TraceHooks`, `load_recorded_run` used consistently.
