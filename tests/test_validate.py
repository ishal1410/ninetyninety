from ninetyninety.corpus.validate import ValidationReport, score_return
from ninetyninety.corpus.xmlparse import FiledReturn


def _ret(amounts, filed):
    return FiledReturn(ein="1", name="X", tax_period="2025-12-31",
                       amounts=amounts, filed=filed)


def test_score_return_all_three_agree():
    assert score_return(_ret({"1": 100, "12": 40},
                             {"line9": 100, "line17": 40, "line18": 60})) == {
        "line9": True, "line17": True, "line18": True}


def test_score_return_detects_a_filed_total_that_is_wrong():
    assert score_return(_ret({"1": 100, "12": 40},
                             {"line9": 100, "line17": 40, "line18": 59}))["line18"] is False


def test_report_rate_is_matched_over_checked():
    report = ValidationReport()
    report.add(_ret({"1": 10}, {"line9": 10}), {"line9": True})
    report.add(_ret({"1": 10}, {"line9": 11}), {"line9": False})
    assert report.rate("line9") == 50.0
    assert report.line9 == (1, 2)


def test_report_skips_lines_the_filer_left_blank():
    report = ValidationReport()
    report.add(_ret({"1": 10}, {"line9": 10}), {"line9": True})
    assert report.line17 == (0, 0)
    assert report.rate("line17") == 0.0


def test_report_records_mismatch_detail_for_display():
    report = ValidationReport()
    report.add(_ret({"1": 10}, {"line9": 11}), {"line9": False})
    assert report.mismatches[0]["ein"] == "1"
    assert report.mismatches[0]["key"] == "line9"
