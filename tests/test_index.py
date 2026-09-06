# tests/test_index.py
import csv

from ninetyninety.corpus.index import batch_url, read_index

HEADER = ["RETURN_ID", "FILING_TYPE", "EIN", "TAX_PERIOD", "SUB_DATE",
          "TAXPAYER_NAME", "RETURN_TYPE", "DLN", "OBJECT_ID", "XML_BATCH_ID"]


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)


def test_read_index_filters_to_990ez(tmp_path):
    path = tmp_path / "index.csv"
    _write(path, [
        ["1", "EFILE", "760252367", "202509", "2026", "GALVESTON LITTLE LEAGUE INC",
         "990EZ", "d", "202630139349201873", "2026_TEOS_XML_01A"],
        ["2", "EFILE", "111111111", "202512", "2026", "SOME BIG CHARITY",
         "990", "d", "202630139349209999", "2026_TEOS_XML_01A"],
    ])
    rows = read_index(path)
    assert len(rows) == 1
    assert rows[0]["TAXPAYER_NAME"] == "GALVESTON LITTLE LEAGUE INC"
    assert rows[0]["XML_BATCH_ID"] == "2026_TEOS_XML_01A"


def test_read_index_can_select_another_return_type(tmp_path):
    path = tmp_path / "index.csv"
    _write(path, [
        ["2", "EFILE", "111111111", "202512", "2026", "SOME BIG CHARITY",
         "990", "d", "202630139349209999", "2026_TEOS_XML_01A"],
    ])
    assert len(read_index(path, return_type="990")) == 1


def test_batch_url_appends_zip_to_the_batch_id():
    url = batch_url("2026_TEOS_XML_01A")
    assert url == ("https://apps.irs.gov/pub/epostcard/990/xml/2026/"
                   "2026_TEOS_XML_01A.zip")
