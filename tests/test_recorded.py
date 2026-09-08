from pathlib import Path

from ninetyninety.recorded import load_recorded_run


def test_recorded_run_rebuilds_the_form():
    form = load_recorded_run(Path("results/demo_run.json"))
    assert form.totals["line9"] == 40369
    assert form.lines["1"].amount == 9100
    assert len(form.disagreements) == 2
    assert form.trace[0]["rows"] == 12
    assert form.lines["1"].transactions[0]["source_row"] == 2
