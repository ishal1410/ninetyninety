from ninetyninety.corpus.xmlparse import parse_990ez

EZ = b"""<?xml version="1.0" encoding="UTF-8"?>
<Return xmlns="http://www.irs.gov/efile">
  <ReturnHeader>
    <TaxPeriodEndDt>2025-09-30</TaxPeriodEndDt>
    <Filer><EIN>760252367</EIN><BusinessName>
      <BusinessNameLine1Txt>GALVESTON LITTLE LEAGUE INC</BusinessNameLine1Txt>
    </BusinessName></Filer>
  </ReturnHeader>
  <ReturnData>
    <IRS990EZ>
      <ContributionsGiftsGrantsEtcAmt>33456</ContributionsGiftsGrantsEtcAmt>
      <InvestmentIncomeAmt>9</InvestmentIncomeAmt>
      <SpecialEventsNetIncomeLossAmt>3495</SpecialEventsNetIncomeLossAmt>
      <TotalRevenueAmt>36960</TotalRevenueAmt>
      <SalariesOtherCompEmplBnftAmt>12000</SalariesOtherCompEmplBnftAmt>
      <OtherExpensesTotalAmt>4000</OtherExpensesTotalAmt>
      <TotalExpensesAmt>16000</TotalExpensesAmt>
      <ExcessOrDeficitForYearAmt>20960</ExcessOrDeficitForYearAmt>
    </IRS990EZ>
  </ReturnData>
</Return>"""

NOT_EZ = b"""<?xml version="1.0" encoding="UTF-8"?>
<Return xmlns="http://www.irs.gov/efile">
  <ReturnData><IRS990><TotalRevenueAmt>5</TotalRevenueAmt></IRS990></ReturnData>
</Return>"""


def test_parse_reads_header_and_line_amounts():
    result = parse_990ez(EZ)
    assert result.ein == "760252367"
    assert result.name == "GALVESTON LITTLE LEAGUE INC"
    assert result.amounts["1"] == 33456
    assert result.amounts["6d"] == 3495
    assert result.amounts["12"] == 12000


def test_parse_reads_the_filed_totals_separately():
    assert parse_990ez(EZ).filed == {"line9": 36960, "line17": 16000,
                                     "line18": 20960}


def test_absent_lines_are_absent_not_zero():
    assert "2" not in parse_990ez(EZ).amounts


def test_a_full_990_is_rejected():
    assert parse_990ez(NOT_EZ) is None


def test_malformed_xml_returns_none():
    assert parse_990ez(b"<not xml") is None
