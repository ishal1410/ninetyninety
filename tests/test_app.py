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


def test_copy_counts_checkable_returns_and_spells_organization_us_style():
    at = run_app()
    text = markdown_text(at)
    assert "3,687 real IRS returns re-computed" not in text
    assert "3,632 real IRS returns re-computed" in text
    assert at.text_input[0].label == "Organization name for the PDF"


def test_mobile_css_rules_are_present():
    at = run_app()
    css = at.markdown[0].value
    nav = css[css.index(".nav{"):css.index("}", css.index(".nav{"))]
    assert "width:max-content" in nav and "white-space:nowrap" in nav
    assert ".block-container{max-width:100%;padding:0 1rem 6rem}" in css
    assert "table.ledger tr.empty td{color:var(--muted)}" in css


def css_rule(css: str, selector: str) -> str:
    """The declaration block for one selector in the page stylesheet."""
    start = css.index(selector + "{") + len(selector) + 1
    return css[start:css.index("}", start)]


def test_the_nav_pill_scrolls_away_instead_of_floating_over_the_results():
    at = run_app()
    css = at.markdown[0].value
    assert "position:absolute" in css_rule(css, ".nav")
    assert "position:relative" in css_rule(css, ".nn")


def test_the_two_result_columns_stack_before_the_ledger_label_is_crushed():
    at = run_app()
    css = at.markdown[0].value
    block = css[css.index("@media (max-width:1100px)"):]
    block = block[:block.index("\n")]
    assert 'stHorizontalBlock' in block and "flex-wrap:wrap" in block
    assert "min-width:100%" in block


def test_the_graph_never_renders_smaller_than_its_designed_size():
    at = run_app()
    css = at.markdown[0].value
    assert "overflow-x:auto" in css_rule(css, ".graph")
    svg = css_rule(css, ".graph svg")
    assert "max-width:520px" in svg and "min-width:420px" in svg


def test_the_hero_form_image_starts_below_the_buttons_on_a_phone():
    at = run_app()
    css = at.markdown[0].value
    block = css[css.index("@media (max-width:900px)"):]
    block = block[:block.index("\n")]
    assert ".hero .bg{top:76%}" in block


def test_the_ledger_gives_the_line_label_room_on_a_phone():
    at = run_app()
    css = at.markdown[0].value
    block = css[css.index("@media (max-width:600px)"):]
    block = block[:block.index("\n")]
    # 3.4 + 6.5 + 9 rem of fixed columns leaves a 390px phone 109px for the label
    assert "table.ledger td.cnt{display:none}" in block
    assert "table.ledger td.amt{width:6.2rem}" in block
    assert "table.ledger td.n{width:2.4rem}" in block
    # equal specificity, so the phone block only wins if it comes last
    assert css.index("@media (max-width:600px)") > css.index("table.ledger td.amt{width:9rem;")
