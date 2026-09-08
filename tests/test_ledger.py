from ninetyninety.ledger import load_ledger, parse_amount


def test_parse_amount_handles_currency_formatting():
    assert parse_amount("$1,234.00") == 1234
    assert parse_amount("1234") == 1234
    assert parse_amount("(500.00)") == -500
    assert parse_amount("-500") == -500


def test_parse_amount_rounds_cents_to_whole_dollars():
    assert parse_amount("10.49") == 10
    assert parse_amount("10.50") == 11


def test_load_ledger_reads_rows_and_records_source_row(tmp_path):
    path = tmp_path / "led.csv"
    path.write_text(
        "date,description,amount\n"
        "2025-03-04,SQUARE INC DEPOSIT SPRING GALA,\"$4,200.00\"\n"
        "2025-03-06,CITY OF ELGIN UTILITY PMT,(318.42)\n",
        encoding="utf-8")
    rows = load_ledger(path)
    assert len(rows) == 2
    assert rows[0].amount == 4200
    assert rows[0].source_row == 2
    assert rows[1].amount == -318
    assert rows[1].source_row == 3


def test_load_ledger_skips_blank_and_unparseable_rows(tmp_path):
    path = tmp_path / "led.csv"
    path.write_text("date,description,amount\n"
                    ",,\n"
                    "2025-01-01,GOOD ROW,100\n"
                    "2025-01-02,BAD AMOUNT,abc\n", encoding="utf-8")
    assert [r.description for r in load_ledger(path)] == ["GOOD ROW"]


def test_load_ledger_reports_skipped_rows_when_asked(tmp_path):
    path = tmp_path / "led.csv"
    path.write_text("date,description,amount\n"
                    "2025-01-02,BAD AMOUNT,abc\n", encoding="utf-8")
    skipped = []
    assert load_ledger(path, skipped) == []
    assert skipped == [{"source_row": 2, "description": "BAD AMOUNT",
                        "amount_raw": "abc"}]


def test_parse_amount_rejects_infinity_as_unreadable():
    import pytest
    for raw in ("inf", "-Infinity", "nan"):
        with pytest.raises(ValueError):
            parse_amount(raw)


def test_load_ledger_accepts_capitalised_and_padded_headers(tmp_path):
    path = tmp_path / "led.csv"
    path.write_text("Date, Description ,AMOUNT\n2025-01-01,DONATION,100\n", encoding="utf-8")
    rows = load_ledger(path)
    assert [(r.description, r.amount) for r in rows] == [("DONATION", 100)]


def test_load_ledger_refuses_a_file_without_the_required_columns(tmp_path):
    import pytest
    path = tmp_path / "led.csv"
    path.write_text("posted,memo,value\n2025-01-01,DONATION,100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="description, amount"):
        load_ledger(path)


def test_load_ledger_accepts_a_cp1252_bank_export(tmp_path):
    from ninetyninety.ledger import load_ledger
    path = tmp_path / "bank.csv"
    path.write_bytes("date,description,amount\r\n2025-03-01,CAF\u00c9 DONATION,100\r\n".encode("cp1252"))
    [tx] = load_ledger(path)
    assert tx.description == "CAF\u00c9 DONATION" and tx.amount == 100
