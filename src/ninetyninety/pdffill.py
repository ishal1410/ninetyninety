"""Fill the real IRS Form 990-EZ AcroForm.

The blank form has 385 fields. FIELD_MAP is populated from the exact names
printed by scripts/dump_fields.py -- never guess them.

Output is always a DRAFT: e-filing requires an Authorized IRS e-File Provider
EFIN, which this project does not have.
"""
import os
import textwrap
import threading
import uuid
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText
from pypdf.constants import AnnotationFlag
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

FORM_URL = "https://www.irs.gov/pub/irs-pdf/f990ez.pdf"
DRAFT_NOTICE = ("DRAFT - NOT A FILING. Prepared by NinetyNinety for officer review. "
                "An officer must review and sign; e-filing requires an IRS e-File Provider.")

# Keys are our line numbers plus "line9"/"line17"/"line18"/"org_name"/"ein".
# Values are exact AcroForm field names from scripts/dump_fields.py, mapped
# by widget geometry on 2026-09-06 (the form carries no tooltips): each Part I
# label's text baseline sits 3pt above the bottom edge of its amount box.
_P1 = "topmostSubform[0].Page1[0]."
FIELD_MAP: dict[str, str] = {
    "org_name": _P1 + "LineC[0].p1-t4[0]",   # C Name of organization
    "ein": _P1 + "p1-t9[0]",                 # D Employer identification number
    "1": _P1 + "p1-t16[0]",
    "2": _P1 + "p1-t17[0]",
    "3": _P1 + "p1-t18[0]",
    "4": _P1 + "p1-t19[0]",
    "5c": _P1 + "p1-t22[0]",
    "6d": _P1 + "p1-t101[0]",
    "7c": _P1 + "p1-t29[0]",
    "8": _P1 + "p1-t31[0]",
    "line9": _P1 + "p1-t32[0]",
    "10": _P1 + "p1-t33[0]",
    "11": _P1 + "p1-t34[0]",
    "12": _P1 + "p1-t35[0]",
    "13": _P1 + "p1-t36[0]",
    "14": _P1 + "p1-t37[0]",
    "15": _P1 + "p1-t38[0]",
    "16": _P1 + "p1-t40[0]",
    "line17": _P1 + "p1-t41[0]",
    "line18": _P1 + "p1-t42[0]",
}


NOTICE_RED = (0.753, 0.0, 0.0)      # c00000
NOTICE_BG = (1.0, 0.949, 0.949)     # fff2f2
NOTICE_LEFT = 36
NOTICE_WIDTH = 540
# Geometry is for this template: f990ez.pdf is US Letter on every page, with
# MediaBox and CropBox at the origin and /Rotate 0 (checked 2026-09-10). The
# box hangs from 786 and grows down, and the form's own title starts at 759.3 --
# so NOTICE_MAX_LINES exists to keep the fill off "Form 990-EZ".
NOTICE_TOP = 786
NOTICE_MAX_LINES = 2
NOTICE_SIZES = (9, 8, 7)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _fit(text: str, width: float) -> tuple[list[str], int]:
    """Wrap the notice, shrinking the type before the box can grow into the form.

    ponytail: 0.55em is a safe advance for the mixed-case prose this notice is
    (measured Helvetica is 0.446em); if it is ever rewritten in capitals or long
    digit runs, budget 0.72em instead. An appearance stream clips to its BBox,
    so an underestimate does not overflow visibly -- it cuts the sentence off
    mid-word and still looks deliberate. Which is why we never truncate: a
    notice that overlaps the form's title is ugly, one that silently drops
    "INCOMPLETE" is a lie, and the whole point of this box is not lying.
    """
    for size in NOTICE_SIZES:
        lines = textwrap.wrap(text, max(1, int(width / (size * 0.55))))
        if len(lines) <= NOTICE_MAX_LINES:
            return lines, size
    return lines, NOTICE_SIZES[-1]


def _coverage_note(form, rows_total: int | None) -> str:
    """The sentence that keeps a partial draft from looking like a whole one.

    Three ways a total ends up built from part of the books: app.py caps the
    shared demo at 60 rows, load_ledger diverts rows with an unreadable amount
    before the graph ever sees them, and a quota-exhausted batch leaves its rows
    classified as nothing. The screen says so; the file has to say so too,
    because the file is what gets mailed to a board member.

    rows_read comes off the form's own trace, never from the caller: the replay
    path builds its form from results/demo_run.json while its transactions come
    from the fixture CSV, and those two agree only by coincidence.
    """
    parts: list[str] = []
    rows_read = sum(batch.get("rows", 0) for batch in getattr(form, "trace", None) or [])
    if rows_total and rows_read and rows_total > rows_read:
        parts.append(f"covers {rows_read} of {rows_total} rows")
    unclassified = len(getattr(form, "unclassified", None) or [])
    if unclassified:
        plural = "" if unclassified == 1 else "s"
        parts.append(f"{unclassified} row{plural} unclassified")
    if not parts:
        return ""
    return " Totals INCOMPLETE: " + ", ".join(parts) + "."


def _appearance(writer, lines: list[str], size: int,
                width: float, height: float) -> DictionaryObject:
    """Build the annotation's /AP normal appearance.

    Without this the notice is an empty red box in Chrome, Edge and Streamlit's
    viewer: those all render through pdfium, which synthesises appearances for
    form fields (what /NeedAppearances covers) but never for markup annotations.
    """
    ops = [
        f"{NOTICE_BG[0]} {NOTICE_BG[1]} {NOTICE_BG[2]} rg",
        f"0 0 {width:.2f} {height:.2f} re f",
        f"{NOTICE_RED[0]} {NOTICE_RED[1]} {NOTICE_RED[2]} RG 0.7 w",
        f"0.35 0.35 {width - 0.7:.2f} {height - 0.7:.2f} re S",
        "BT",
        f"/Helv {size} Tf",
        f"{NOTICE_RED[0]} {NOTICE_RED[1]} {NOTICE_RED[2]} rg",
        f"{size + 2} TL",
        f"1 0 0 1 4 {height - size - 3:.2f} Tm",
    ]
    for index, line in enumerate(lines):
        if index:
            ops.append("T*")
        ops.append(f"({_pdf_escape(line)}) Tj")
    ops.append("ET")

    stream = DecodedStreamObject()
    # cp1252, not latin-1: the font below declares /WinAnsiEncoding, and the two
    # disagree over 0x80-0x9F -- every curly quote, em dash and euro sign the
    # notice might pick up in an editorial pass renders fine and raises here.
    stream.set_data("\n".join(ops).encode("cp1252", errors="replace"))
    stream[NameObject("/Type")] = NameObject("/XObject")
    stream[NameObject("/Subtype")] = NameObject("/Form")
    stream[NameObject("/FormType")] = NumberObject(1)
    stream[NameObject("/BBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(width), FloatObject(height)])
    stream[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/Helv"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            })})})
    # ponytail: _add_object is private, but pypdf exposes no public way to
    # register a standalone indirect object, and a /AP stream must be indirect.
    return writer._add_object(stream)


_FORM_LOCK = threading.Lock()


def download_form(dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # The hosted app is shared and every session is a thread of one process:
    # one download at a time, and a unique partial name, so two first
    # visitors never truncate each other's half-written form.
    with _FORM_LOCK:
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        response = requests.get(FORM_URL, timeout=120)
        response.raise_for_status()
        partial = dest.with_name(f"{dest.name}.{uuid.uuid4().hex}.part")
        partial.write_bytes(response.content)
        os.replace(partial, dest)
    return dest


def field_map() -> dict[str, str]:
    return dict(FIELD_MAP)


def fill_form(form, template: Path, dest: Path,
              org_name: str, ein: str,
              rows_total: int | None = None) -> Path:
    reader = PdfReader(str(template))
    writer = PdfWriter()
    writer.append(reader)

    mapping = field_map()
    values: dict[str, str] = {}
    if "org_name" in mapping:
        values[mapping["org_name"]] = org_name
    if "ein" in mapping:
        values[mapping["ein"]] = ein
    for number, result in form.lines.items():
        if number in mapping:
            values[mapping[number]] = str(result.amount)
    for key, amount in form.totals.items():
        if key in mapping:
            values[mapping[key]] = str(amount)

    for page in writer.pages:
        writer.update_page_form_field_values(page, values)

    # Visible on every page, not just in metadata: this is never a filing.
    notice = DRAFT_NOTICE + _coverage_note(form, rows_total)
    lines, size = _fit(notice, NOTICE_WIDTH - 8)
    height = len(lines) * (size + 2) + 8
    rect = (NOTICE_LEFT, NOTICE_TOP - height,
            NOTICE_LEFT + NOTICE_WIDTH, NOTICE_TOP)
    # One stream serves all four annotations: a form XObject is not page-scoped,
    # and /Rect is mapped through /BBox per annotation.
    appearance = _appearance(writer, lines, size, NOTICE_WIDTH, height)
    for index in range(len(writer.pages)):
        annotation = writer.add_annotation(page_number=index, annotation=FreeText(
            text=notice, rect=rect,
            font="Helvetica", font_size=f"{size}pt", font_color="c00000",
            border_color="c00000", background_color="fff2f2"))
        annotation[NameObject("/AP")] = DictionaryObject({
            NameObject("/N"): appearance})
        # Without /F the Print bit is clear and a conforming reader must not
        # print the notice -- the draft would reach the board as a clean form.
        # ReadOnly keeps it from being dragged off in Acrobat.
        annotation[NameObject("/F")] = NumberObject(
            AnnotationFlag.PRINT | AnnotationFlag.READ_ONLY)
        # pypdf builds /DA from the colour alone, with no Tf. A viewer that
        # regenerates this appearance would then have no font to select and the
        # empty red box comes back; /Helv is already in the template's /DR.
        annotation[NameObject("/DA")] = TextStringObject(
            f"/Helv {size} Tf {NOTICE_RED[0]} {NOTICE_RED[1]} {NOTICE_RED[2]} rg")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as handle:
        writer.write(handle)
    return dest
