# NinetyNinety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a small nonprofit's uncategorised transaction ledger into a drafted IRS Form 990-EZ Part I, where every line cites the transactions it came from and the instruction rule that put them there — and prove the engine is correct by reconstructing thousands of real filed federal returns.

**Architecture:** Two Strands agents in adversarial review — a **Preparer** classifies each messy transaction to a 990-EZ line and cites the rule; a **Reviewer** independently classifies the same transaction without seeing the Preparer's reasoning, and disagreements are surfaced rather than hidden. All arithmetic and the three Part I balance identities are deterministic Python, never model output. A validation harness runs that same deterministic engine over real IRS e-file XML to publish an accuracy rate.

**Tech Stack:** Python 3.12, `strands-agents[gemini,openai]` 1.54.0, `gemini-2.5-flash` (OpenRouter `z-ai/glm-5.2:free` failover), Streamlit Community Cloud, `pypdf` for AcroForm filling, IRS 990 e-file XML corpus, pytest.

## Global Constraints

- **Deadline: 2026-09-14 17:00 PDT.** No extension. Devpost submissions may be edited until then — bank a valid submission early, improve after.
- **`strands-agents` is mandatory.** Name "Strands Agents" explicitly in the README, the Devpost description, and the video. Organizer update: *"Name Strands Agents explicitly — it's one of the first things reviewed."*
- **License must be MIT or Apache-2.0**, as a real `LICENSE` file at repo root, detectable in GitHub's About sidebar. GPL/AGPL are ineligible.
- **New project only.** Enforced on the record (forum 44877). No reused code.
- **Zero budget.** No paid API, no AWS model spend, no paid host.
- **The output is a DRAFT, never a filing.** Every screen, the PDF, and the video must say so. E-filing requires an Authorized IRS e-File Provider EFIN we do not have, and *"If you are filing a 2025 Form 990-EZ, you are required to file electronically."*
- **Leave the Paid Preparer block blank.** *"Volunteers or others who prepare forms without compensation are not required to have a PTIN."* State that an officer of the organisation must sign.
- **The model never does arithmetic.** Totals, subtotals and the three Part I identities are computed in Python. The model only classifies and explains.
- **Never claim a capability that is not implemented.**
- Video ≤ 5 minutes, public on YouTube or Vimeo, containing a working demo plus a pitch covering (1) the problem (2) who it's for (3) why it matters.
- Required submission fields: public repo URL, text description, README, architecture diagram, video, AWS Builder ID.

## Verified Facts (measured 2026-09-06 — do not re-derive)

| Fact | Value |
|---|---|
| IRS index | `https://apps.irs.gov/pub/epostcard/990/xml/2026/index_2026.csv` — 47,506,032 bytes, keyless, HTTP 200 |
| Index columns | `RETURN_ID,FILING_TYPE,EIN,TAX_PERIOD,SUB_DATE,TAXPAYER_NAME,RETURN_TYPE,DLN,OBJECT_ID,XML_BATCH_ID` |
| Index contents | 385,890 returns: 990 = 180,965 · **990EZ = 121,299** · 990PF = 72,782 · 990T = 10,844 |
| Batch zip | `https://apps.irs.gov/pub/epostcard/990/xml/2026/2026_TEOS_XML_01A.zip` — 71,497,607 bytes, 12,245 XMLs |
| Directory browsing | **404s.** Files are reachable only by exact filename; a batch's filename is its `XML_BATCH_ID` plus `.zip` |
| XML namespace | `http://www.irs.gov/efile`; the form element is `IRS990EZ` |
| Fillable form | `https://www.irs.gov/pub/irs-pdf/f990ez.pdf` — HTTP 200, 397,623 bytes, AcroForm, 385 fields |
| Instructions | `https://www.irs.gov/pub/irs-pdf/i990ez.pdf` — 49 pages |
| Filing thresholds | 990-EZ if *"gross receipts less than $200,000 and total assets at the end of the year less than $500,000"*; ≤$50,000 may file 990-N |
| **Reconstruction accuracy** | **Line 9: 3,632/3,632 = 100.00%** · Line 17: 3,617/3,618 = 99.97% · Line 18: 3,620/3,621 = 99.97%, over 3,687 real 990-EZ returns in one batch |

### Real Part I element names (verified from live XML — guessing two of these cost 12.5% accuracy)

**Revenue, lines 1–8, summing to `TotalRevenueAmt` (line 9):**
```
ContributionsGiftsGrantsEtcAmt      ProgramServiceRevenueAmt
MembershipDuesAmt                   InvestmentIncomeAmt
GainOrLossFromSaleOfAssetsAmt       SpecialEventsNetIncomeLossAmt
GrossProfitLossSlsOfInvntryAmt      OtherRevenueTotalAmt
```
**Expenses, lines 10–16, summing to `TotalExpensesAmt` (line 17):**
```
GrantsAndSimilarAmountsPaidAmt      BenefitsPaidToOrForMembersAmt
SalariesOtherCompEmplBnftAmt        FeesAndOtherPymtToIndCntrctAmt
OccupancyRentUtltsAndMaintAmt       PrintingPublicationsPostageAmt
OtherExpensesTotalAmt
```
**Identity (line 18):** `TotalRevenueAmt - TotalExpensesAmt == ExcessOrDeficitForYearAmt`

Watch out: `GainOrLossFromSaleOfAssetsAmt` (NOT `NetGainOrLoss…`) and `GrossProfitLossSlsOfInvntryAmt` (NOT `…SalesOfInvntry…`).

## File Structure

```
ninetyninety/
  LICENSE                      MIT, repo root
  README.md
  requirements.txt
  .env.example
  docs/architecture.png
  src/ninetyninety/
    __init__.py
    config.py                  model provider + failover
    lines.py                   the 990-EZ line taxonomy, single source of truth
    formmath.py                deterministic totals + the 3 identities
    corpus/index.py            IRS index CSV client
    corpus/xmlparse.py         990-EZ XML -> FiledReturn
    corpus/validate.py         the accuracy harness  <- THE HEADLINE
    ledger.py                  Transaction model + CSV loader
    agents.py                  Preparer + Reviewer prompts and builders
    graph.py                   Strands GraphBuilder wiring
    prepare.py                 orchestration: ledger -> Form990EZ
    pdffill.py                 fill f990ez.pdf AcroForm
  app.py                       Streamlit UI
  cli.py
  fixtures/demo_ledger.csv     synthetic, clearly labelled
  scripts/
  tests/
```

**Boundary rule:** `formmath.py` is pure functions over plain numbers — no model, no network. It is the only place a total is produced, and it is shared by both the live preparer and the validation harness. That sharing is what makes the published accuracy rate mean something.

---

### Task 1: Scaffold and license

**Files:**
- Create: `LICENSE`, `requirements.txt`, `.gitignore`, `.env.example`, `src/ninetyninety/__init__.py`, `src/ninetyninety/corpus/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: importable package `ninetyninety`

- [ ] **Step 1: Create the MIT license file**

Write `LICENSE` at repo root, exactly that filename:

```
MIT License

Copyright (c) 2026 <YOUR NAME>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create `requirements.txt`**

```
strands-agents[gemini,openai]==1.54.0
requests==2.32.3
pypdf==5.1.0
streamlit==1.63.0
python-dotenv==1.0.1
pytest==8.3.3
```

The `openai` extra is required: `strands/models/openai.py` does a top-level `import openai`, so the OpenRouter failover cannot import without it.

`streamlit` must be 1.63.0 or newer: `strands-agents` 1.54.0 requires `watchdog>=6,<7`, while `streamlit` 1.39.0 requires `watchdog<6` on non-macOS platforms. Those pins are disjoint and pip fails with `ResolutionImpossible`. Resolved live 2026-09-06: streamlit 1.63.0 + watchdog 6.0.0 coexist with everything else here.

- [ ] **Step 3: Create `.gitignore` and `.env.example`**

`.gitignore`:
```
__pycache__/
*.pyc
.env
.cache/
data/
out/
venv/
.venv/
```

`.env.example`:
```
# Google AI Studio key -- https://aistudio.google.com/apikey (free tier, no card)
GOOGLE_API_KEY=
# Optional failover -- https://openrouter.ai/keys (free models, no card)
OPENROUTER_API_KEY=
```

- [ ] **Step 4: Create package files**

```bash
mkdir -p src/ninetyninety/corpus tests fixtures scripts data
touch src/ninetyninety/__init__.py src/ninetyninety/corpus/__init__.py tests/__init__.py
```

- [ ] **Step 5: Install and verify every import the plan depends on**

Run: `pip install -r requirements.txt && python -c "import strands; from strands.multiagent import GraphBuilder; from strands.models.gemini import GeminiModel; from strands.models.openai import OpenAIModel; import pypdf; print('deps ok')"`
Expected: `deps ok`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold project with MIT license and pinned Strands Agents"
```

---

### Task 2: The 990-EZ line taxonomy

**Files:**
- Create: `src/ninetyninety/lines.py`, `tests/test_lines.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Line(number: str, label: str, xml_element: str, kind: str, guidance: str)`
  - `REVENUE_LINES: list[Line]`, `EXPENSE_LINES: list[Line]`
  - `ALL_LINE_NUMBERS: set[str]`
  - `line_by_number(number: str) -> Line`

Single source of truth shared by the parser, the harness, the agents, and the PDF filler.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lines.py
from ninetyninety.lines import (
    ALL_LINE_NUMBERS, EXPENSE_LINES, REVENUE_LINES, line_by_number,
)


def test_revenue_has_eight_lines_and_expenses_seven():
    assert len(REVENUE_LINES) == 8
    assert len(EXPENSE_LINES) == 7


def test_element_names_match_live_irs_schema():
    names = {line.xml_element for line in REVENUE_LINES}
    assert "GainOrLossFromSaleOfAssetsAmt" in names
    assert "GrossProfitLossSlsOfInvntryAmt" in names
    assert "NetGainOrLossSaleOfAssetsAmt" not in names


def test_line_by_number_returns_the_right_line():
    assert line_by_number("1").xml_element == "ContributionsGiftsGrantsEtcAmt"
    assert line_by_number("16").kind == "expense"


def test_every_line_carries_guidance_for_the_agents():
    for line in REVENUE_LINES + EXPENSE_LINES:
        assert line.guidance.strip(), f"line {line.number} has no guidance"


def test_all_line_numbers_is_the_union():
    assert ALL_LINE_NUMBERS == {line.number for line in REVENUE_LINES + EXPENSE_LINES}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_lines.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.lines'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/lines.py
"""The IRS Form 990-EZ Part I line taxonomy.

Single source of truth for the parser, the validation harness, the agents and
the PDF filler. Every `xml_element` was read from live IRS e-file XML on
2026-09-06 -- guessing two of these names cost 12.5% reconstruction accuracy.

`guidance` is what the Preparer and Reviewer agents see. Keep it short and
plainly derived from the Form 990-EZ instructions (i990ez.pdf).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    number: str
    label: str
    xml_element: str
    kind: str  # "revenue" or "expense"
    guidance: str


REVENUE_LINES: list[Line] = [
    Line("1", "Contributions, gifts, grants, and similar amounts received",
         "ContributionsGiftsGrantsEtcAmt", "revenue",
         "Voluntary transfers where the donor receives nothing of comparable "
         "value in return: donations, grants from foundations or government, "
         "bequests, and the contribution portion of a fundraising ticket."),
    Line("2", "Program service revenue including government fees and contracts",
         "ProgramServiceRevenueAmt", "revenue",
         "Income earned by carrying out the organisation's exempt purpose: "
         "tuition, admissions, class fees, service fees paid by clients or by "
         "a government agency buying the service."),
    Line("3", "Membership dues and assessments",
         "MembershipDuesAmt", "revenue",
         "Dues paid to belong to the organisation. If members receive benefits "
         "of comparable value the payment belongs on line 3; if it is really a "
         "donation with no benefit it belongs on line 1."),
    Line("4", "Investment income",
         "InvestmentIncomeAmt", "revenue",
         "Interest, dividends, and rent from investment property. Bank account "
         "interest belongs here."),
    Line("5c", "Gain or (loss) from sale of assets other than inventory",
         "GainOrLossFromSaleOfAssetsAmt", "revenue",
         "Net gain or loss from selling equipment, vehicles or securities. This "
         "is a NET figure -- proceeds minus basis -- and may be negative."),
    Line("6d", "Net income or (loss) from gaming and fundraising events",
         "SpecialEventsNetIncomeLossAmt", "revenue",
         "Gross receipts from events such as galas, raffles and bingo, minus the "
         "direct expenses of those events. NET, and may be negative."),
    Line("7c", "Gross profit or (loss) from sales of inventory",
         "GrossProfitLossSlsOfInvntryAmt", "revenue",
         "Sales of goods (merchandise, cookbooks, thrift goods) minus cost of "
         "goods sold. NET, and may be negative."),
    Line("8", "Other revenue",
         "OtherRevenueTotalAmt", "revenue",
         "Revenue that fits none of lines 1 through 7c. Use sparingly; prefer a "
         "specific line whenever one applies."),
]

EXPENSE_LINES: list[Line] = [
    Line("10", "Grants and similar amounts paid",
         "GrantsAndSimilarAmountsPaidAmt", "expense",
         "Grants, scholarships and assistance the organisation pays out to "
         "others, including direct aid to the people it serves."),
    Line("11", "Benefits paid to or for members",
         "BenefitsPaidToOrForMembersAmt", "expense",
         "Payments made to members as members, such as insurance or death "
         "benefits from a fraternal or mutual organisation."),
    Line("12", "Salaries, other compensation, and employee benefits",
         "SalariesOtherCompEmplBnftAmt", "expense",
         "Wages, payroll taxes, pension and health benefits for EMPLOYEES. "
         "Payments to non-employees belong on line 13."),
    Line("13", "Professional fees and other payments to independent contractors",
         "FeesAndOtherPymtToIndCntrctAmt", "expense",
         "Payments to people and firms who are not employees: accountants, "
         "lawyers, consultants, contract cleaners, freelance instructors."),
    Line("14", "Occupancy, rent, utilities, and maintenance",
         "OccupancyRentUtltsAndMaintAmt", "expense",
         "Rent or mortgage interest on premises, electricity, gas, water, "
         "internet at the premises, cleaning and repairs to the premises."),
    Line("15", "Printing, publications, postage, and shipping",
         "PrintingPublicationsPostageAmt", "expense",
         "Printing, newsletters, stationery, stamps, courier and shipping."),
    Line("16", "Other expenses",
         "OtherExpensesTotalAmt", "expense",
         "Expenses fitting none of lines 10 through 15: insurance, software "
         "subscriptions, bank fees, supplies, travel, training."),
]

ALL_LINE_NUMBERS: set[str] = {
    line.number for line in REVENUE_LINES + EXPENSE_LINES
}

_BY_NUMBER = {line.number: line for line in REVENUE_LINES + EXPENSE_LINES}


def line_by_number(number: str) -> Line:
    return _BY_NUMBER[number]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_lines.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ninetyninety/lines.py tests/test_lines.py
git commit -m "feat: add 990-EZ line taxonomy with verified IRS element names"
```

---

### Task 3: Deterministic form arithmetic

**Files:**
- Create: `src/ninetyninety/formmath.py`, `tests/test_formmath.py`

**Interfaces:**
- Consumes: `REVENUE_LINES`, `EXPENSE_LINES` (Task 2)
- Produces:
  - `total_revenue(amounts: dict[str, int]) -> int`
  - `total_expenses(amounts: dict[str, int]) -> int`
  - `excess_or_deficit(amounts: dict[str, int]) -> int`
  - `check_identities(amounts: dict[str, int], filed: dict[str, int]) -> dict[str, bool]`

`amounts` is keyed by line number (`"1"`, `"5c"`, `"16"`). `filed` is keyed by `"line9"`, `"line17"`, `"line18"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_formmath.py
from ninetyninety.formmath import (
    check_identities, excess_or_deficit, total_expenses, total_revenue,
)


def test_total_revenue_sums_lines_1_to_8():
    assert total_revenue({"1": 33456, "4": 9, "6d": 3495}) == 36960


def test_totals_ignore_the_other_side_of_the_form():
    amounts = {"1": 1000, "12": 500}
    assert total_revenue(amounts) == 1000
    assert total_expenses(amounts) == 500


def test_negative_net_lines_are_allowed():
    assert total_revenue({"1": 5000, "7c": -800}) == 4200


def test_missing_lines_count_as_zero():
    assert total_revenue({}) == 0
    assert total_expenses({}) == 0


def test_excess_or_deficit_is_revenue_minus_expenses():
    assert excess_or_deficit({"1": 10000, "12": 4000}) == 6000


def test_check_identities_reports_each_line_separately():
    result = check_identities({"1": 100, "12": 40},
                              {"line9": 100, "line17": 40, "line18": 60})
    assert result == {"line9": True, "line17": True, "line18": True}


def test_check_identities_flags_only_the_wrong_one():
    result = check_identities({"1": 100, "12": 40},
                              {"line9": 100, "line17": 40, "line18": 59})
    assert result["line18"] is False
    assert result["line9"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_formmath.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.formmath'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/formmath.py
"""Deterministic Form 990-EZ Part I arithmetic.

No model output ever reaches this module. Totals are computed here and only
here, so the accuracy rate published by the validation harness describes
exactly the same code path that fills a user's form.
"""
from .lines import EXPENSE_LINES, REVENUE_LINES

_REVENUE_NUMBERS = [line.number for line in REVENUE_LINES]
_EXPENSE_NUMBERS = [line.number for line in EXPENSE_LINES]


def total_revenue(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 9 = sum of lines 1 through 8."""
    return sum(int(amounts.get(number, 0)) for number in _REVENUE_NUMBERS)


def total_expenses(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 17 = sum of lines 10 through 16."""
    return sum(int(amounts.get(number, 0)) for number in _EXPENSE_NUMBERS)


def excess_or_deficit(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 18 = line 9 minus line 17."""
    return total_revenue(amounts) - total_expenses(amounts)


def check_identities(amounts: dict[str, int],
                     filed: dict[str, int]) -> dict[str, bool]:
    """Compare our reconstruction against a filed return's own stated totals."""
    return {
        "line9": total_revenue(amounts) == filed.get("line9"),
        "line17": total_expenses(amounts) == filed.get("line17"),
        "line18": excess_or_deficit(amounts) == filed.get("line18"),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_formmath.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/ninetyninety/formmath.py tests/test_formmath.py
git commit -m "feat: add deterministic 990-EZ Part I arithmetic"
```

---

### Task 4: IRS corpus client

**Files:**
- Create: `src/ninetyninety/corpus/index.py`, `tests/test_index.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `batch_url(batch_id: str) -> str`
  - `download_index(dest: Path) -> Path`
  - `download_batch(batch_id: str, dest_dir: Path) -> Path`
  - `read_index(path: Path, return_type: str = "990EZ") -> list[dict]`

Critical: directory browsing at that path **404s**. Batch files are reachable only by exact filename, which is the index's `XML_BATCH_ID` plus `.zip`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.corpus.index'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/corpus/index.py
"""Client for the IRS Form 990 e-file XML corpus.

Measured 2026-09-06: the 2026 index holds 385,890 returns of which 121,299 are
990-EZ. Directory listing at this path 404s -- files are reachable only by
exact filename, and a batch's filename is its XML_BATCH_ID plus '.zip'.
"""
import csv
from pathlib import Path

import requests

BASE = "https://apps.irs.gov/pub/epostcard/990/xml/2026"
INDEX_URL = f"{BASE}/index_2026.csv"
TIMEOUT = 300


def batch_url(batch_id: str) -> str:
    return f"{BASE}/{batch_id}.zip"


def _download(url: str, dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    response = requests.get(url, timeout=TIMEOUT, stream=True)
    response.raise_for_status()
    with open(dest, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1 << 20):
            handle.write(chunk)
    return dest


def download_index(dest: Path) -> Path:
    return _download(INDEX_URL, dest)


def download_batch(batch_id: str, dest_dir: Path) -> Path:
    return _download(batch_url(batch_id), Path(dest_dir) / f"{batch_id}.zip")


def read_index(path: Path, return_type: str = "990EZ") -> list[dict]:
    with open(path, newline="", encoding="latin-1") as handle:
        return [row for row in csv.DictReader(handle)
                if row.get("RETURN_TYPE") == return_type]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_index.py -v`
Expected: 3 passed

- [ ] **Step 5: Verify against the live IRS server**

Run:
```bash
PYTHONPATH=src python -c "
from pathlib import Path
from ninetyninety.corpus.index import download_index, read_index
rows = read_index(download_index(Path('data/index_2026.csv')))
print('990-EZ returns:', len(rows))
print('first batch id:', rows[0]['XML_BATCH_ID'])"
```
Expected: `990-EZ returns: 121299` and a batch id like `2026_TEOS_XML_01A`.

- [ ] **Step 6: Commit**

```bash
git add src/ninetyninety/corpus/index.py tests/test_index.py
git commit -m "feat: add IRS 990 corpus index client"
```

---

### Task 5: 990-EZ XML parser

**Files:**
- Create: `src/ninetyninety/corpus/xmlparse.py`, `tests/test_xmlparse.py`

**Interfaces:**
- Consumes: `REVENUE_LINES`, `EXPENSE_LINES` (Task 2)
- Produces:
  - `FiledReturn(ein: str, name: str, tax_period: str, amounts: dict[str, int], filed: dict[str, int])`
  - `parse_990ez(xml_bytes: bytes) -> FiledReturn | None` — `None` when the document is not a 990-EZ
  - `iter_990ez(zip_path: Path) -> Iterator[FiledReturn]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_xmlparse.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_xmlparse.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.corpus.xmlparse'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/corpus/xmlparse.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_xmlparse.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ninetyninety/corpus/xmlparse.py tests/test_xmlparse.py
git commit -m "feat: parse IRS 990-EZ e-file XML"
```

---

### Task 6: The validation harness — the headline number

**Files:**
- Create: `src/ninetyninety/corpus/validate.py`, `scripts/validate.py`, `tests/test_validate.py`

**Interfaces:**
- Consumes: `iter_990ez`, `FiledReturn` (Task 5), `check_identities` (Task 3)
- Produces:
  - `score_return(filed_return: FiledReturn) -> dict[str, bool]`
  - `ValidationReport` with `.add(filed_return, scores)`, `.rate(key) -> float`, `.line9/.line17/.line18 -> tuple[int, int]`, `.mismatches: list[dict]`
  - `validate_batch(zip_path: Path, limit: int | None = None) -> ValidationReport`
  - `scripts/validate.py` writing `results/validation.json`

This is the project's central claim and the first shot of the video. Measured 2026-09-06 over 3,687 real returns in one batch: **line 9 = 100.00%**, line 17 = 99.97%, line 18 = 99.97%. Mismatches are real filed returns whose own stated totals disagree with their own components — surface them, they are interesting.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.corpus.validate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/corpus/validate.py
"""Reconstruct real filed 990-EZ returns from their own components.

Runs the SAME formmath module that fills a user's form, so the accuracy rate
it publishes describes the real code path rather than a validation-only
reimplementation.
"""
from dataclasses import dataclass, field
from pathlib import Path

from ..formmath import check_identities
from .xmlparse import FiledReturn, iter_990ez

KEYS = ("line9", "line17", "line18")


def score_return(filed_return: FiledReturn) -> dict[str, bool]:
    return check_identities(filed_return.amounts, filed_return.filed)


@dataclass
class ValidationReport:
    total: int = 0
    matched: dict[str, int] = field(default_factory=lambda: {k: 0 for k in KEYS})
    checked: dict[str, int] = field(default_factory=lambda: {k: 0 for k in KEYS})
    mismatches: list[dict] = field(default_factory=list)

    def add(self, filed_return: FiledReturn, scores: dict[str, bool]) -> None:
        self.total += 1
        for key in KEYS:
            if key not in filed_return.filed:
                continue
            self.checked[key] += 1
            if scores[key]:
                self.matched[key] += 1
            else:
                self.mismatches.append({
                    "ein": filed_return.ein, "name": filed_return.name,
                    "key": key, "filed": filed_return.filed.get(key),
                    "components": filed_return.amounts,
                })

    def rate(self, key: str) -> float:
        if not self.checked[key]:
            return 0.0
        return 100.0 * self.matched[key] / self.checked[key]

    @property
    def line9(self) -> tuple[int, int]:
        return self.matched["line9"], self.checked["line9"]

    @property
    def line17(self) -> tuple[int, int]:
        return self.matched["line17"], self.checked["line17"]

    @property
    def line18(self) -> tuple[int, int]:
        return self.matched["line18"], self.checked["line18"]


def validate_batch(zip_path: Path, limit: int | None = None) -> ValidationReport:
    report = ValidationReport()
    for filed_return in iter_990ez(Path(zip_path)):
        report.add(filed_return, score_return(filed_return))
        if limit is not None and report.total >= limit:
            break
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_validate.py -v`
Expected: 5 passed

- [ ] **Step 5: Write the runner script**

```python
# scripts/validate.py
"""Download a real IRS batch and publish the reconstruction accuracy rate."""
import json
from pathlib import Path

from ninetyninety.corpus.index import download_batch
from ninetyninety.corpus.validate import validate_batch

BATCH = "2026_TEOS_XML_01A"
LABELS = (("line9", "Line 9  total revenue "),
          ("line17", "Line 17 total expenses"),
          ("line18", "Line 18 excess/deficit"))


def main() -> None:
    report = validate_batch(download_batch(BATCH, Path("data")))
    print(f"990-EZ returns: {report.total}")
    for key, label in LABELS:
        print(f"  {label} {report.matched[key]}/{report.checked[key]}"
              f"  ({report.rate(key):.2f}%)")
    print(f"  filed returns whose own totals disagree: {len(report.mismatches)}")

    Path("results").mkdir(exist_ok=True)
    Path("results/validation.json").write_text(json.dumps({
        "batch": BATCH,
        "returns": report.total,
        "matched": report.matched,
        "checked": report.checked,
        "rates": {key: round(report.rate(key), 2) for key in report.matched},
        "mismatch_count": len(report.mismatches),
        "mismatches": report.mismatches[:20],
    }, indent=2), encoding="utf-8")
    print("wrote results/validation.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run it against real IRS data**

Run: `PYTHONPATH=src python scripts/validate.py`
Expected: approximately
```
990-EZ returns: 3687
  Line 9  total revenue  3632/3632  (100.00%)
  Line 17 total expenses 3617/3618  (99.97%)
  Line 18 excess/deficit 3620/3621  (99.97%)
```
If line 9 is below 99%, an element name in `lines.py` is wrong. Fix it before continuing — this number is the pitch.

- [ ] **Step 7: Commit**

```bash
git add src/ninetyninety/corpus/validate.py scripts/validate.py tests/test_validate.py results/validation.json
git commit -m "feat: add reconstruction accuracy harness over real IRS filings"
```

---

### Task 7: Ledger model and the demo ledger

**Files:**
- Create: `src/ninetyninety/ledger.py`, `fixtures/demo_ledger.csv`, `fixtures/README.md`, `tests/test_ledger.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Transaction(date: str, description: str, amount: int, source_row: int)`
  - `parse_amount(raw: str) -> int`
  - `load_ledger(path: Path) -> list[Transaction]`

Whole dollars as integers; positive is money in, negative is money out. The demo ledger must contain genuinely messy uncategorised descriptions — that mess is the agent's job, and a pre-categorised ledger would collapse this project into a spreadsheet with a PDF filler.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ledger.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.ledger'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/ledger.py
"""The organisation's raw transaction ledger -- the messy input.

Whole dollars as integers. Positive is money in, negative is money out.
`source_row` is the 1-based CSV line number, so every form line can cite the
exact rows it came from.
"""
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transaction:
    date: str
    description: str
    amount: int
    source_row: int


def parse_amount(raw: str) -> int:
    text = str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not text:
        raise ValueError("empty amount")
    parenthesised = text.startswith("(") and text.endswith(")")
    if parenthesised:
        text = text[1:-1]
    value = float(text)
    rounded = int(value + 0.5) if value >= 0 else -int(-value + 0.5)
    return -rounded if parenthesised else rounded


def load_ledger(path: Path) -> list[Transaction]:
    transactions: list[Transaction] = []
    with open(Path(path), newline="", encoding="utf-8-sig") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            description = (row.get("description") or "").strip()
            if not description:
                continue
            try:
                amount = parse_amount(row.get("amount") or "")
            except ValueError:
                continue
            transactions.append(Transaction(
                date=(row.get("date") or "").strip(),
                description=description,
                amount=amount,
                source_row=row_number,
            ))
    return transactions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_ledger.py -v`
Expected: 4 passed

- [ ] **Step 5: Create the demo ledger**

Write `fixtures/demo_ledger.csv` with at least 40 rows for a plausible small community organisation. Every description is raw bank-statement text with **no category column** — abbreviations, vendor codes, ALL CAPS. Include at least one of each: an obvious donation, a government program contract payment, membership dues, bank interest, a fundraising event deposit paired with its direct costs, merchandise sales paired with cost of goods, payroll, a contractor payment that superficially resembles payroll, rent, a utility bill, postage, and at least two genuinely ambiguous rows the two agents can disagree about. Opening rows:

```csv
date,description,amount
2025-01-08,ONLINE DONATION STRIPE PAYOUT BATCH 4471,1250.00
2025-01-12,IL DEPT HUMAN SVCS CONTRACT PMT Q1 YOUTH PRG,8750.00
2025-01-15,ANNUAL MEMBER DUES 14 @ 25,350.00
2025-01-31,INTEREST PAID FIRST COMMUNITY BK,9.14
2025-02-03,ACH PAYROLL ADP RUN 0203,(3120.00)
2025-02-04,VENMO J MARTINEZ SAT WORKSHOP INSTRUCTION,(600.00)
2025-02-05,ELGIN PROPERTIES LLC FEB RENT,(1450.00)
```

Write `fixtures/README.md` stating plainly: this ledger is synthetic and illustrative; the accuracy numbers in this project come from real IRS filings, not from this file.

- [ ] **Step 6: Commit**

```bash
git add src/ninetyninety/ledger.py fixtures/ tests/test_ledger.py
git commit -m "feat: add ledger model and synthetic demo ledger"
```

---

### Task 8: Model configuration

**Files:**
- Create: `src/ninetyninety/config.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces: `select_provider(env: dict) -> str | None`, `build_model(provider: str | None = None)`

`build_model` takes an explicit provider so a caller can retry on the other one after a 429 — key presence alone is not a failover.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import pytest

from ninetyninety.config import build_model, select_provider


def test_select_provider_prefers_gemini():
    assert select_provider({"GOOGLE_API_KEY": "x",
                            "OPENROUTER_API_KEY": "y"}) == "gemini"


def test_select_provider_falls_back_to_openrouter():
    assert select_provider({"OPENROUTER_API_KEY": "x"}) == "openrouter"


def test_select_provider_none_when_unconfigured():
    assert select_provider({}) is None


def test_build_model_raises_with_setup_instructions(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="aistudio.google.com"):
        build_model()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/config.py
"""Model provider selection.

Gemini's free tier needs no credit card; its exact quota is no longer
published, so read the live numbers at aistudio.google.com/rate-limit.
"""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL_ID = "gemini-2.5-flash"
OPENROUTER_MODEL_ID = "z-ai/glm-5.2:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def select_provider(env: dict) -> str | None:
    if env.get("GOOGLE_API_KEY"):
        return "gemini"
    if env.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return None


def build_model(provider: str | None = None):
    provider = provider or select_provider(os.environ)
    if provider == "gemini":
        from strands.models.gemini import GeminiModel
        return GeminiModel(
            client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
            model_id=GEMINI_MODEL_ID,
        )
    if provider == "openrouter":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": os.environ["OPENROUTER_API_KEY"],
                         "base_url": OPENROUTER_BASE_URL},
            model_id=OPENROUTER_MODEL_ID,
        )
    raise RuntimeError(
        "No model provider configured. Get a free key at "
        "https://aistudio.google.com/apikey and set GOOGLE_API_KEY, "
        "or set OPENROUTER_API_KEY. See .env.example."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ninetyninety/config.py tests/test_config.py
git commit -m "feat: add model provider selection with explicit failover"
```

---

### Task 9: Preparer and Reviewer agents

**Files:**
- Create: `src/ninetyninety/agents.py`, `src/ninetyninety/graph.py`, `tests/test_agents.py`

**Interfaces:**
- Consumes: `lines` (Task 2)
- Produces:
  - `Classification(source_row: int, line_number: str, rationale: str, rule: str, confidence: str)`
  - `line_reference() -> str`
  - `build_preparer(model) -> Agent`, `build_reviewer(model) -> Agent`
  - `parse_classification(text: str, source_row: int) -> Classification | None`
  - `graph.build_review_graph(model)`

The Reviewer is a genuinely independent second opinion, not a rubber stamp: it sees the transaction and the line menu but **not** the Preparer's rationale, so agreement carries information.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents.py
from ninetyninety.agents import line_reference, parse_classification


def test_parse_classification_reads_the_structured_reply():
    text = ("LINE: 13\n"
            "RULE: line 13 covers payments to non-employees\n"
            "WHY: Venmo to an individual instructor, not payroll\n"
            "CONFIDENCE: high")
    result = parse_classification(text, source_row=7)
    assert result.line_number == "13"
    assert result.source_row == 7
    assert result.confidence == "high"
    assert "non-employees" in result.rule


def test_parse_classification_rejects_a_line_not_on_the_form():
    assert parse_classification("LINE: 99\nRULE: x\nWHY: y\nCONFIDENCE: high",
                                source_row=1) is None


def test_parse_classification_rejects_unstructured_output():
    assert parse_classification("I think this is probably rent?",
                                source_row=1) is None


def test_parse_classification_defaults_missing_confidence_to_low():
    assert parse_classification("LINE: 1\nRULE: r\nWHY: w",
                                source_row=1).confidence == "low"


def test_line_reference_lists_every_line_with_guidance():
    reference = line_reference()
    assert "5c" in reference and "6d" in reference
    assert "independent contractors" in reference
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_agents.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.agents'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/agents.py
"""The two Strands Agents.

Preparer classifies each transaction to a Form 990-EZ Part I line and cites
the rule. Reviewer independently classifies the SAME transaction without
seeing the Preparer's reasoning, so agreement is real corroboration and
disagreement is shown to the user rather than silently resolved.

Neither agent ever computes a total -- see formmath.py.
"""
import re
from dataclasses import dataclass

from strands import Agent

from .lines import ALL_LINE_NUMBERS, EXPENSE_LINES, REVENUE_LINES


@dataclass
class Classification:
    source_row: int
    line_number: str
    rationale: str
    rule: str
    confidence: str


def line_reference() -> str:
    parts = ["REVENUE LINES (money in):"]
    parts += [f"  Line {line.number}: {line.label}\n    {line.guidance}"
              for line in REVENUE_LINES]
    parts.append("EXPENSE LINES (money out):")
    parts += [f"  Line {line.number}: {line.label}\n    {line.guidance}"
              for line in EXPENSE_LINES]
    return "\n".join(parts)


_ANSWER_FORMAT = """Answer in exactly this format and nothing else:

LINE: <the line number, e.g. 1 or 5c or 13>
RULE: <the sentence from the line guidance that decides it>
WHY: <one sentence tying this transaction's wording to that rule>
CONFIDENCE: <high|medium|low>

Use CONFIDENCE: low when the description is genuinely ambiguous. Never invent a
line number that is not listed. Never compute totals."""


def _prompt(role: str) -> str:
    return f"""{role}

You classify one transaction from a small US nonprofit's bank ledger onto a
line of IRS Form 990-EZ Part I.

{line_reference()}

Money in must go to a revenue line; money out must go to an expense line.

{_ANSWER_FORMAT}"""


PREPARER_PROMPT = _prompt(
    "You are a bookkeeper preparing a nonprofit's Form 990-EZ.")

REVIEWER_PROMPT = _prompt(
    "You are an independent reviewer auditing a nonprofit's Form 990-EZ. You "
    "have NOT seen anyone else's opinion of this transaction. Form your own "
    "judgement from the description alone.")


def build_preparer(model) -> Agent:
    return Agent(model=model, system_prompt=PREPARER_PROMPT)


def build_reviewer(model) -> Agent:
    return Agent(model=model, system_prompt=REVIEWER_PROMPT)


def _field(text: str, name: str) -> str:
    match = re.search(rf"^{name}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_classification(text: str, source_row: int) -> Classification | None:
    number = _field(text, "LINE")
    if number not in ALL_LINE_NUMBERS:
        return None
    confidence = _field(text, "CONFIDENCE").lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    return Classification(
        source_row=source_row,
        line_number=number,
        rationale=_field(text, "WHY"),
        rule=_field(text, "RULE"),
        confidence=confidence,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_agents.py -v`
Expected: 5 passed

- [ ] **Step 5: Add the Strands graph**

```python
# src/ninetyninety/graph.py
"""Strands Agents multi-agent wiring: preparer -> reviewer."""
from strands.multiagent import GraphBuilder

from .agents import build_preparer, build_reviewer


def build_review_graph(model):
    builder = GraphBuilder()
    builder.add_node(build_preparer(model), "preparer")
    builder.add_node(build_reviewer(model), "reviewer")
    builder.add_edge("preparer", "reviewer")
    builder.set_entry_point("preparer")
    return builder.build()
```

- [ ] **Step 6: Verify the Strands API against the installed wheel**

Run: `PYTHONPATH=src python -c "from ninetyninety.graph import build_review_graph; print('graph ok')"`
Expected: `graph ok`

If `add_node`, `add_edge` or `set_entry_point` raise `AttributeError`, run
`python -c "from strands.multiagent import GraphBuilder; print([m for m in dir(GraphBuilder) if not m.startswith('_')])"`
and correct the calls before continuing.

- [ ] **Step 7: Commit**

```bash
git add src/ninetyninety/agents.py src/ninetyninety/graph.py tests/test_agents.py
git commit -m "feat: add Preparer and Reviewer agents with Strands graph"
```

---

### Task 10: Orchestration — ledger to form

**Files:**
- Create: `src/ninetyninety/prepare.py`, `cli.py`, `tests/test_prepare.py`

**Interfaces:**
- Consumes: `Transaction` (Task 7), `Classification`/`build_preparer`/`build_reviewer`/`parse_classification` (Task 9), `formmath` (Task 3)
- Produces:
  - `LineResult(line_number: str, amount: int, transactions: list[dict])`
  - `Form990EZ(lines: dict[str, LineResult], totals: dict[str, int], disagreements: list[dict], low_confidence: list[dict])`
  - `assemble(rows: list[tuple[Transaction, Classification, Classification]]) -> Form990EZ`
  - `prepare_ledger(transactions: list[Transaction], model) -> Form990EZ`

`assemble` is pure and fully tested; only `prepare_ledger` calls the model. On disagreement the Preparer's line is used **and** the row is recorded — never silently dropped.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prepare.py
from ninetyninety.agents import Classification
from ninetyninety.ledger import Transaction
from ninetyninety.prepare import assemble


def tx(row, description, amount):
    return Transaction(date="2025-01-01", description=description,
                       amount=amount, source_row=row)


def cls(row, line, confidence="high"):
    return Classification(source_row=row, line_number=line, rationale="r",
                          rule="rule", confidence=confidence)


def test_agreed_rows_are_summed_onto_their_line():
    form = assemble([
        (tx(2, "DONATION", 1000), cls(2, "1"), cls(2, "1")),
        (tx(3, "DONATION", 250), cls(3, "1"), cls(3, "1")),
    ])
    assert form.lines["1"].amount == 1250
    assert form.totals["line9"] == 1250


def test_expense_rows_are_stored_as_positive_amounts():
    form = assemble([(tx(2, "RENT", -1450), cls(2, "14"), cls(2, "14"))])
    assert form.lines["14"].amount == 1450
    assert form.totals["line17"] == 1450
    assert form.totals["line18"] == -1450


def test_disagreement_uses_preparer_and_is_recorded():
    form = assemble([(tx(4, "VENMO INSTRUCTOR", -600),
                      cls(4, "13"), cls(4, "12"))])
    assert form.lines["13"].amount == 600
    assert form.disagreements[0]["source_row"] == 4
    assert form.disagreements[0]["preparer"] == "13"
    assert form.disagreements[0]["reviewer"] == "12"


def test_low_confidence_rows_are_flagged_even_when_agreed():
    form = assemble([(tx(5, "MISC", 40), cls(5, "8", "low"), cls(5, "8", "low"))])
    assert form.low_confidence[0]["source_row"] == 5
    assert form.disagreements == []


def test_every_line_keeps_its_citing_transactions():
    form = assemble([(tx(9, "STRIPE PAYOUT", 1250), cls(9, "1"), cls(9, "1"))])
    citation = form.lines["1"].transactions[0]
    assert citation["source_row"] == 9
    assert citation["description"] == "STRIPE PAYOUT"
    assert citation["rule"] == "rule"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_prepare.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ninetyninety.prepare'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ninetyninety/prepare.py
"""Turn a classified ledger into a Form 990-EZ Part I.

`assemble` is pure and deterministic. Totals come from formmath, never from a
model. Where the two agents disagree the Preparer's line is used and the row
is surfaced for a human to resolve.
"""
from dataclasses import dataclass, field

from .agents import (
    Classification, build_preparer, build_reviewer, parse_classification,
)
from .formmath import excess_or_deficit, total_expenses, total_revenue
from .ledger import Transaction


@dataclass
class LineResult:
    line_number: str
    amount: int = 0
    transactions: list[dict] = field(default_factory=list)


@dataclass
class Form990EZ:
    lines: dict[str, LineResult] = field(default_factory=dict)
    totals: dict[str, int] = field(default_factory=dict)
    disagreements: list[dict] = field(default_factory=list)
    low_confidence: list[dict] = field(default_factory=list)


def assemble(
    rows: list[tuple[Transaction, Classification, Classification]],
) -> Form990EZ:
    form = Form990EZ()
    for transaction, preparer, reviewer in rows:
        chosen = preparer.line_number
        result = form.lines.setdefault(chosen, LineResult(chosen))
        result.amount += abs(transaction.amount)
        result.transactions.append({
            "source_row": transaction.source_row,
            "date": transaction.date,
            "description": transaction.description,
            "amount": transaction.amount,
            "rule": preparer.rule,
            "why": preparer.rationale,
        })
        if reviewer.line_number != chosen:
            form.disagreements.append({
                "source_row": transaction.source_row,
                "description": transaction.description,
                "preparer": chosen,
                "preparer_rule": preparer.rule,
                "reviewer": reviewer.line_number,
                "reviewer_rule": reviewer.rule,
            })
        elif "low" in (preparer.confidence, reviewer.confidence):
            form.low_confidence.append({
                "source_row": transaction.source_row,
                "description": transaction.description,
                "line": chosen,
            })

    amounts = {number: result.amount for number, result in form.lines.items()}
    form.totals = {
        "line9": total_revenue(amounts),
        "line17": total_expenses(amounts),
        "line18": excess_or_deficit(amounts),
    }
    return form


def _ask(agent, transaction: Transaction) -> Classification | None:
    direction = "MONEY IN" if transaction.amount >= 0 else "MONEY OUT"
    question = (f"{direction}\nDATE: {transaction.date}\n"
                f"DESCRIPTION: {transaction.description}\n"
                f"AMOUNT: {abs(transaction.amount)}")
    return parse_classification(str(agent(question)), transaction.source_row)


def prepare_ledger(transactions: list[Transaction], model) -> Form990EZ:
    preparer, reviewer = build_preparer(model), build_reviewer(model)
    rows = []
    for transaction in transactions:
        first = _ask(preparer, transaction)
        if first is None:
            continue
        rows.append((transaction, first, _ask(reviewer, transaction) or first))
    return assemble(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_prepare.py -v`
Expected: 5 passed

- [ ] **Step 5: Write the CLI**

```python
# cli.py
"""NinetyNinety CLI -- draft a Form 990-EZ from a transaction ledger.

Usage: PYTHONPATH=src python cli.py fixtures/demo_ledger.csv
"""
import sys
from pathlib import Path

from ninetyninety.config import build_model
from ninetyninety.ledger import load_ledger
from ninetyninety.lines import line_by_number
from ninetyninety.prepare import prepare_ledger


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    transactions = load_ledger(Path(argv[1]))
    print(f"Loaded {len(transactions)} transactions. Classifying...")
    form = prepare_ledger(transactions, build_model())

    print("\nFORM 990-EZ PART I (DRAFT -- NOT A FILING)")
    for number in sorted(form.lines, key=lambda n: (len(n), n)):
        result = form.lines[number]
        print(f"  Line {number:<4} {line_by_number(number).label[:44]:<46}"
              f"{result.amount:>10,}  ({len(result.transactions)} txns)")
    print(f"\n  Line 9  total revenue   {form.totals['line9']:>10,}")
    print(f"  Line 17 total expenses  {form.totals['line17']:>10,}")
    print(f"  Line 18 excess/deficit  {form.totals['line18']:>10,}")
    print(f"\nDisagreements: {len(form.disagreements)}   "
          f"Low confidence: {len(form.low_confidence)}")
    for item in form.disagreements:
        print(f"  row {item['source_row']}: {item['description'][:44]}")
        print(f"     preparer line {item['preparer']} "
              f"vs reviewer line {item['reviewer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 6: Run the CLI end to end**

Run: `PYTHONPATH=src python cli.py fixtures/demo_ledger.csv`
Expected: a Part I listing, three totals, and at least one printed disagreement. **Zero disagreements means the demo ledger is not ambiguous enough** — add genuinely borderline rows before continuing, because the disagreement is the centrepiece of the video.

- [ ] **Step 7: Commit**

```bash
git add src/ninetyninety/prepare.py cli.py tests/test_prepare.py
git commit -m "feat: assemble classified ledger into Form 990-EZ Part I"
```

---

### Task 11: Fill the real IRS PDF

**Files:**
- Create: `src/ninetyninety/pdffill.py`, `scripts/dump_fields.py`, `tests/test_pdffill.py`

**Interfaces:**
- Consumes: `Form990EZ` (Task 10)
- Produces:
  - `download_form(dest: Path) -> Path`
  - `field_map() -> dict[str, str]`
  - `fill_form(form: Form990EZ, template: Path, dest: Path, org_name: str, ein: str) -> Path`

The blank form is 397,623 bytes with 385 AcroForm fields. Field names must be **discovered, never guessed**.

- [ ] **Step 1: Write pdffill with an empty map, plus the field dumper**

```python
# src/ninetyninety/pdffill.py
"""Fill the real IRS Form 990-EZ AcroForm.

The blank form has 385 fields. FIELD_MAP is populated from the exact names
printed by scripts/dump_fields.py -- never guess them.

Output is always a DRAFT: e-filing requires an Authorized IRS e-File Provider
EFIN, which this project does not have.
"""
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter

FORM_URL = "https://www.irs.gov/pub/irs-pdf/f990ez.pdf"

# Keys are our line numbers plus "line9"/"line17"/"line18"/"org_name"/"ein".
# Values are exact AcroForm field names from scripts/dump_fields.py.
FIELD_MAP: dict[str, str] = {}


def download_form(dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    response = requests.get(FORM_URL, timeout=120)
    response.raise_for_status()
    dest.write_bytes(response.content)
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

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as handle:
        writer.write(handle)
    return dest
```

```python
# scripts/dump_fields.py
"""Print every AcroForm field in the blank IRS Form 990-EZ."""
from pathlib import Path

from pypdf import PdfReader

from ninetyninety.pdffill import download_form


def main() -> None:
    fields = PdfReader(str(download_form(Path("data/f990ez.pdf")))).get_fields() or {}
    print(f"{len(fields)} fields")
    for name, spec in fields.items():
        print(f"  {name}\t{spec.get('/FT')}\t{str(spec.get('/TU'))[:70]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Discover the real field names**

Run: `PYTHONPATH=src python scripts/dump_fields.py > data/fields.txt && head -40 data/fields.txt`
Expected: `385 fields` followed by the list. The `/TU` tooltip column names the line each field belongs to — use it to build the map.

- [ ] **Step 3: Write the failing test**

```python
# tests/test_pdffill.py
from ninetyninety.lines import ALL_LINE_NUMBERS
from ninetyninety.pdffill import field_map


def test_field_map_covers_every_part_one_line():
    mapping = field_map()
    for number in ALL_LINE_NUMBERS:
        assert number in mapping, f"line {number} has no PDF field"


def test_field_map_includes_the_three_totals_and_the_header():
    mapping = field_map()
    for key in ("line9", "line17", "line18", "org_name", "ein"):
        assert key in mapping


def test_field_names_are_non_empty_strings():
    for name in field_map().values():
        assert isinstance(name, str) and name.strip()
```

Run: `PYTHONPATH=src pytest tests/test_pdffill.py -v`
Expected: FAIL — `FIELD_MAP` is still empty.

- [ ] **Step 4: Populate FIELD_MAP from `data/fields.txt` and re-run**

Fill in every key from the test above using the exact names the dumper printed.

Run: `PYTHONPATH=src pytest tests/test_pdffill.py -v`
Expected: 3 passed

- [ ] **Step 5: Produce a real filled PDF and open it**

```bash
PYTHONPATH=src python -c "
from pathlib import Path
from ninetyninety.agents import Classification
from ninetyninety.ledger import load_ledger
from ninetyninety.pdffill import download_form, fill_form
from ninetyninety.prepare import assemble
txs = load_ledger(Path('fixtures/demo_ledger.csv'))
rows = [(t, Classification(t.source_row, '1' if t.amount >= 0 else '16', 'r', 'rule', 'high'),
             Classification(t.source_row, '1' if t.amount >= 0 else '16', 'r', 'rule', 'high'))
        for t in txs]
print('wrote', fill_form(assemble(rows), download_form(Path('data/f990ez.pdf')),
                         Path('out/draft.pdf'), 'DEMO COMMUNITY ORG', '00-0000000'))"
```
Expected: `wrote out\draft.pdf`. Open it — amounts must land in the correct boxes on the real IRS form.

- [ ] **Step 6: Commit**

```bash
git add src/ninetyninety/pdffill.py scripts/dump_fields.py tests/test_pdffill.py
git commit -m "feat: fill the real IRS Form 990-EZ AcroForm"
```

---

### Task 12: Streamlit app and deploy

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `load_ledger`, `prepare_ledger`, `build_model`, `line_by_number`, `results/validation.json`
- Produces: a public `*.streamlit.app` URL

- [ ] **Step 1: Write the app**

```python
# app.py
"""NinetyNinety -- draft an IRS Form 990-EZ from a nonprofit's raw ledger.

Built with Strands Agents.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

from ninetyninety.config import build_model
from ninetyninety.ledger import load_ledger
from ninetyninety.lines import line_by_number
from ninetyninety.prepare import prepare_ledger

st.set_page_config(page_title="NinetyNinety", layout="wide")
st.title("NinetyNinety")
st.caption("A shoebox of bank transactions becomes a drafted IRS Form 990-EZ -- "
           "every line citing the transactions and the rule behind it. "
           "Built with Strands Agents.")
st.warning("**DRAFT -- not a filing.** An officer of the organisation must "
           "review and sign. E-filing requires an Authorized IRS e-File Provider.")

report_path = Path("results/validation.json")
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
    st.caption("Source: IRS Form 990 e-file XML, "
               "apps.irs.gov/pub/epostcard/990/xml/2026/")

st.divider()
st.subheader("Draft a return")
uploaded = st.file_uploader("Transaction ledger (CSV: date, description, amount)",
                            type="csv")
use_demo = st.checkbox("Use the synthetic demo ledger instead", value=True)

if st.button("Draft the 990-EZ", type="primary"):
    path = Path("fixtures/demo_ledger.csv")
    if uploaded is not None and not use_demo:
        path = Path("data/uploaded.csv")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(uploaded.getvalue())

    transactions = load_ledger(path)
    st.write(f"Loaded **{len(transactions)}** transactions.")
    try:
        with st.spinner("Preparer and Reviewer agents classifying each line..."):
            form = prepare_ledger(transactions, build_model())
    except Exception as error:  # noqa: BLE001 - surface any failure to the user
        st.error(f"Could not complete the draft: {error}")
        st.stop()

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### Form 990-EZ Part I")
        for number in sorted(form.lines, key=lambda n: (len(n), n)):
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

    with right:
        st.markdown(f"#### Agent disagreements ({len(form.disagreements)})")
        st.caption("The Reviewer never sees the Preparer's reasoning, so these "
                   "are two independent readings of the same transaction.")
        for item in form.disagreements:
            st.warning(f"**row {item['source_row']}** · {item['description']}\n\n"
                       f"Preparer → line {item['preparer']}: {item['preparer_rule']}\n\n"
                       f"Reviewer → line {item['reviewer']}: {item['reviewer_rule']}")
        st.markdown(f"#### Low confidence ({len(form.low_confidence)})")
        for item in form.low_confidence:
            st.info(f"row {item['source_row']} · {item['description']} "
                    f"→ line {item['line']}")
```

- [ ] **Step 2: Run locally**

Run: `streamlit run app.py`
Expected: validation metrics render at the top; clicking "Draft the 990-EZ" produces Part I lines with citations and at least one disagreement.

- [ ] **Step 3: Push and deploy**

```bash
git add app.py
git commit -m "feat: add Streamlit UI"
gh repo create ninetyninety --public --source=. --push
```

At https://share.streamlit.io — New app, pick the repo, main file `app.py`, add `GOOGLE_API_KEY` under Advanced settings → Secrets, Deploy. Record the public URL.

- [ ] **Step 4: Verify the deployed URL in a private window**

Expected: renders for a logged-out visitor. If not, the live-demo link is invalid — fix before submitting.

---

### Task 13: Submission deliverables

**Files:**
- Create: `README.md`, `docs/architecture.png`

- [ ] **Step 1: Write the README**

In order: the one-sentence problem; who it is for (US nonprofits under $200,000 gross receipts with no finance staff); **the validation result — 3,632/3,632 line 9 reconstructions against real IRS filings**; an explicit **"Built with Strands Agents"** line; the architecture diagram; setup a stranger can follow cold (`git clone`, `pip install -r requirements.txt`, free key at https://aistudio.google.com/apikey, `PYTHONPATH=src python cli.py fixtures/demo_ledger.csv`); the live demo URL; and a limitations section stating: the output is a **draft, not a filing**; e-filing requires an Authorized IRS e-File Provider EFIN; an officer must sign; the demo ledger is synthetic while the accuracy numbers come from real filings; only Part I is drafted, with other Parts and Schedules detected and flagged rather than completed.

- [ ] **Step 2: Draw the architecture diagram**

Per the hackathon FAQ, label: user input/interface (Streamlit web app, CLI); **Strands Agents core and its agentic loop (model → tools → reasoning → response)**, showing Preparer and Reviewer as separate nodes; tools and integrations (IRS 990 e-file XML corpus, `f990ez.pdf` AcroForm, Gemini API); AWS services used — state plainly: AWS Builder ID for submission, no AWS runtime service, model provider is Gemini; and the output (drafted Part I with per-line citations, disagreement list, filled PDF). Export to `docs/architecture.png`.

- [ ] **Step 3: Create the AWS Builder ID**

https://builder.aws.com — free, no credit card, independent of any AWS account. Record the email; the submission form asks for it.

- [ ] **Step 4: Record the video (≤5 minutes, public on YouTube)**

Winner evidence: all three podium videos ran 2:24–3:51, while both 9–15 minute videos took lower prizes. Open on the verified number, not the product.

1. **0:00–0:20 — the proof, first.** The validation screen. *"Before I show you what this builds: we rebuilt 3,632 real Form 990-EZ returns filed with the IRS from their own line items. 3,632 out of 3,632 exact."*
2. **0:20–0:50 — the problem.** A nonprofit under $200k has no bookkeeper and a shoebox of bank transactions. Tax990 charges $109.90 — **name the competitor** — but every one of those tools starts *after* the books are categorised. The categorising is the work.
3. **0:50–2:20 — the demo.** Load the messy ledger. Preparer and Reviewer classify. Open a line: the transactions that made it and the rule behind each. **Land on the disagreement** — Venmo to an instructor: Preparer says line 13 contractors, Reviewer says line 12 salaries. Show that it is surfaced, not hidden.
4. **2:20–2:50 — the filled form.** The real IRS PDF with the DRAFT notice visible. Say an officer must sign.
5. **2:50–3:20 — how it's built.** Name **Strands Agents** out loud. Show the two-node graph. State the rule: the model classifies and cites, Python does every total, and that is why the accuracy number means something.

Upload to YouTube, set Public.

- [ ] **Step 5: Publish three builder.aws posts (+0.6, ~10.7% of the 5.6 maximum)**

Publish at https://builder.aws.com with the AWS Builder ID. The hashtag requirement is contradictory across the rules and forum 45031 is unanswered, so each title carries **both** forms — e.g. `Rebuilding 3,632 IRS returns with Strands Agents for Humans #AgentsforHumans`. All three before Sep 14 5:00pm PT. The largest judge bloc is technical writers, so these posts are read by the people scoring you.

Suggested: (1) reconstructing 3,632 real IRS filings to prove an agent's arithmetic; (2) why the model must never compute a total; (3) an adversarial Preparer/Reviewer pair in Strands `GraphBuilder`, and what their disagreements revealed.

- [ ] **Step 6: Submit on Devpost**

**Good Neighbor Agents** track. Attach: public repo URL, text description (lead with the validation number, name Strands Agents explicitly), README, architecture diagram, YouTube link, AWS Builder ID email, and the live `*.streamlit.app` URL.

- [ ] **Step 7: Verify against the rules checklist**

- [ ] `LICENSE` at repo root, MIT, visible in GitHub's About sidebar
- [ ] Repo public, runs cold from the README
- [ ] README present · architecture diagram present and labelled per the FAQ
- [ ] Video ≤5 min, public, demo + problem/who/why
- [ ] AWS Builder ID entered · track = Good Neighbor Agents
- [ ] "Strands Agents" named in README, description, and video
- [ ] Live demo URL loads for a logged-out visitor
- [ ] Three builder.aws posts published, both hashtag forms in each title
- [ ] "DRAFT — not a filing" visible in the app, the PDF, and the video

- [ ] **Step 8: Commit**

```bash
git add README.md docs/
git commit -m "docs: add README and architecture diagram"
git push
```

---

## Submission Ladder

Devpost submissions can be edited until the deadline. Bank a valid entry early, then improve.

| Rung | Tasks | State |
|---|---|---|
| 1 | 1–6 | **The headline number exists.** Validation harness proven against real IRS filings |
| 2 | 7–10 | CLI drafts Part I from a messy ledger, with citations and disagreements |
| 3 | 13 steps 1–4, 6 | **VALID SUBMISSION BANKED** — repo, license, README, diagram, video, Builder ID |
| 4 | 11 | Filled real IRS PDF |
| 5 | 12 | Live demo URL → strengthens Technical Implementation |
| 6 | 13 step 5 | Three blog posts → +0.6 |

Rung 1 comes first because it *is* the pitch. If it fails, the concept fails on day one rather than day seven.

## Risks

| Risk | Mitigation |
|---|---|
| Judge reads it as "AI fills a tax form", like the 1040 project that placed 3rd | Video opens on the 3,632/3,632 validation, never on the form |
| "Tax990 already does this for $109.90" | Say it in the video and answer it: those tools require already-categorised books |
| Demo ledger is synthetic — the documented losing profile | The headline number comes from real filings; the ledger is labelled synthetic in the UI and in `fixtures/README.md` |
| Gemini free quota unpublished; per-transaction calls add up | A 40-row ledger is ~80 calls; `build_model("openrouter")` retry on 429 |
| Agents agree on everything, so the Reviewer looks decorative | Task 10 Step 6 fails the build if there are zero disagreements |
| PDF field names guessed | Task 11 Step 2 dumps the real 385 names before any mapping is written |
| Scope creep into the full 990, all Parts, or Schedules | Part I only. Other Parts and Schedules are detected and flagged, never filled |
