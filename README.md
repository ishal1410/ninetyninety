# NinetyNinety

**A shoebox of bank transactions becomes a drafted IRS Form 990-EZ, with every line citing the transactions behind it and the rule that put them there.**

Built with **Strands Agents** for the AWS *Agents for Humans* hackathon (Good Neighbor Agents track).

## The problem

Small US nonprofits (gross receipts under $200,000, total assets under $500,000) file Form 990-EZ. Most have no finance staff. The IRS auto-revokes tax-exempt status after three missed filings, and its revocation list holds over a million entries. Existing filing tools start *after* the books are categorised. Categorising the books is the actual work, and it is the part nobody helps with.

## Who it is for

Volunteer treasurers of small US nonprofits: the little league, the food pantry, the community band. People with a bank export and no bookkeeper.

## Does the engine actually work?

Before drafting anything for a user, the same arithmetic that fills the form was run against **3,687 real Form 990-EZ returns** filed with the IRS (e-file XML batch `2026_TEOS_XML_01A`), rebuilding each return's stated totals from its own line items:

| Part I identity | Reconstructed | Rate |
|---|---|---|
| Line 9, total revenue = lines 1 through 8 | **3,632 / 3,632** | **100.00%** |
| Line 17, total expenses = lines 10 through 16 | 3,617 / 3,618 | 99.97% |
| Line 18, excess = line 9 minus line 17 | 3,619 / 3,621 | 99.94% |

All three mismatches are real filed returns whose own stated totals disagree with their own components (one is off by one dollar). They are listed in `results/validation.json`. Reproduce with `PYTHONPATH=src python scripts/validate.py`.

## How it works

![Architecture](docs/architecture.png)

1. **Ledger in.** A CSV of `date, description, amount`. Raw bank text, no categories.
2. **Two Strands Agents, independently.** The **Preparer** classifies each transaction onto a Form 990-EZ Part I line and cites the rule from the IRS instructions. The **Reviewer** classifies the *same* transaction without ever seeing the Preparer's reasoning. Agreement is corroboration. Disagreement is shown to the user, never silently resolved.
3. **Python does every total.** The model classifies and explains. It never adds. Lines 9, 17 and 18 are computed in `formmath.py`, the same module the validation harness runs over real filings. That is why the accuracy number above means something.
4. **The real IRS PDF.** Amounts land in the actual `f990ez.pdf` AcroForm fields, and every page carries a red **DRAFT, NOT A FILING** notice.

## Run it

```bash
git clone https://github.com/ishal1410/ninetyninety
cd ninetyninety
pip install -r requirements.txt
cp .env.example .env    # then paste a free key from https://aistudio.google.com/apikey
PYTHONPATH=src python cli.py fixtures/demo_ledger.csv
```

Web UI: `streamlit run app.py`

Tests: `PYTHONPATH=src python -m pytest`

Model providers: Gemini (free tier, no card) first, OpenRouter free models as failover. Configured in `src/ninetyninety/config.py`. No AWS spend.

## Live demo

_Deploying to Streamlit Community Cloud. URL will be added here._

## Limitations, stated plainly

- **The output is a draft, not a filing.** For tax year 2025 the IRS requires Form 990-EZ to be filed electronically, which needs an Authorized IRS e-File Provider. This project is not one.
- **An officer of the organisation must review and sign.** The Paid Preparer block is left blank on purpose.
- **Only Part I is drafted.** Parts II through VI and all Schedules are out of scope. The app does not pretend to fill them.
- **The demo ledger is synthetic.** `fixtures/demo_ledger.csv` is made up. The accuracy numbers above come from real IRS filings, never from that file.
- **Classification is a model judgement.** The two-agent design surfaces uncertainty; it does not eliminate it. Low-confidence and disputed rows are flagged for a human.

## Layout

```
src/ninetyninety/
  lines.py        Part I line taxonomy, IRS XML element names, guidance text
  formmath.py     the only place totals are computed
  ledger.py       CSV in -> Transaction rows with source-row provenance
  agents.py       Preparer and Reviewer (Strands Agents)
  prepare.py      classify every row, assemble Part I, record disagreements
  pdffill.py      fill the real IRS AcroForm, stamp DRAFT on every page
  corpus/         IRS 990 e-file XML index, parser, validation harness
cli.py            terminal entry point
app.py            Streamlit UI
scripts/          validate.py (the headline number), dump_fields.py
```

## License

MIT. See `LICENSE`.
