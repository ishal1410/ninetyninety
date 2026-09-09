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
