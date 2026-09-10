from pathlib import Path

from ninetyninety.lines import ALL_LINE_NUMBERS
from ninetyninety.pdffill import field_map


def test_field_map_covers_every_part_one_line():
    mapping = field_map()
    for number in ALL_LINE_NUMBERS:
        assert number in mapping, f"line {number} has no PDF field"


def test_field_map_includes_the_three_totals_and_the_header():
    mapping = field_map()
    for key in ("line9", "line17", "line18", "org_name", "ein"):
        assert key in mapping


def test_field_names_are_non_empty_strings():
    for name in field_map().values():
        assert isinstance(name, str) and name.strip()


def test_filled_pdf_carries_a_visible_draft_notice_on_every_page(tmp_path):
    import pytest
    from pypdf import PdfReader

    from ninetyninety.pdffill import fill_form
    from ninetyninety.prepare import Form990EZ

    template = Path("data/f990ez.pdf")
    if not template.exists():
        pytest.skip("blank IRS form not downloaded; run scripts/dump_fields.py")
    out = fill_form(Form990EZ(totals={"line9": 0, "line17": 0, "line18": 0}),
                    template, tmp_path / "draft.pdf", "ORG", "00-0000000")
    for page in PdfReader(str(out)).pages:
        notices = [a.get_object() for a in page.get("/Annots", [])
                   if a.get_object().get("/Subtype") == "/FreeText"]
        assert any("DRAFT" in str(n.get("/Contents")) for n in notices)


def test_download_form_leaves_nothing_behind_when_the_request_fails(tmp_path, monkeypatch):
    import pytest
    from ninetyninety import pdffill

    class Broken:
        content = b"half"

        def raise_for_status(self):
            raise ConnectionError("dropped")

    monkeypatch.setattr(pdffill.requests, "get", lambda *a, **k: Broken())
    dest = tmp_path / "f990ez.pdf"
    with pytest.raises(ConnectionError):
        pdffill.download_form(dest)
    assert not dest.exists() and not list(tmp_path.iterdir())


def test_two_sessions_can_download_the_form_at_once(tmp_path, monkeypatch):
    import threading
    from ninetyninety import pdffill

    class Slow:
        content = b"%PDF-fake"

        def raise_for_status(self):
            pass

    def get(url, timeout):
        threading.Event().wait(0.2)
        return Slow()
    monkeypatch.setattr(pdffill.requests, "get", get)
    dest = tmp_path / "f990ez.pdf"
    errors = []

    def worker():
        try:
            pdffill.download_form(dest)
        except Exception as e:  # noqa: BLE001
            errors.append(e)
    threads = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert dest.read_bytes() == b"%PDF-fake"
    assert [p.name for p in tmp_path.iterdir()] == ["f990ez.pdf"]


def _draft_notices(page):
    return [a.get_object() for a in page.get("/Annots", [])
            if a.get_object().get("/Subtype") == "/FreeText"
            and "DRAFT" in str(a.get_object().get("/Contents"))]


def _drawn(page):
    """What a viewer actually paints: /Contents is inert, the /AP stream is not."""
    return _draft_notices(page)[0]["/AP"]["/N"].get_data().decode("cp1252")


def _fill(tmp_path, form=None, **kwargs):
    import pytest

    from ninetyninety.pdffill import fill_form
    from ninetyninety.prepare import Form990EZ

    template = Path("data/f990ez.pdf")
    if not template.exists():
        pytest.skip("blank IRS form not downloaded; run scripts/dump_fields.py")
    form = form or Form990EZ(totals={"line9": 0, "line17": 0, "line18": 0})
    return fill_form(form, template, tmp_path / "draft.pdf", "ORG", "00-0000000", **kwargs)


def _form(rows, **kwargs):
    from ninetyninety.prepare import Form990EZ
    return Form990EZ(totals={"line9": 0, "line17": 0, "line18": 0},
                     trace=[{"rows": rows}], **kwargs)


def test_draft_notice_is_drawn_by_an_appearance_stream_on_every_page(tmp_path):
    from pypdf import PdfReader

    out = _fill(tmp_path)
    for page in PdfReader(str(out)).pages:
        assert _draft_notices(page), "no DRAFT annotation on this page"
        assert "DRAFT - NOT A FILING" in _drawn(page)


def test_the_notice_is_flagged_to_print(tmp_path):
    """Without the Print bit a conforming reader must not print the annotation,
    so the copy mailed to the board would be a clean, complete-looking form."""
    from pypdf import PdfReader

    out = _fill(tmp_path)
    for page in PdfReader(str(out)).pages:
        assert int(_draft_notices(page)[0]["/F"]) & 4


def test_the_default_appearance_names_a_font(tmp_path):
    """pypdf writes colour only. A viewer that regenerates the appearance with
    no Tf in /DA has no font to select -- the empty red box returns."""
    from pypdf import PdfReader

    notice = _draft_notices(PdfReader(str(_fill(tmp_path))).pages[0])[0]
    assert "Tf" in str(notice["/DA"])


def test_a_truncated_ledger_says_so_on_the_pdf_itself(tmp_path):
    from pypdf import PdfReader

    out = _fill(tmp_path, form=_form(60), rows_total=500)
    drawn = _drawn(PdfReader(str(out)).pages[0])
    assert "covers 60 of 500 rows" in drawn
    assert "Totals INCOMPLETE" in drawn


def test_unclassified_rows_are_named_on_the_pdf(tmp_path):
    from pypdf import PdfReader

    form = _form(54, unclassified=[{"source_row": 3}, {"source_row": 4}])
    drawn = _drawn(PdfReader(str(_fill(tmp_path, form=form, rows_total=54))).pages[0])
    assert "2 rows unclassified" in drawn


def test_one_unclassified_row_reads_as_singular(tmp_path):
    from pypdf import PdfReader

    form = _form(54, unclassified=[{"source_row": 3}])
    drawn = _drawn(PdfReader(str(_fill(tmp_path, form=form, rows_total=54))).pages[0])
    assert "1 row unclassified" in drawn and "1 rows" not in drawn


def test_a_complete_ledger_makes_no_incompleteness_claim(tmp_path):
    from pypdf import PdfReader

    drawn = _drawn(PdfReader(str(_fill(tmp_path, form=_form(54), rows_total=54))).pages[0])
    assert "INCOMPLETE" not in drawn and "DRAFT - NOT A FILING" in drawn


def test_coverage_counts_the_form_not_the_callers_ledger(tmp_path):
    """The replay path reads its transactions from the fixture CSV and its form
    from demo_run.json. rows_read must come off the form, or the PDF describes
    a run it is not showing."""
    from pypdf import PdfReader

    drawn = _drawn(PdfReader(str(_fill(tmp_path, form=_form(54), rows_total=61))).pages[0])
    assert "covers 54 of 61 rows" in drawn


def test_the_notice_never_grows_into_the_form_title():
    """The box hangs from y=786 and grows down. 756 is the two-line-at-9pt
    bottom, checked against a rendered page: the band clears the form's own
    masthead. Any notice that pushes below it starts covering "Form 990-EZ"."""
    from ninetyninety.pdffill import (DRAFT_NOTICE, NOTICE_MAX_LINES,
                                      NOTICE_TOP, NOTICE_WIDTH, _coverage_note,
                                      _fit)

    # A big nonprofit's year, generously: a five-figure ledger, 60 rows a spent
    # quota could not classify.
    worst = DRAFT_NOTICE + _coverage_note(
        _form(60, unclassified=[{"source_row": n} for n in range(60)]), 99999)
    lines, size = _fit(worst, NOTICE_WIDTH - 8)
    assert len(lines) <= NOTICE_MAX_LINES
    assert NOTICE_TOP - (len(lines) * (size + 2) + 8) >= 756


def test_the_notice_survives_typographic_punctuation():
    """cp1252 covers every curly quote and dash the declared /WinAnsiEncoding
    font can render; latin-1 raises on all of them."""
    from ninetyninety.pdffill import _fit, _pdf_escape

    lines, _ = _fit("DRAFT — NOT A FILING. An officer’s signature is required.", 532)
    joined = "\n".join(_pdf_escape(line) for line in lines)
    assert "—" in joined and "’" in joined
    joined.encode("cp1252")  # raises on latin-1, which is the bug this guards


def test_the_notice_is_never_truncated(tmp_path):
    """An appearance stream clips to its BBox, so an over-long line vanishes
    mid-word and still looks deliberate. Dropping "INCOMPLETE" off the end of
    an incompleteness warning is the worst failure this file can have."""
    from pypdf import PdfReader

    form = _form(60, unclassified=[{"source_row": n} for n in range(999)])
    out = _fill(tmp_path, form=form, rows_total=9999999)
    drawn = _drawn(PdfReader(str(out)).pages[0])
    notice = _draft_notices(PdfReader(str(out)).pages[0]).pop().get("/Contents")
    for word in str(notice).split():
        assert word in drawn, f"{word!r} was clipped out of the rendered notice"
