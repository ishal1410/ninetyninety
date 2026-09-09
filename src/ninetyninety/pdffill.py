"""Fill the real IRS Form 990-EZ AcroForm.

The blank form has 385 fields. FIELD_MAP is populated from the exact names
printed by scripts/dump_fields.py -- never guess them.

Output is always a DRAFT: e-filing requires an Authorized IRS e-File Provider
EFIN, which this project does not have.
"""
import os
import threading
import uuid
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText

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
              org_name: str, ein: str) -> Path:
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
    for index in range(len(writer.pages)):
        writer.add_annotation(page_number=index, annotation=FreeText(
            text=DRAFT_NOTICE, rect=(36, 756, 576, 786),
            font="Helvetica", font_size="9pt", font_color="c00000",
            border_color="c00000", background_color="fff2f2"))

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as handle:
        writer.write(handle)
    return dest
