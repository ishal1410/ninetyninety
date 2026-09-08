import io
import sys

import cli
from ninetyninety.prepare import assemble


def test_cli_survives_a_cp1252_console(tmp_path, monkeypatch):
    """Windows consoles default to cp1252; a non-ASCII description must not crash."""
    ledger = tmp_path / "l.csv"
    ledger.write_text("date,description,amount\n2025-01-01,CAFÉ → 无 SALE,50\n",
                      encoding="utf-8")
    monkeypatch.setattr(cli, "prepare_ledger", lambda transactions, progress=None: assemble(
        [(t, None, None) for t in transactions], {}))
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", out)
    assert cli.main(["cli.py", str(ledger)]) == 0
    out.flush()
    assert b"UNCLASSIFIED row 2" in out.buffer.getvalue()


def test_cli_help_prints_usage_and_exits_zero(capsys):
    assert cli.main(["cli.py", "--help"]) == 0
    out = capsys.readouterr().out
    assert "usage" in out.lower() and "ledger" in out.lower()
