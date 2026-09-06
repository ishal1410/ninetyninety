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
    from pypdf import PdfReader

    from ninetyninety.pdffill import download_form, fill_form
    from ninetyninety.prepare import Form990EZ

    template = download_form(tmp_path.parent / "f990ez.pdf")
    out = fill_form(Form990EZ(totals={"line9": 0, "line17": 0, "line18": 0}),
                    template, tmp_path / "draft.pdf", "ORG", "00-0000000")
    for page in PdfReader(str(out)).pages:
        notices = [a.get_object() for a in page.get("/Annots", [])
                   if a.get_object().get("/Subtype") == "/FreeText"]
        assert any("DRAFT" in str(n.get("/Contents")) for n in notices)
