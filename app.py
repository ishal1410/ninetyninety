"""NinetyNinety -- draft an IRS Form 990-EZ from a nonprofit's raw ledger.

Built with Strands Agents.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

from ninetyninety.ledger import load_ledger
from ninetyninety.lines import form_order, line_by_number
from ninetyninety.pdffill import download_form, fill_form
from ninetyninety.prepare import prepare_ledger

st.set_page_config(page_title="NinetyNinety", layout="wide")
st.title("NinetyNinety")
st.caption("A shoebox of bank transactions becomes a drafted IRS Form 990-EZ -- "
           "every line citing the transactions and the rule behind it. "
           "Built with Strands Agents.")
st.warning("**DRAFT -- not a filing.** An officer of the organisation must "
           "review and sign. E-filing requires an Authorized IRS e-File Provider.")

report_path = Path(__file__).parent / "results" / "validation.json"
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
    st.subheader("Does the engine actually work?")
    st.write(f"The same arithmetic that fills your form was run against "
             f"**{report['returns']:,} real Form 990-EZ returns** filed with the "
             f"IRS, rebuilding each return's totals from its own line items.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Line 9 · total revenue", f"{report['rates']['line9']}%",
                f"{report['matched']['line9']:,}/{report['checked']['line9']:,}")
    col2.metric("Line 17 · total expenses", f"{report['rates']['line17']}%",
                f"{report['matched']['line17']:,}/{report['checked']['line17']:,}")
    col3.metric("Line 18 · excess/deficit", f"{report['rates']['line18']}%",
                f"{report['matched']['line18']:,}/{report['checked']['line18']:,}")
    st.caption(f"Source: IRS Form 990 e-file XML batch {report['batch']}, "
               "apps.irs.gov/pub/epostcard/990/xml/2026/. The mismatches are "
               "filed returns whose own stated totals disagree with their own "
               "line items.")

st.divider()
st.subheader("Draft a return")
uploaded = st.file_uploader("Transaction ledger (CSV: date, description, amount)",
                            type="csv")
use_demo = st.checkbox("Use the synthetic demo ledger instead",
                       value=uploaded is None)
org_name = st.text_input("Organisation name (for the PDF)", "DEMO COMMUNITY ORG")
ein = st.text_input("EIN (for the PDF)", "00-0000000")

if st.button("Draft the 990-EZ", type="primary"):
    base = Path(__file__).parent
    # Every visitor gets private scratch files: the hosted app is shared.
    workdir = Path(tempfile.mkdtemp(prefix="ninetyninety-"))
    path = base / "fixtures" / "demo_ledger.csv"
    if uploaded is not None and not use_demo:
        path = workdir / "ledger.csv"
        path.write_bytes(uploaded.getvalue())

    skipped: list[dict] = []
    try:
        transactions = load_ledger(path, skipped)
    except ValueError as error:
        st.error(f"Could not read the ledger: {error}")
        st.stop()
    bar = st.progress(0.0, text="Preparer and Reviewer running in parallel through the Strands graph...")
    try:
        form = prepare_ledger(
            transactions,
            progress=lambda done, total: bar.progress(
                done / total, text=f"Batch {done}/{total} through the Strands graph"))
    except Exception as error:  # noqa: BLE001 - surface any failure to the user
        st.error(f"Could not complete the draft: {error}")
        st.stop()
    bar.empty()
    pdf_bytes, pdf_error = None, None
    try:
        pdf = fill_form(form, download_form(base / "data" / "f990ez.pdf"),
                        workdir / "draft.pdf", org_name, ein)
        pdf_bytes = pdf.read_bytes()
    except Exception as error:  # noqa: BLE001
        pdf_error = str(error)
    # Kept across reruns: the download button reruns the script and st.button
    # is False on that rerun, so without this the whole draft would vanish.
    st.session_state["draft"] = {"form": form, "skipped": skipped, "loaded": len(transactions),
                                 "pdf": pdf_bytes, "pdf_error": pdf_error}

draft = st.session_state.get("draft")
if draft:
    form, skipped = draft["form"], draft["skipped"]
    st.write(f"Loaded **{draft['loaded']}** transactions"
             + (f", skipped **{len(skipped)}** with unreadable amounts." if skipped else "."))
    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### Form 990-EZ Part I")
        for number in sorted(form.lines, key=form_order):
            result = form.lines[number]
            with st.expander(f"Line {number} · {line_by_number(number).label} · "
                             f"${result.amount:,}"):
                for citation in result.transactions:
                    st.write(f"row {citation['source_row']} · {citation['date']} · "
                             f"{citation['description']} · ${citation['amount']:,}")
                    st.caption(f"Rule: {citation['rule']}")
        st.markdown(f"**Line 9 total revenue: ${form.totals['line9']:,}**")
        st.markdown(f"**Line 17 total expenses: ${form.totals['line17']:,}**")
        st.markdown(f"**Line 18 excess/(deficit): ${form.totals['line18']:,}**")
        st.caption("Totals are computed in Python from the classified lines. "
                   "The model never does arithmetic.")

        if draft["pdf"] is not None:
            st.download_button("Download the drafted IRS Form 990-EZ (PDF, marked DRAFT)",
                               draft["pdf"], file_name="990-EZ-DRAFT.pdf",
                               mime="application/pdf")
        else:
            st.info(f"PDF not produced: {draft['pdf_error']}")

    with right:
        st.markdown(f"#### Agent disagreements ({len(form.disagreements)})")
        st.caption("The Reviewer never sees the Preparer's reasoning, so these "
                   "are two independent readings of the same transaction. The "
                   "Referee runs only when they differ and must cite the IRS text.")
        for item in form.disagreements:
            referee = (f"Referee → line {item['referee']}: {item['referee_reason']}"
                       if item["referee"] else "Referee did not rule; Preparer's line used")
            st.warning(f"**row {item['source_row']}** · {item['description']}\n\n"
                       f"Preparer → line {item['preparer']}: {item['preparer_rule']}\n\n"
                       f"Reviewer → line {item['reviewer']}: {item['reviewer_rule']}\n\n"
                       f"{referee}\n\nOn the form: line {item['used']}")
        st.markdown(f"#### Low confidence ({len(form.low_confidence)})")
        for item in form.low_confidence:
            st.info(f"row {item['source_row']} · {item['description']} "
                    f"→ line {item['line']} · {item['note']}")
        if form.ungrounded:
            st.markdown(f"#### Rule not found in IRS guidance ({len(form.ungrounded)})")
            for item in form.ungrounded:
                st.error(f"row {item['source_row']} · line {item['line']} · "
                         f"quoted rule: “{item['rule'][:120]}”")
        if form.unreviewed:
            st.markdown(f"#### Single opinion only ({len(form.unreviewed)})")
            for item in form.unreviewed:
                st.info(f"row {item['source_row']} · {item['description']} "
                        f"→ line {item['line']} · {item['note']}")
        if form.unclassified:
            st.markdown(f"#### Not classified ({len(form.unclassified)})")
            for item in form.unclassified:
                st.error(f"row {item['source_row']} · {item['description']} · "
                         f"${item['amount']:,} -- {item['error']}")
        if skipped:
            st.markdown(f"#### Rows with unreadable amounts ({len(skipped)})")
            for item in skipped:
                st.error(f"row {item['source_row']} · {item['description']} · "
                         f"amount {item['amount_raw']!r}")

        with st.expander(f"Strands trace · {len(form.trace)} graph runs"):
            st.caption("Preparer and Reviewer are parallel entry nodes that never see "
                       "each other; the Referee is reached by a conditional edge only "
                       "when they disagree. Tool calls are real line_guidance lookups.")
            st.table([{k: (", ".join(v) if isinstance(v, list) else
                           ", ".join(f"{n} {round(ms)}ms" for n, ms in v.items() if ms is not None)
                           if isinstance(v, dict) else v)
                       for k, v in t.items()} for t in form.trace])
