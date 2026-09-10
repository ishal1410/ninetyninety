# Devpost submission text

Copy each field into the Devpost form. Placeholders in angle brackets are filled by a human before submitting.

## Project name

NinetyNinety

## Tagline

Bank CSV in, drafted IRS Form 990-EZ out, every line cited.

## Track

Good Neighbor Agents. The user is a volunteer treasurer acting for a small nonprofit, and the track text names nonprofits and the volunteers who run them.

## Description

The IRS processed 203,699 Form 990-EZ returns in calendar year 2024, filed by 185,581 different organisations. Each one is small by definition: a 990-EZ filer has gross receipts under $200,000 and assets under $500,000. In the public IRS e-file batch this project was validated against, 1,106 of the 3,687 Form 990-EZ returns carry no paid-preparer block, so roughly three in ten were put together by someone inside the organisation, usually a volunteer treasurer doing it once a year out of a shoebox.

Getting it wrong is expensive at that size. A late Form 990-EZ costs $25 a day, up to the lesser of $13,000 or 5 percent of gross receipts. Miss three years in a row and exemption is revoked automatically: contributions stop being deductible, and the organisation has to apply for exemption again from the beginning. The IRS Auto-Revocation List downloaded on 8 September 2026 holds 1,247,210 revocations, and 1,065,726 of those rows carry no reinstatement date.

The form is not the hard part. Filing software exists, it is cheap, and it starts once the books are categorised. Categorising the books is the work nobody helps with. A year of a food pantry's bank account is a few hundred rows reading "SQUARE INC DEPOSIT", "ZELLE FROM R PATEL", "CHECK 1192 DELIA FIGUEROA CPA", and every one of them has to land on one of the fifteen Part I lines in a way the treasurer can defend to a board.

That is the step NinetyNinety does. It takes a bank export of date, description and amount and returns Form 990-EZ Part I drafted on the real IRS PDF, with every line showing the transactions behind it and the IRS instruction sentence that put them there.

Two agents do the sorting and neither can see the other. The Preparer and the Reviewer are separate entry nodes of a Strands `GraphBuilder` graph, so Strands hands each of them the same rows and nothing else. Where they agree, the row goes on the form with the rule they both quoted. Where they disagree, a conditional edge wakes a third agent, the Referee, which reads the IRS text for both candidate lines and picks one. The disagreement is printed with all three opinions and the line that was used. In the recorded run, "ACME HARDWARE GALA TABLE SPONSOR" drew line 6d from the Preparer and line 1 from the Reviewer; the Referee quoted the fundraising-event sentence and sent it to 6d, and the treasurer sees that whole exchange.

The agents classify. They never add. Lines 9, 17 and 18 are computed in Python by the same module that was checked against 3,632 real filed Form 990-EZ returns from the IRS e-file corpus, rebuilding each return's own stated totals from its own line items. Line 9 came back in 3,632 of 3,632 (100.00 percent), line 17 in 3,617 of 3,618 (99.97 percent), line 18 in 3,619 of 3,621 (99.94 percent). The three misses sit in two filed returns whose stated totals disagree with their own components, one of them by a dollar, and both are listed by EIN in `results/validation.json`.

What comes out is a draft. Every page carries a red DRAFT, NOT A FILING notice, an officer of the organisation has to review and sign it, and e-filing a 990-EZ for tax year 2025 needs an Authorized IRS e-File Provider, which this is not.

Where the numbers come from:

- 203,699 returns and 185,581 EINs: IRS SOI annual extract of Form 990-EZ filings processed in 2024, https://www.irs.gov/statistics/soi-tax-stats-annual-extract-of-tax-exempt-organization-financial-data (file `24eoextract990EZ.zip`, one row per processed return).
- $200,000 and $500,000 thresholds, the $25-a-day penalty and its cap, automatic revocation after three years, and the tax year 2025 electronic filing requirement: IRS Instructions for Form 990-EZ (2025), https://www.irs.gov/instructions/i990ez
- Consequences of revocation: IRS Automatic Revocation of Exemption FAQ, https://www.irs.gov/pub/irs-tege/auto_rev_faqs.pdf
- 1,247,210 revocations and 1,065,726 without a reinstatement date: IRS Auto-Revocation List bulk file, https://apps.irs.gov/pub/epostcard/data-download-revocation.zip, downloaded 2026-09-08 and counted row by row.
- 1,106 of 3,687 with no paid preparer: counted in the same IRS batch the accuracy harness uses. Reproduce with `PYTHONPATH=src python scripts/preparers.py`.
- The Part I accuracy rates: `PYTHONPATH=src python scripts/validate.py`, output in `results/validation.json`.

## How we built it

The obvious build is one agent with a classify tool and a careful prompt. That design has no way to tell a confident wrong answer from a right one, and telling those apart is what a treasurer signing under penalty of perjury needs most. So the graph is shaped to manufacture a second opinion first, and to spend a model call on arbitration only where the two opinions differ.

Each batch of twelve ledger rows becomes one Strands `GraphBuilder` graph. The Preparer and the Reviewer are both entry nodes, and that is what makes them blind: Strands passes an entry node the task text and nothing else, so the Reviewer never receives the Preparer's reasoning and cannot anchor on it. The two run in parallel. The Referee hangs off conditional edges from both entry nodes, and the condition compares the two structured outputs row by row, so on a batch where they agree the Referee node never executes and costs nothing. `set_max_node_executions(3)` caps the graph at one pass. In the recorded 54-row run the Referee ran on 1 batch out of 5.

All three agents carry one Strands `@tool`, `line_guidance`, which returns the IRS Part I instruction text for a line number. The prompts require them to call it for every line they intend to use and to copy the deciding sentence into their answer. Each agent returns pydantic structured output, `BatchCalls` for the two classifiers and `Verdicts` for the Referee, which is what turns "the agents disagree" into a boolean a graph edge can test. Strands passes that schema down to the provider as the response schema, so declaring `confidence` as a three-value `Literal` makes Gemini itself refuse an answer of "fairly low", which the low-confidence check downstream would otherwise have dropped without a word.

The parts of the code that look like fussy detail are the parts that took the reading. Part I line numbers do not sort as strings: 5c, 6d and 7c are revenue lines that print above line 10, and `"10" < "5c"` in Python, so form order is held as an explicit list in `lines.py` and everything sorts through it. The IRS XML element names in that same file were read off live e-file returns rather than guessed: putting back the two plausible-looking guesses they replaced (`NetGainOrLossFromSaleOfAssetsAmt` for 5c, `GrossProfitLossSalesOfInvntryAmt` for 7c) drops line 9 reconstruction over the same 3,632 returns from 100.00 percent to 86.62 percent. Lines 5c, 6d and 7c are net figures and may legitimately be negative, so a gala's venue deposit nets against the gala's ticket income on 6d instead of turning into an occupancy expense. Any row that pushes money against its line's direction is netted and flagged for a person, even after the Referee has settled the dispute, because a refund and a misfiled expense look identical in the arithmetic.

Python then checks the model. Every quoted rule, the Referee's included, is compared word by word against the IRS sentence the tool returned; at least 60 percent of its words must appear there, and the line's label does not count, because the label is already printed in the system prompt and quoting it back proves nothing. A Referee verdict is accepted only if it names one of the two disputed lines, so the tie-breaker cannot introduce a third line of its own. Totals come from `formmath.py`, and the amounts land in the actual `f990ez.pdf` AcroForm fields with a DRAFT stamp on every page.

The trace on screen comes from a Strands `HookProvider`. It registers callbacks on `BeforeToolCallEvent` and `AfterModelCallEvent` and counts model calls and tool calls per agent, so each batch shows which nodes ran, in what order, how many times each one called the model and the tool, whether the Referee was needed, and which model id answered.

The runtime provider is Google Gemini through Strands' native `GeminiModel`. The free tier caps each model id at 20 requests a day, so the batch runner rotates through five model ids, sleeps for the delay Gemini advertises on a 429 or a 5xx, and after three attempts hands the batch to the next id. A batch no model can answer is recorded as unclassified with the error text and the run continues.

The hosted Streamlit app has a "Replay the recorded run" button that rebuilds the form from `results/demo_run.json` without any model calls, so the demo still works when the day's quota is spent. Live runs use the same code path.

## Challenges we ran into

Amazon Bedrock was the first choice of provider. A new AWS account's applied Bedrock quota is 0 tokens a day for every model and region until AWS Support seeds it, and that did not happen before the deadline. The Bedrock code was written, then removed, because a one-provider story is clearer than a failover ladder; `BedrockModel` in place of `GeminiModel` is a one-line swap when the quota arrives.

That left the Gemini free tier, measured at 20 requests a day per model id. A graph with two parallel agents and a conditional third spends several requests per batch, so a single ledger cannot finish on one id. The fix was the rotation described above plus retry logic that matches status codes rather than substrings, after an early version treated a validation error echoing a $500 row as an HTTP 500.

Grounding was the other hard part. The first check counted the line's label, and agents passed it by quoting the menu. Only the instruction sentence counts now.

## Accomplishments

The arithmetic that fills the form was run against real filed returns before it was ever run for a user. IRS e-file batch 2026_TEOS_XML_01A holds 3,687 Form 990-EZ returns, 3,632 of them with a checkable Part I, and `formmath.py` rebuilt each return's stated totals from its own line items: line 9 in 3,632 of 3,632 (100.00 percent), line 17 in 3,617 of 3,618 (99.97 percent), line 18 in 3,619 of 3,621 (99.94 percent). Three line mismatches across two returns, and in both cases the filed return's own totals disagree with its own components. Both EINs are printed in `results/validation.json`. This is the same module that fills a user's PDF, not a validation-only reimplementation, and `PYTHONPATH=src python scripts/validate.py` regenerates the whole table from the public IRS batch.

The recorded demo run on 2026-09-08 classified 54 of 54 rows in 5 batches, with 2 disagreements, the Referee running on 1 batch, 92 tool calls and 577 seconds, all on the free tier.

The output is the real IRS PDF, filled, not a mockup.

## What we learned

Two blind agents plus a referee surface uncertainty better than one confident agent, but only if the disagreement is shown rather than resolved quietly. A judgement a treasurer has to sign is worth less as a clean answer than as a disputed one with both arguments attached. Structured output is what turns "the agents disagree" into a boolean a graph edge can test, and a conditional edge is what keeps the third opinion from costing anything on the batches that do not need it. A word-overlap check against the source text is cheap and catches invented rules that read well. And the model should never do arithmetic that Python can do and be checked against thousands of real filings.

## What's next

Parts II through VI and the Schedules, which today are out of scope and are not pretended to be filled. Bedrock as the provider once the account quota is seeded. A path to e-filing through an Authorized IRS e-File Provider, since the IRS requires electronic filing of Form 990-EZ for tax year 2025.

## Testing instructions

```
git clone https://github.com/ishal1410/ninetyninety && cd ninetyninety && pip install -r requirements.txt && cp .env.example .env
PYTHONPATH=src python cli.py fixtures/demo_ledger.csv
```

Paste a free Google AI Studio key into `.env` as `GOOGLE_API_KEY` before the second command; no card is needed. `streamlit run app.py` opens the web UI. `python -m pytest` runs the test suite.

Hosted app: https://ninetyninety.streamlit.app. Use "Replay the recorded run" if the day's free quota is already spent.

Product page: https://ishal1410.github.io/ninetyninety/
Technical page with the recorded trace: https://ishal1410.github.io/ninetyninety/technical.html

## Pre-existing work

The blank IRS form `f990ez.pdf` and the IRS Form 990 e-file XML corpus are public IRS assets used as inputs, not project code. The Strands Agents SDK is a third-party dependency. All project code was written during the submission period. `fixtures/demo_ledger.csv` is synthetic; the accuracy figures come from the real IRS filings, never from that file.

## Video

<YOUTUBE_URL>

## Repository

https://github.com/ishal1410/ninetyninety

## Architecture diagram

`docs/architecture.png` (source: `scripts/diagram.py`)
