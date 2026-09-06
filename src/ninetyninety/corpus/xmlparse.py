"""Parse IRS 990-EZ e-file XML into a FiledReturn.

Element names verified against live IRS XML on 2026-09-06. Two are easy to get
wrong: GainOrLossFromSaleOfAssetsAmt (not NetGainOrLoss...) and
GrossProfitLossSlsOfInvntryAmt (not ...SalesOfInvntry...).
"""
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from ..lines import EXPENSE_LINES, REVENUE_LINES

NS = {"i": "http://www.irs.gov/efile"}
_ALL_LINES = REVENUE_LINES + EXPENSE_LINES
_FILED_ELEMENTS = (("line9", "TotalRevenueAmt"),
                   ("line17", "TotalExpensesAmt"),
                   ("line18", "ExcessOrDeficitForYearAmt"))


@dataclass
class FiledReturn:
    ein: str
    name: str
    tax_period: str
    amounts: dict[str, int] = field(default_factory=dict)
    filed: dict[str, int] = field(default_factory=dict)


def _int_or_none(element) -> int | None:
    if element is None or element.text is None or not element.text.strip():
        return None
    try:
        return int(float(element.text))
    except (ValueError, OverflowError):
        return None


def _text(root, path: str) -> str:
    element = root.find(path, NS)
    return element.text.strip() if element is not None and element.text else ""


def parse_990ez(xml_bytes: bytes) -> FiledReturn | None:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    form = root.find(".//i:IRS990EZ", NS)
    if form is None:
        return None

    amounts: dict[str, int] = {}
    for line in _ALL_LINES:
        value = _int_or_none(form.find("i:" + line.xml_element, NS))
        if value is not None:
            amounts[line.number] = value

    filed: dict[str, int] = {}
    for key, element_name in _FILED_ELEMENTS:
        value = _int_or_none(form.find("i:" + element_name, NS))
        if value is not None:
            filed[key] = value

    return FiledReturn(
        ein=_text(root, ".//i:Filer/i:EIN"),
        name=_text(root, ".//i:Filer/i:BusinessName/i:BusinessNameLine1Txt"),
        tax_period=_text(root, ".//i:TaxPeriodEndDt"),
        amounts=amounts,
        filed=filed,
    )


def iter_990ez(zip_path: Path) -> Iterator[FiledReturn]:
    with zipfile.ZipFile(Path(zip_path)) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            parsed = parse_990ez(archive.read(name))
            if parsed is not None:
                yield parsed
