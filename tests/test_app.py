"""The Streamlit app, run headless through streamlit.testing.v1.AppTest.

Each test pins one of the 2026-09-08 bug-hunter findings against app.py.
"""
import tempfile
import threading
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ninetyninety.agents import RowCall
from ninetyninety.ledger import Transaction
from ninetyninety.prepare import Form990EZ, assemble

APP = Path(__file__).resolve().parent.parent / "app.py"


def run_app():
    return AppTest.from_file(str(APP), default_timeout=120).run()


def markdown_text(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def fake_form(trace=None) -> Form990EZ:
    tx = Transaction(date="2025-01-01", description="DONATION", amount=100, source_row=2)
    good = RowCall(row=2, line="1", rule="Voluntary transfers where the donor receives nothing",
                   why="w", confidence="high")
    form = assemble([(tx, good, good)], {})
    form.trace = trace or []
    return form


def test_disagreement_lines_from_the_agents_are_html_escaped():
    tx = Transaction(date="2025-01-01", description="X", amount=100, source_row=2)
    evil = RowCall(row=2, line="<img src=x onerror=alert(1)>", rule="r", why="w", confidence="high")
    good = RowCall(row=2, line="1", rule="Voluntary transfers where the donor receives nothing",
                   why="w", confidence="high")
    form = assemble([(tx, evil, good)], {})
    assert form.disagreements[0]["preparer"] == evil.line
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.session_state["draft"] = {"form": form, "skipped": [], "loaded": 1, "pdf": None,
                                 "pdf_error": "skipped", "recorded": False}
    at.run()
    text = markdown_text(at)
    assert "<img src=x" not in text
    assert "&lt;img src=x" in text


def test_replay_caption_survives_a_rerun():
    at = run_app()
    at.button[1].click().run()
    assert any("Recorded on" in c.value for c in at.caption)
    at.text_input[1].set_value("11-1111111").run()
    assert any("Recorded on" in c.value for c in at.caption)


def test_a_failed_live_draft_does_not_leave_the_previous_draft_on_screen(monkeypatch):
    from ninetyninety import prepare

    def boom(*a, **k):
        raise RuntimeError("provider down")
    at = run_app()
    at.button[1].click().run()
    assert "draft" in at.session_state
    monkeypatch.setattr(prepare, "prepare_ledger", boom)
    at.button[0].click().run()
    assert at.error and "provider down" in at.error[0].value
    assert "draft" not in at.session_state


def test_partial_quota_exhaustion_is_warned_and_model_calls_drawn(monkeypatch):
    from ninetyninety import prepare
    trace = [{"batch": 1, "rows": 12, "provider": "gemini:a", "nodes": ["preparer", "reviewer"],
              "referee_ran": False, "tool_calls": 18, "tool_calls_by_node": {"preparer": 9},
              "model_calls": {"preparer": 4, "reviewer": 3},
              "node_ms": {"preparer": 100.0, "reviewer": 90.0}, "seconds": 12.0},
             {"batch": 2, "rows": 42, "provider": "gemini:b",
              "error": "gemini:b exhausted: 429", "seconds": 1.0}]
    monkeypatch.setattr(prepare, "prepare_ledger", lambda *a, **k: fake_form(trace))
    at = run_app()
    at.button[0].click().run()
    assert at.warning and "42" in at.warning[0].value
    assert "7 model calls, counted by Strands hooks" in markdown_text(at)


def test_live_draft_runs_off_the_script_thread_with_the_shared_host_caps(monkeypatch):
    from ninetyninety import prepare
    seen = {}

    def fake(transactions, **kwargs):
        seen["thread"] = threading.current_thread().name
        seen["kwargs"] = kwargs
        return fake_form()
    monkeypatch.setattr(prepare, "prepare_ledger", fake)
    at = run_app()
    at.button[0].click().run()
    assert not at.exception
    assert "draft" in at.session_state
    assert seen["thread"] != threading.main_thread().name
    assert seen["kwargs"]["max_rows"] == 60 and seen["kwargs"]["exclusive"] is True


def test_a_ledger_with_no_readable_rows_is_an_error(monkeypatch):
    from ninetyninety import ledger
    monkeypatch.setattr(ledger, "load_ledger", lambda path, skipped=None: [])
    at = run_app()
    at.button[0].click().run()
    assert at.error and "No readable rows" in at.error[0].value
    assert "draft" not in at.session_state


def test_replay_leaves_no_temp_directory_behind():
    def dirs():
        return {p.name for p in Path(tempfile.gettempdir()).glob("ninetyninety-*")}
    before = dirs()
    at = run_app()
    at.button[1].click().run()
    assert at.session_state["draft"]["pdf"] is not None
    assert dirs() == before


def test_trace_is_a_full_width_dataframe_and_graph_fits_its_viewbox():
    at = run_app()
    at.button[1].click().run()
    assert len(at.dataframe) == 1 and len(at.table) == 0
    assert 'viewBox="0 0 520 230"' in markdown_text(at)


def test_no_empty_heading_and_the_anchor_sits_on_the_real_heading():
    at = run_app()
    assert len(at.subheader) == 0
    assert 'id="draft-a-return"' in markdown_text(at)


def css_rule(css: str, selector: str) -> str:
    """The declaration block for one selector in the page stylesheet."""
    start = css.index(selector + "{") + len(selector) + 1
    return css[start:css.index("}", start)]


def test_the_footer_comes_after_the_tool_not_in_the_middle_of_the_page():
    at = run_app()
    blocks = [m.value for m in at.markdown]
    foot = next(i for i, b in enumerate(blocks) if 'class="foot"' in b)
    tool = next(i for i, b in enumerate(blocks) if 'id="draft-a-return"' in b)
    assert foot > tool


# --- the Federal Register interface, 2026-09-09 -----------------------------

def test_the_app_opens_on_the_product_not_a_marketing_scroll():
    at = run_app()
    page = markdown_text(at)
    for gone in ('class="hero"', 'class="marq"', 'class="bento"',
                 'class="card"', 'class="act"', "position:sticky"):
        assert gone not in page, gone
    blocks = [m.value for m in at.markdown]
    mast = next(i for i, b in enumerate(blocks) if 'class="mast"' in b)
    tool = next(i for i, b in enumerate(blocks) if 'id="draft-a-return"' in b)
    assert mast < tool
    assert "OMB No. 1545-0047" in blocks[mast]


def test_the_page_is_set_in_the_federal_typeface():
    at = run_app()
    css = at.markdown[0].value
    assert "family=Public+Sans" in css
    assert "--sans:'Public Sans'" in css
    assert "Outfit" not in css


def test_one_accent_and_a_measured_palette():
    at = run_app()
    root = css_rule(at.markdown[0].value, ":root")
    for token, value in (("--paper", "#FFFFFF"), ("--ink", "#1B1B1B"),
                         ("--muted", "#565C65"), ("--accent", "#005EA2"),
                         ("--notice", "#B50909"), ("--control", "#8D9297")):
        assert f"{token}:{value}" in root, token
    assert "#62D39A" not in at.markdown[0].value


def test_the_document_has_corners():
    at = run_app()
    css = at.markdown[0].value
    assert "border-radius:2px" in css
    for big in ("border-radius:18px", "border-radius:14px", "border-radius:999px"):
        assert big not in css, big


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


def test_the_adjudication_record_marks_the_column_that_reached_the_form():
    at = run_app()
    at.button[1].click().run()
    text = markdown_text(at)
    assert 'class="adj"' in text
    assert 'class="col win"' in text and 'class="col out"' in text
    assert "On the form" in text


def test_the_result_columns_stack_and_the_graph_keeps_its_size():
    at = run_app()
    css = at.markdown[0].value
    block = css[css.index("@media (max-width:1100px)"):]
    block = block[:block.index("@media (max-width:600px)")]
    assert "stHorizontalBlock" in block and "flex-wrap:wrap" in block
    assert "min-width:100%" in block
    svg = css_rule(css, ".graph svg")
    assert "max-width:520px" in svg and "min-width:430px" in svg


def test_the_phone_rules_come_last_so_they_win_the_cascade():
    at = run_app()
    css = at.markdown[0].value
    phone = css.index("@media (max-width:600px)")
    assert phone > css.index("table.ledger td.amt{width:8rem")
    block = css[phone:]
    assert "table.ledger td.cnt{display:none}" in block
    assert "table.ledger td.amt{width:6rem}" in block


def test_the_proof_line_names_line_9_and_does_not_claim_whole_returns():
    at = run_app()
    text = markdown_text(at)
    assert "Line 9 rebuilt exactly in" in text
    assert "returns checked from the IRS e-file corpus" in text
    for overclaim in ("returns rebuilt exactly",
                      "The arithmetic that fills this form"):
        assert overclaim not in text, overclaim


def test_the_strip_shows_a_real_recorded_row():
    # Fixture constants from results/demo_run.json, deliberately not derived through the code.
    line_number = "1"
    transaction_description = "ONLINE DONATION STRIPE PAYOUT BATCH 4471"
    rule_beginning = "Voluntary transfers where the donor receives nothing"

    at = run_app()
    page = markdown_text(at)
    assert 'class="lands"' in page
    strip = page[page.index('class="lands"'):page.index('class="proof"')]
    assert transaction_description in strip
    assert rule_beginning in strip
    # Closing tag included: a loose "Line 1" also matches proof()'s "Line 17".
    assert f">Line {line_number}</b>" in strip


def test_the_hero_never_prints_a_line_total():
    # Fixture constants from results/demo_run.json, deliberately not derived through the code.
    transaction_amount_formatted = "1,250"
    line_total_formatted = "9,100"

    at = run_app()
    page = markdown_text(at)
    strip = page[page.index('class="lands"'):page.index('class="proof"')]
    assert transaction_amount_formatted in strip
    assert line_total_formatted not in strip
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
