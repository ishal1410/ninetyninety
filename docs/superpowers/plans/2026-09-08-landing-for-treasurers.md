# Landing for Treasurers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `index.html` for the volunteer treasurer, move the engineering material to `technical.html`, and make the build script feed both pages from the recorded run.

**Architecture:** Two static pages share one stylesheet block and one data contract: `scripts/build_landing.py` injects `results/demo_run.json` (plus `validation.json` and the Part I taxonomy) into a `<script id="run">` and `<script id="lines">` tag in each page. Each page renders its own sections from that JSON in inline JS. A Playwright test opens both pages from `file://` and asserts the copy rules.

**Tech Stack:** Static HTML/CSS/JS, Python 3.12 build script, pytest, Playwright (already installed).

## Global Constraints

- Reader: volunteer treasurer of a small US nonprofit (README "Who it is for").
- Agent names stay Preparer, Reviewer, Referee.
- CTA text is "Run it on your computer" while `STREAMLIT_URL` is empty; "Draft a return" when set.
- Hackathon appears once on index.html, in the footer: "Built with Strands Agents for the AWS Agents for Humans hackathon."
- No em dash (U+2014) or en dash (U+2013) anywhere in either page.
- DRAFT disclaimer stays on the form image alt text and in copy ("a draft, not a filing").
- Nothing the repo cannot back: every number comes from `results/demo_run.json` or `results/validation.json`.
- Data note sentence: "Your transactions are sent to Google's Gemini API to be sorted. The blank IRS form is fetched once from irs.gov. Nothing else leaves your computer."
- Visual system unchanged from the approved v10 `index.html` (dark, Geist, `--accent: #35d07f`, bezel frames, island nav).
- Tests run with `PYTHONPATH=src python -m pytest`.

---

### Task 1: build_landing.py injects into every page that carries the tags

**Files:**
- Modify: `scripts/build_landing.py` (whole file)
- Test: `tests/test_build_landing.py`

**Interfaces:**
- Produces: `inject(page: Path, payload: dict, lines: list[dict]) -> str` returning the new HTML and writing it; `PAGES = ["index.html", "technical.html"]`; module still runnable as a script.

- [ ] **Step 1: Write the failing test** (`tests/test_build_landing.py`): load the script as a module, call `inject` on a temp page holding both tags, assert `</` is escaped, the lines tag is filled, the file is written, and a second call is idempotent.
- [ ] **Step 2: Run** `PYTHONPATH=src python -m pytest tests/test_build_landing.py -v`. Expected: FAIL, no attribute `inject`.
- [ ] **Step 3: Implement** `_put`, `inject`, `main` with `PAGES`; `main` skips pages that do not exist and prints one line per page.
- [ ] **Step 4: Run the test.** Expected: 2 passed.
- [ ] **Step 5: Commit** `refactor(build_landing): inject() function, feeds every page with the data tags`.

### Task 2: technical.html, the engineering page

**Files:**
- Create: `technical.html` (same head and style block as index.html; sections `#graph`, `#trace`, `#validation`; footer links to `index.html`)
- Test: `tests/test_landing_pages.py`

- [ ] **Step 1: Write the failing test**: render `technical.html` from `file://` with Playwright, assert no page errors, "Preparer" and "Referee" present, a model name present, "tool calls" present, a link to `index.html`, no dashes.
- [ ] **Step 2: Run.** Expected: FAIL, file not found.
- [ ] **Step 3: Write the page** (graph with measured wires, trace table, validation table, mismatch note; JS as in the current index.html for trace, validation and wires).
- [ ] **Step 4: Run** `PYTHONPATH=src python scripts/build_landing.py` then the test. Expected: 1 passed.
- [ ] **Step 5: Commit** `feat: technical.html carries the graph, trace and validation for engineers and judges`.

### Task 3: index.html rewritten for the treasurer

**Files:**
- Modify: `index.html` body and inline script; add `.steps/.step` and `.nots/.not` CSS
- Test: `tests/test_landing_pages.py` (one more test)

- [ ] **Step 1: Write the failing test**: render `index.html`; assert no errors; "Your bank export becomes a Form 990-EZ draft", "Run it on your computer", "What this is not", "sent to Google's Gemini API" present; "Agents for Humans" appears exactly once; none of "gemini-3.5", "tool calls", "twelve rows", "conditional node", "free Gemini tier" present; link to `technical.html`; no dashes.
- [ ] **Step 2: Run.** Expected: FAIL on the hero sentence.
- [ ] **Step 3: Rewrite** nav, hero, sections in spec order (What you get with Part I "How it was decided", How it works in four steps, When the readers disagree, Is the math right, What this is not with the README's five limitations, Get started with the data note and `streamlit run app.py`), footer with the technical link and the one hackathon line. Script: chips in treasurer words, rows with "Both readers agreed on N" / "N settled by the Referee", disputes with "Preparer said / Reviewer said / Referee chose", accuracy sentence from validation, mismatch note.
- [ ] **Step 4: Run** build_landing, then `PYTHONPATH=src python -m pytest tests/test_landing_pages.py tests/test_build_landing.py -v`. Expected: 4 passed.
- [ ] **Step 5: Screenshot check** at 1440 and 390: no horizontal overflow, no JS errors.
- [ ] **Step 6: Commit** `feat(landing): written for the treasurer; engineering material moved to technical.html`.

### Task 4: README and PRODUCT.md agree with the page

- [ ] **Step 1: README "Live demo"**: product page URL, technical page URL, app not hosted yet.
- [ ] **Step 2: PRODUCT.md "Users"**: treasurers primary; judges read the same page for criteria 2, 3, 5 and `technical.html`, README, diagram for 1 and 4.
- [ ] **Step 3:** `PYTHONPATH=src python -m pytest -q` all pass; commit `docs: point README and PRODUCT.md at the treasurer page and the technical page`; push; confirm both live URLs return 200 and the hero sentence is live.
