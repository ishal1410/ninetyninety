# Agents for Humans: I checked my agent's arithmetic against 3,687 real IRS returns before letting it near a user

```
990-EZ returns: 3687
  Line 9  total revenue  3632/3632  (100.00%)
  Line 17 total expenses 3617/3618  (99.97%)
  Line 18 excess/deficit 3619/3621  (99.94%)
  filed returns whose own totals disagree: 3
```

That is `scripts/validate.py` running against one batch of the IRS Form 990 e-file corpus. The three misses are returns where the filer's own stated total does not equal the filer's own line items. One is a Little League whose line 17 is one dollar off from its line 14. The code is right; the filer rounded.

## Why an agent project needs this at all

NinetyNinety drafts Form 990-EZ from a nonprofit's bank ledger using a Strands Agents graph (Preparer, blind Reviewer, conditional Referee). The agents decide which Part I line each transaction belongs on. They are forbidden from adding anything up.

```python
def total_revenue(amounts: dict[str, int]) -> int:
    """Form 990-EZ Part I line 9 = sum of lines 1 through 8."""
    return sum(int(amounts.get(number, 0)) for number in _REVENUE_NUMBERS)
```

Thirty lines of Python. Boring on purpose. But "the model never does arithmetic" is only worth saying if the arithmetic it hands off to is actually the IRS's arithmetic, and the only way to know is to run it on returns the IRS has already accepted.

## The corpus

The IRS publishes every e-filed 990 as XML at `apps.irs.gov/pub/epostcard/990/xml/2026/`. The directory listing 404s; files are reachable only by exact name from an index CSV. The 2026 index holds 385,890 returns, of which 121,299 are 990-EZ. One zip batch, `2026_TEOS_XML_01A`, is 71 MB and yields the 3,687 990-EZ returns above.

Each return carries both its line items and its own stated totals:

```python
_FILED_ELEMENTS = (("line9", "TotalRevenueAmt"),
                   ("line17", "TotalExpensesAmt"),
                   ("line18", "ExcessOrDeficitForYearAmt"))
```

So the check is: parse the fifteen component elements, feed them through the same `formmath` module the app uses, compare against what the filer wrote on line 9, 17 and 18. Same code path, not a validation-only reimplementation.

## The mistake this caught

Two element names in the IRS schema are not what you would guess. Line 5c is `GainOrLossFromSaleOfAssetsAmt`, not `NetGainOrLoss…`. Line 7c is `GrossProfitLossSlsOfInvntryAmt`, not `…SalesOfInvntry…`. My first taxonomy guessed both, and the harness reported 87.5% reconstruction accuracy. It was two strings. After reading the live XML and fixing them: 100.00%.

Without the harness that bug ships silently. Every return with a 5c or 7c amount gets a wrong line 9, and the app would still print a confident total.

## What lands on the user's screen

The Streamlit app reads `results/validation.json` and shows the three rates above the upload box, with the batch id and a caption explaining that the misses are filer-side. A judge, or a treasurer, sees the evidence before the first model call.

## Takeaways

- If your agent hands a job to deterministic code, test that code against ground truth from the domain, not against fixtures you wrote.
- Government data is often published in an awkward but complete form. 71 MB of XML is a free test set of 3,687 accountant-reviewed answers.
- Put the validation number in the product, not only in the README.

Built with Strands Agents for the AWS Agents for Humans hackathon. Repo: https://github.com/ishal1410/ninetyninety
