# App Hero: Transformation Strip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the app's scanned-JPEG hero with a strip showing one real recorded ledger row becoming the Form 990-EZ line it lands on, and give the page the visual weight it currently lacks.

**Architecture:** Presentation only, all inside `app.py`. `empty_state()` splits into `hero()` (always rendered, above the controls) and `explainer()` (rendered only when no draft exists). The strip reads one row verbatim from `results/demo_run.json`, loaded once at module level with the same `if path.exists()` guard `report` already uses. CSS gains a solid ink masthead band, a 1.3rem hero lede on its own class, and 3px zone rules; the existing hairlines survive only inside the form sheet.

**Tech Stack:** Python 3.12, Streamlit, `streamlit.testing.v1.AppTest`, pytest. No new dependencies.

Spec: `docs/superpowers/specs/2026-09-09-app-hero-redesign-design.md`

## Global Constraints

- Nothing in `src/ninetyninety/` changes. Presentation only.
- No new colour. The palette stays `--paper #FFFFFF`, `--ink #1B1B1B`, `--muted #565C65`, `--accent #005EA2`, `--notice #B50909`, `--control #8D9297`. `tests/test_app.py::test_one_accent_and_a_measured_palette` enforces this.
- Typefaces stay Public Sans and IBM Plex Mono. `test_the_page_is_set_in_the_federal_typeface` enforces this.
- The strip's wrapper class is `.lands`, never `.hero`. `class="hero"` is banned on purpose, to stop the app drifting back to the marketing page that was rejected twice.
- `border-radius:2px` only. No radius above 2px. `test_the_document_has_corners` enforces this.
- The hero must never print a form line's total. Only the row's own amount, labelled `this row`.
- The proof copy must contain "Line 9" and "checked", and must never say "returns rebuilt exactly".
- `p.lede` keeps `font-size:.93rem`. It has four call sites and enlarging it undoes commit `6745fb5`.
- `assets/draft-page1.jpg` stays on disk. `index.html:22` and `index.html:271` still use it.
- Every result view (form sheet, provenance, graph, adjudication) is untouched.

---

### Task 1: Correct the proof copy

The current sentence claims "The arithmetic that fills this form was run against 3,632 real filed returns… It rebuilt line 9 in 3,632 of 3,632". Reworded so the claim is line-scoped and the word "checked" survives, and extracted into its own function so the hero can use it in Task 2.

**Files:**
- Modify: `app.py:278-305` (inside `empty_state()`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: module-level `report`, already loaded at `app.py:248-251`.
- Produces: `proof() -> str`, returning one `<p class="proof">` element. Task 2 calls it.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py`:

```python
def test_the_proof_line_names_line_9_and_does_not_claim_whole_returns():
    at = run_app()
    text = markdown_text(at)
    assert "Line 9 rebuilt exactly in" in text
    assert "returns checked from the IRS e-file corpus" in text
    for overclaim in ("returns rebuilt exactly",
                      "The arithmetic that fills this form"):
        assert overclaim not in text, overclaim
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app.py::test_the_proof_line_names_line_9_and_does_not_claim_whole_returns -v`
Expected: FAIL, `AssertionError` on `"Line 9 rebuilt exactly in" in text`.

- [ ] **Step 3: Add `proof()` above `empty_state()`**

Insert immediately before `def empty_state() -> str:` in `app.py`:

```python
def proof() -> str:
    """The validation numbers, stated at the width they were measured: line by
    line, against the returns actually checked, never the whole return."""
    def got(kind: str, field: str, fallback: str) -> str:
        return f"{report[kind][field]:,}" if report else fallback
    m9, c9 = got("matched", "line9", "3,632"), got("checked", "line9", "3,632")
    m17, c17 = got("matched", "line17", "3,617"), got("checked", "line17", "3,618")
    m18, c18 = got("matched", "line18", "3,619"), got("checked", "line18", "3,621")
    return (f'<p class="proof">Line 9 rebuilt exactly in <b class="num">{m9}</b> of '
            f'<b class="num">{c9}</b> returns checked from the IRS e-file corpus. '
            f'Line 17: <b class="num">{m17}</b> of <b class="num">{c17}</b>. '
            f'Line 18: <b class="num">{m18}</b> of <b class="num">{c18}</b>. '
            f'The misses are returns whose own stated totals disagree with their '
            f'own line items.</p>')
```

- [ ] **Step 4: Use it in `empty_state()`**

Delete these lines from the top of `empty_state()`:

```python
    checked = f"{report['checked']['line9']:,}" if report else "3,632"

    def got(kind: str, field: str, fallback: str) -> str:
        return f"{report[kind][field]:,}" if report else fallback
    m9, c9 = got("matched", "line9", "3,632"), got("checked", "line9", "3,632")
    m17, c17 = got("matched", "line17", "3,617"), got("checked", "line17", "3,618")
    m18, c18 = got("matched", "line18", "3,619"), got("checked", "line18", "3,621")
```

so the function begins:

```python
def empty_state() -> str:
    """Shown until a draft exists: the real output, with what produced it."""
    steps = "".join(f'<div class="step"><h4>{h}</h4><p>{p}</p></div>' for h, p in STEPS)
```

Then replace this block in the returned f-string:

```html
  <div class="cert">
    <p>The arithmetic that fills this form was run against <b>{checked}</b> real filed
    Form 990-EZ returns from the IRS e-file corpus. It rebuilt line 9 in
    <b class="num">{m9}</b> of <b class="num">{c9}</b>, line 17 in
    <b class="num">{m17}</b> of <b class="num">{c17}</b>, and line 18 in
    <b class="num">{m18}</b> of <b class="num">{c18}</b>. The misses are returns
    whose own stated totals disagree with their own line items.</p>
  </div>
```

with:

```html
  <div class="cert">{proof()}</div>
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_app.py -q`
Expected: PASS, 19 passed.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "fix(copy): the proof line claims a line, not a whole return"
```

---

### Task 2: The transformation strip

**Files:**
- Modify: `app.py:26` region (module load), `app.py:76-78` (font selector list), the masthead CSS block, `app.py:315` (masthead call), `app.py:385` (`with body:`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `proof()` from Task 1; `form_order` and `line_by_number`, already imported at `app.py:24`; `esc()` at `:38`; `money()` at `:42`.
- Produces: `recorded_rows: dict | None`, `hero_row() -> tuple[str, dict] | None`, `hero() -> str`. Task 3 relies on `hero()` rendering the `<h1>` and lede so `empty_state()` can stop rendering them.

- [ ] **Step 1: Write the three failing tests**

Add `import json` to the imports at the top of `tests/test_app.py`, and add `from ninetyninety.lines import form_order` beside the other `ninetyninety` imports. Then append:

```python
def recorded_first_row():
    """The row the strip is specified to show: the first classified row of the
    recorded run, in Form 990-EZ Part I order."""
    data = json.loads((APP.parent / "results" / "demo_run.json").read_text(encoding="utf-8"))
    number = next(n for n in sorted(data["lines"], key=form_order)
                  if data["lines"][n]["transactions"])
    return number, data["lines"][number]


def test_the_strip_shows_a_real_recorded_row():
    number, line = recorded_first_row()
    tx = line["transactions"][0]
    at = run_app()
    text = markdown_text(at)
    assert 'class="lands"' in text
    assert tx["description"] in text
    assert tx["rule"][:60] in text
    assert f"Line {number}" in text


def test_the_hero_never_prints_a_line_total():
    number, line = recorded_first_row()
    at = run_app()
    page = markdown_text(at)
    strip = page[page.index('class="lands"'):page.index('class="proof"')]
    assert f"{line['transactions'][0]['amount']:,}" in strip
    assert f"{line['amount']:,}" not in strip
    assert "this row" in strip


def test_the_page_boots_without_the_recorded_run():
    path = APP.parent / "results" / "demo_run.json"
    hidden = path.with_name("demo_run.json.hidden")
    path.rename(hidden)
    try:
        at = run_app()
        assert not at.exception
        text = markdown_text(at)
        assert 'class="lands"' not in text
        assert "A bank export goes in." in text
    finally:
        hidden.rename(path)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_app.py -k "strip_shows or line_total or boots_without" -v`
Expected: 3 FAIL — `'class="lands"' in text` is False, and `page.index('class="lands"')` raises `ValueError: substring not found`.

- [ ] **Step 3: Load the recorded run at module level**

In `app.py`, immediately after the existing block at `:248-251`:

```python
report = None
report_path = BASE / "results" / "validation.json"
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
```

add:

```python
# Same idiom as report above: the hosted app must still boot if the recorded
# run is absent, it just loses the strip.
recorded_rows = None
demo_run_path = BASE / "results" / "demo_run.json"
if demo_run_path.exists():
    recorded_rows = json.loads(demo_run_path.read_text(encoding="utf-8"))["lines"]
```

- [ ] **Step 4: Add `hero_row()` and `hero()`**

Insert immediately after `proof()` in `app.py`:

```python
def hero_row() -> tuple[str, dict] | None:
    """The first classified row of the recorded run, in form order. Real output
    from a real Gemini run: description, amount and the rule the model quoted,
    all verbatim."""
    if not recorded_rows:
        return None
    for number in sorted(recorded_rows, key=form_order):
        transactions = recorded_rows[number]["transactions"]
        if transactions:
            return number, transactions[0]
    return None


def hero() -> str:
    """The page's one loud element: a line of a bank export becoming the form
    line it lands on, with the instruction that put it there."""
    row, strip = hero_row(), ""
    if row is not None:
        number, tx = row
        # The row's own amount only. The line's total belongs to the drafted
        # form; printing it here would read as this row's figure.
        strip = f"""<div class="lands">
  <div class="from">
    <span class="who">one row of a bank export</span>
    <b>{esc(tx["date"])}</b>
    <span class="desc">{esc(tx["description"])}</span>
    <span class="amt num">{money(tx["amount"])}</span>
  </div>
  <div class="arrow" aria-hidden="true"></div>
  <div class="to">
    <span class="who">the line, and the instruction that put it there</span>
    <b class="num">Line {esc(number)}</b>
    <span class="desc">{esc(line_by_number(number).label)}</span>
    <span class="rowamt"><span class="who">this row</span>
      <span class="num">{money(tx["amount"])}</span></span>
    <p class="rule">{esc(tx["rule"])}</p>
  </div>
</div>"""
    return f"""<div class="head">
  <h1>A bank export goes in. This comes back.</h1>
  <p class="hero-lede">Every figure on the drafted form cites the transactions behind it
  and the sentence of the IRS instructions that put them there. It is a draft for an
  officer to review and sign, never a filing.</p>
  {strip}
  {proof()}
</div>"""
```

- [ ] **Step 5: Add the strip CSS**

In the `CSS` string, immediately after the `.mast .omb{…}` rule, insert:

```css
/* The strip: one row of a bank export, and where it lands. */
.head h1{font-size:clamp(2.1rem,3.6vw,3.5rem);font-weight:800;letter-spacing:-.035em;
  line-height:1.02;color:var(--ink);margin:1.4rem 0 .9rem;max-width:18ch;text-wrap:balance}
p.hero-lede{font-size:1.3rem;line-height:1.45;color:var(--ink);max-width:52ch;margin:0 0 1.5rem}
.lands{display:grid;grid-template-columns:minmax(0,1fr) 3.5rem minmax(0,1.3fr);
  align-items:start;margin:0 0 1.3rem}
.lands .from,.lands .to{background:var(--paper);border:1px solid var(--ink);
  padding:.85rem 1rem .95rem}
.lands .to{border-left-width:3px}
.lands .who{display:block;font-size:.72rem;color:var(--muted);line-height:1.4;
  margin-bottom:.5rem}
.lands b{display:block;font-family:var(--mono);font-size:.86rem;font-weight:600;color:var(--ink)}
.lands .desc{display:block;font-size:.95rem;line-height:1.4;color:var(--ink);margin-top:.2rem}
.lands .from .amt{display:block;margin-top:.7rem;font-size:1.15rem;font-weight:600;
  text-align:right;color:var(--ink)}
.lands .rowamt{display:flex;justify-content:space-between;align-items:baseline;
  margin-top:.7rem;padding-top:.55rem;border-top:1px solid var(--rule)}
.lands .rowamt .who{margin:0}
.lands .rowamt .num{font-family:var(--mono);font-size:1.15rem;font-weight:600;color:var(--ink)}
.lands .rule{margin:.7rem 0 0;padding-top:.55rem;border-top:1px solid var(--rule);
  font-size:.82rem;line-height:1.5;color:var(--muted)}
.lands .arrow{align-self:center;height:1px;background:var(--ink);position:relative}
.lands .arrow::after{content:"";position:absolute;right:0;top:-4px;
  border-left:8px solid var(--ink);border-top:4px solid transparent;
  border-bottom:4px solid transparent}
p.proof{font-size:.95rem;line-height:1.6;color:var(--ink);max-width:70ch;margin:0}
p.proof b{font-weight:600}
```

Then extend the shared font-family selector list at `app.py:76-78`. It currently reads:

```css
.mast,.mast *,.intro,.intro *,.cert,.cert *,.shell,.shell *,.adj,.adj *,
.note,.note *,.graph,.graph *,.foot,.foot *,h2.sec,h3.sub,p.lede{
  font-family:var(--sans)}
```

Change it to:

```css
.mast,.mast *,.intro,.intro *,.cert,.cert *,.shell,.shell *,.adj,.adj *,
.note,.note *,.graph,.graph *,.foot,.foot *,.head,.head *,h2.sec,h3.sub,
p.lede,p.hero-lede,p.proof{
  font-family:var(--sans)}
```

- [ ] **Step 6: Move the masthead inside `body` and render the hero**

Delete this line at `app.py:315`:

```python
st.markdown(masthead(), unsafe_allow_html=True)
```

Change the opening of the body block from:

```python
pad_l, body, pad_r = st.columns([1, 12, 1])
with body:
    st.markdown('<h2 class="sec" id="draft-a-return">Draft a return</h2>'
```

to:

```python
pad_l, body, pad_r = st.columns([1, 12, 1])
with body:
    # Inside body, not above it: filled solid, a full-container masthead would
    # overhang the 12/14 content column by about 95px on each side.
    st.markdown(masthead() + hero(), unsafe_allow_html=True)
    st.markdown('<h2 class="sec" id="draft-a-return">Draft a return</h2>'
```

- [ ] **Step 7: Run the tests**

Run: `python -m pytest tests/test_app.py -q`
Expected: the 3 new tests PASS. `test_the_app_opens_on_the_product_not_a_marketing_scroll` and `test_the_empty_state_shows_the_real_drafted_form_and_then_makes_way` now FAIL — the masthead is no longer at `at.markdown[1]`, and the page renders both the strip and the old `.intro`. Both are rewritten in Task 3.

- [ ] **Step 8: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat(ui): the hero is a row of a bank export landing on its line"
```

---

### Task 3: Split the empty state and delete the JPEG

**Files:**
- Modify: `app.py:10` (import), `app.py:34-36` (`asset()`), `app.py:76-78`, the `.intro`/`.cert` CSS, `empty_state()`, `app.py:486`, the `@media (max-width:1100px)` block
- Test: `tests/test_app.py:153`, `tests/test_app.py:189`

**Interfaces:**
- Consumes: `hero()` from Task 2, which now renders the `<h1>` and the lede.
- Produces: `explainer() -> str`, one `<div class="steps">` element. Task 4 restyles it into three columns.

- [ ] **Step 1: Rewrite the two tests that pin the old structure**

In `tests/test_app.py`, replace `test_the_app_opens_on_the_product_not_a_marketing_scroll` with:

```python
def test_the_app_opens_on_the_product_not_a_marketing_scroll():
    at = run_app()
    page = at.markdown[0].value + markdown_text(at)
    for gone in ('class="hero"', 'class="marq"', 'class="bento"',
                 'class="card"', 'class="act"', "position:sticky"):
        assert gone not in page, gone
    # The masthead moved inside the body column, so match on content, not index.
    assert 'class="mast"' in markdown_text(at)
    assert "OMB No. 1545-0047" in markdown_text(at)
```

and replace `test_the_empty_state_shows_the_real_drafted_form_and_then_makes_way` with:

```python
def test_the_strip_stays_and_the_explainer_band_makes_way():
    at = run_app()
    text = markdown_text(at)
    assert 'class="steps"' in text
    # the scanned page render is gone from the app
    assert 'class="intro"' not in text and 'class="sheet"' not in text
    assert 'src="data:image/jpeg;base64,' not in text
    at.button[1].click().run()
    after = markdown_text(at)
    assert 'class="steps"' not in after
    assert 'class="lands"' in after, "the strip is the page's head, it stays"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_app.py -k "marketing_scroll or explainer_band" -v`
Expected: 2 FAIL — `'class="intro"' not in text` is False.

- [ ] **Step 3: Replace `empty_state()` with `explainer()`**

Delete the whole `empty_state()` function and put this in its place:

```python
def explainer() -> str:
    """Shown until a draft exists: how the graph reaches each line."""
    steps = "".join(f'<div class="step"><h4>{h}</h4><p>{p}</p></div>' for h, p in STEPS)
    return f'<div class="steps">{steps}</div>'
```

- [ ] **Step 4: Update the call site**

At `app.py:486`, change:

```python
    draft = st.session_state.get("draft")
    if not draft:
        st.markdown(empty_state(), unsafe_allow_html=True)
```

to:

```python
    draft = st.session_state.get("draft")
    if not draft:
        st.markdown(explainer(), unsafe_allow_html=True)
```

- [ ] **Step 5: Delete the dead helper and import**

Delete `import base64` from `app.py:10`, and delete the `asset()` function:

```python
@st.cache_data
def asset(name: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode((BASE / "assets" / name).read_bytes()).decode()
```

Confirm nothing else uses either.

Run: `grep -n "base64\|asset(" app.py`
Expected: no output.

- [ ] **Step 6: Delete the dead CSS**

Remove these rules from the `CSS` string:

```css
.intro{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:2.4rem;
  align-items:start;margin-top:1.3rem}
.intro .sheet{border:1px solid var(--rule);background:var(--paper);padding:6px}
.intro .sheet img{width:100%;display:block;border:1px solid var(--rule)}
.intro h1{font-size:clamp(2.1rem,3.6vw,3.5rem);font-weight:800;letter-spacing:-.035em;
  line-height:1.02;color:var(--ink);margin:0 0 .9rem;max-width:15ch;text-wrap:balance}
.cert{border-top:1px solid var(--ink);border-bottom:1px solid var(--rule);
  padding:.95rem 0 1rem;margin-top:1.5rem}
.cert p{font-size:.9rem;line-height:1.6;color:var(--muted);margin:0;max-width:62ch}
.cert b{color:var(--ink);font-weight:600}
.cert b.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
```

Unscope the step rules — `.intro .steps{…}` and `.intro .step{…}` become (they are restyled in Task 4; this step only unscopes them):

```css
.steps{margin-top:1.6rem;border-top:1px solid var(--rule)}
.step{padding:.9rem 0;border-bottom:1px solid var(--rule)}
.step h4{margin:0 0 .25rem;font-size:.95rem;font-weight:700;color:var(--ink);
  letter-spacing:-.01em}
.step p{font-size:.85rem;color:var(--muted);line-height:1.5;margin:0}
```

Remove `.intro,.intro *,.cert,.cert *,` from the shared font-family selector list and add `.steps,.steps *,`:

```css
.mast,.mast *,.steps,.steps *,.shell,.shell *,.adj,.adj *,
.note,.note *,.graph,.graph *,.foot,.foot *,.head,.head *,h2.sec,h3.sub,
p.lede,p.hero-lede,p.proof{
  font-family:var(--sans)}
```

Delete `.intro{grid-template-columns:1fr}` from the `@media (max-width:1100px)` block.

- [ ] **Step 7: Run the tests**

Run: `python -m pytest tests/test_app.py -q`
Expected: PASS, 22 passed.

- [ ] **Step 8: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "refactor(ui): the scanned page leaves the app, the band stays behind"
```

---

### Task 4: The weight pass

**Files:**
- Modify: `app.py` — the `.mast` CSS block, `p.lede`, `.steps`/`.step`, both media queries, the `FOOTER` constant region, the body block
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `.lands`, `p.hero-lede`, `p.proof` from Task 2; `.steps` from Task 3.
- Produces: `ZONE: str`, the literal `'<div class="zone"></div>'`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py`:

```python
def test_the_control_lede_keeps_its_size_and_the_hero_has_its_own():
    at = run_app()
    css = at.markdown[0].value
    # p.lede has four call sites; enlarging it undoes the control strip height
    assert "font-size:.93rem" in css_rule(css, "p.lede")
    assert "font-size:1.3rem" in css_rule(css, "p.hero-lede")


def test_the_masthead_is_a_filled_band_and_the_zones_are_ink():
    at = run_app()
    css = at.markdown[0].value
    assert "background:var(--ink)" in css_rule(css, ".mast")
    assert "height:3px" in css_rule(css, ".zone")


def test_the_controls_come_before_the_explainer_band():
    at = run_app()
    page = markdown_text(at)
    assert page.count('class="zone"') == 2
    assert page.index('class="steps"') > page.rindex('class="zone"')
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_app.py -k "keeps_its_size or filled_band or come_before" -v`
Expected: 3 FAIL — `background:var(--ink)` absent from the `.mast` block; `css_rule` raises `ValueError: substring not found` for `.zone{`; `page.count('class="zone"')` is 0.

- [ ] **Step 3: Fill the masthead band**

Replace the `.mast` rules in the `CSS` string:

```css
.mast{display:flex;align-items:baseline;gap:1.5rem;flex-wrap:wrap;
  padding:1.15rem 0 .95rem;border-bottom:2px solid var(--ink)}
.mast .mark{font-weight:800;font-size:1.32rem;letter-spacing:-.022em;color:var(--ink);line-height:1}
.mast .doc{font-weight:700;font-size:.95rem;color:var(--ink);letter-spacing:-.01em}
.mast .sub{font-size:.86rem;color:var(--muted)}
.mast .omb{margin-left:auto;font-size:.74rem;letter-spacing:.02em;color:var(--muted);
  text-transform:uppercase;border:1px solid var(--rule);background:var(--paper);padding:.3rem .55rem}
```

with:

```css
.mast{display:flex;align-items:baseline;gap:1.5rem;flex-wrap:wrap;
  padding:1.05rem 1.15rem .95rem;background:var(--ink)}
.mast .mark{font-weight:800;font-size:1.32rem;letter-spacing:-.022em;color:var(--paper);line-height:1}
.mast .doc{font-weight:700;font-size:.95rem;color:var(--paper);letter-spacing:-.01em}
.mast .sub{font-size:.86rem;color:#C9CDD2}
.mast .omb{margin-left:auto;font-size:.74rem;letter-spacing:.02em;color:#C9CDD2;
  text-transform:uppercase;border:1px solid #4A5056;background:transparent;padding:.3rem .55rem}
```

`#C9CDD2` on `#1B1B1B` measures about 10.5:1, well over the 4.5:1 floor. These two greys are masthead-local shades of the existing ink, not new palette tokens, so `test_one_accent_and_a_measured_palette` still passes — it asserts the `:root` block only.

- [ ] **Step 4: Add the zone rule, three-column band, and ink body copy**

Add to the `CSS` string, immediately after `p.proof b{…}`:

```css
/* Three regions, three rules. Hairlines are the form's own device and stay
   inside the form sheet; they do not divide the page. */
.zone{height:3px;background:var(--ink);margin:1.9rem 0 1.5rem}
```

Replace the unscoped step rules from Task 3 Step 6 with:

```css
.steps{display:grid;grid-template-columns:repeat(3,1fr);border-top:none;margin-top:0}
.step{padding:0 1.6rem 0 0;border-bottom:none;border-right:1px solid var(--rule)}
.step:last-child{border-right:none;padding-right:0}
.step h4{margin:0 0 .4rem;font-size:1rem;font-weight:700;color:var(--ink);letter-spacing:-.01em}
.step p{font-size:.88rem;color:var(--muted);line-height:1.55;margin:0}
```

Change `p.lede` so the copy carries ink, keeping its size:

```css
p.lede{font-size:.93rem;color:var(--ink);max-width:66ch;line-height:1.55;margin:0 0 .9rem}
```

- [ ] **Step 5: Emit the zone rules**

Add a module-level constant beside `FOOTER` in `app.py`:

```python
ZONE = '<div class="zone"></div>'
```

In the body block, change:

```python
    st.markdown(masthead() + hero(), unsafe_allow_html=True)
```

to:

```python
    st.markdown(masthead() + hero() + ZONE, unsafe_allow_html=True)
```

and immediately after the button row:

```python
    replay = b2.button("Replay the recorded run (no model calls)",
                       help="Shows the draft recorded on 2026-09-08 from the demo ledger through Google Gemini. "
                            "Same code path, no quota used. Use it if the free tier for the day is spent.")
```

add:

```python
    st.markdown(ZONE, unsafe_allow_html=True)
```

- [ ] **Step 6: Stack on a phone**

In the `@media (max-width:600px)` block, add:

```css
  .lands{grid-template-columns:1fr}
  .lands .arrow{display:none}
  .lands .to{border-left-width:1px;border-top-width:3px}
  .steps{grid-template-columns:1fr}
  .step{border-right:none;border-bottom:1px solid var(--rule);padding:.9rem 0}
  .step:last-child{border-bottom:none}
  p.hero-lede{font-size:1.1rem}
```

`test_the_phone_rules_come_last_so_they_win_the_cascade` requires the phone block to stay last in the stylesheet — add inside the existing block, do not append a new one after it.

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS, 129 passed, 1 skipped. (test_app.py goes 18 -> 22 -> 25; the suite's other 104 tests are untouched.)

- [ ] **Step 8: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat(ui): weight — an ink masthead, ink copy, three zone rules"
```

---

### Task 5: Measure it in a browser

`AppTest` is headless and has no layout engine, and the repo's only Playwright tests load static `file://` pages rather than a running Streamlit server. The fold budget and the strip's proportions are therefore verified by hand here, once, the same way the graph clipping was measured.

**Files:**
- Modify: `app.py` (only if a measurement fails)

**Interfaces:**
- Consumes: everything from Tasks 1-4. Produces nothing new.

- [ ] **Step 1: Start the app**

```bash
python -m streamlit run app.py --server.port 8511 --server.headless true
```

- [ ] **Step 2: Measure the fold at 1440×900**

Open `http://localhost:8511` at a 1440×900 viewport and run in the console:

```js
(() => {
  const replay = [...document.querySelectorAll('button')]
    .find(b => /Replay the recorded run/.test(b.innerText));
  const mast = document.querySelector('.mast');
  return {
    controlsVisibleBy: Math.round(replay.getBoundingClientRect().bottom),
    mastWidth: Math.round(mast.getBoundingClientRect().width),
    landsWidth: Math.round(document.querySelector('.lands').getBoundingClientRect().width),
  };
})()
```

Expected: `controlsVisibleBy` ≤ 620. `mastWidth` and `landsWidth` equal to within 2px — that is correction 5 holding.

If `controlsVisibleBy` exceeds 620, reduce `.head h1` `margin-top` and `p.hero-lede` `margin-bottom` until it fits. Do not cut the strip.

- [ ] **Step 3: Check for clipping and overflow**

```js
(() => {
  const over = [];
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 8 && r.right > innerWidth + 1) over.push(el.className);
    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== 'visible')
      over.push('CLIPS: ' + el.className);
  });
  return {overflow: over.slice(0, 10), docW: document.documentElement.scrollWidth, vw: innerWidth};
})()
```

Expected: `overflow: []` and `docW === vw`.

- [ ] **Step 4: Repeat at 1708×1000 and at a 390px-wide emulated phone**

Run both snippets again at each size. At 390px the strip must be one column with the arrow hidden, and `overflow` must still be empty.

- [ ] **Step 5: Click Replay and confirm the strip stays**

The strip, both zone rules and the full result view must all render, with no clipping and no horizontal scrollbar.

- [ ] **Step 6: Stop the server and commit any fixes**

```bash
git add app.py
git commit -m "fix(ui): measured corrections to the hero fold"
```

---

## Verification

Run before calling this done:

```bash
python -m pytest tests/ -q
grep -n "base64\|asset(\|empty_state\|class=\"intro\"\|class=\"cert\"" app.py
grep -c "draft-page1" index.html
```

Expected: `129 passed, 1 skipped`; no output from the second command; `2` from the third, proving the landing page still has its image.
