# Devpost submission text

Copy each field into the Devpost form. Placeholders in angle brackets are filled by a human before submitting.

## Project name

NinetyNinety

## Tagline

Bank CSV in, drafted IRS Form 990-EZ out, every line cited.

## Track

Good Neighbor Agents. The user is a volunteer treasurer acting for a small nonprofit, and the track text names nonprofits and the volunteers who run them.

## Description

Small US nonprofits with gross receipts under $200,000 file IRS Form 990-EZ every year, most of them with no finance staff, and the IRS revokes tax-exempt status after three missed filings, so the revocation list now holds over a million entries. NinetyNinety is built with Strands Agents: it takes a raw bank export of date, description and amount, runs each batch of rows through a Strands graph of three agents, and produces a drafted Form 990-EZ Part I on the real IRS PDF where every line cites the transactions behind it and the IRS instruction sentence that put them there.

The problem is not the form. Filing tools exist, and they start after the books are categorised. Categorising the books is the work nobody helps with, and it is the reason the little league, the food pantry and the community band miss filings. That is the step this project does.

Two agents, a Preparer and a Reviewer, classify the same rows without seeing each other. When they agree, the row goes on the form with the rule they both cited. When they disagree, a third agent, the Referee, reads the IRS text for both candidate lines and rules. Every disagreement is shown on screen with all three opinions and which line was used. In the recorded demo run a row reading "ACME HARDWARE GALA TABLE SPONSOR" went to line 6d from the Preparer and line 1 from the Reviewer; the Referee cited the fundraising event text and put it on 6d, and the treasurer sees exactly that.

The model classifies. It never adds. Lines 9, 17 and 18 are computed in Python by the same module that was checked against 3,632 real Form 990-EZ returns from the IRS e-file corpus, where it rebuilt line 9 in 3,632 of 3,632 returns. The output is a draft with a red notice on every page; an officer must review and sign, and e-filing needs an Authorized IRS e-File Provider.

## How we built it

Each batch of twelve ledger rows becomes one Strands `GraphBuilder` graph. The Preparer and the Reviewer are both entry nodes, so Strands hands each of them only the task text and runs them in parallel; the Reviewer cannot see the Preparer's reasoning because it never receives it. The Referee node hangs off conditional edges from both entry nodes, and the condition compares the two structured outputs row by row, so the Referee runs only when the two picks differ. `set_max_node_executions(3)` caps the graph at one pass.

All three agents carry one Strands `@tool`, `line_guidance`, which returns the IRS Part I instruction text for a line number. The prompts require the agents to call it for every line they use and to copy the deciding sentence into their answer. Each agent returns pydantic structured output (`BatchCalls` for the two classifiers, `Verdicts` for the Referee), which is what makes the disagreement check and the assembly step deterministic.

Python then checks the model. Every quoted rule, the Referee's included, is compared word by word against the IRS sentence the tool returned; at least 60 percent of its words must appear there, and the line's label does not count, so a rule copied from the menu fails. A Referee verdict is accepted only if it names one of the two disputed lines. Money flowing against a line, such as a refund, is netted and flagged. Totals come from `formmath.py`, and the amounts land in the actual `f990ez.pdf` AcroForm fields with a DRAFT stamp on every page.

The trace on screen comes from a Strands `HookProvider`. It registers callbacks on `BeforeToolCallEvent` and `AfterModelCallEvent` and counts model calls and tool calls per agent, so each batch shows which nodes ran, in what order, how many times each one called the model and the tool, whether the Referee was needed, and which model id answered.

The runtime provider is Google Gemini through Strands' native `GeminiModel`. The free tier caps each model id at 20 requests a day, so the batch runner rotates through five model ids, sleeps for the delay Gemini advertises on a 429 or a 5xx, and after three attempts hands the batch to the next id. A batch no model can answer is recorded as unclassified with the error text and the run continues.

The hosted Streamlit app has a "Replay the recorded run" button that rebuilds the form from `results/demo_run.json` without any model calls, so the demo still works when the day's quota is spent. Live runs use the same code path.

## Challenges we ran into

Amazon Bedrock was the first choice of provider. A new AWS account's applied Bedrock quota is 0 tokens a day for every model and region until AWS Support seeds it, and that did not happen before the deadline. The Bedrock code was written, then removed, because a one-provider story is clearer than a failover ladder; `BedrockModel` in place of `GeminiModel` is a one-line swap when the quota arrives.

That left the Gemini free tier, measured at 20 requests a day per model id. A graph with two parallel agents and a conditional third spends several requests per batch, so a single ledger cannot finish on one id. The fix was the rotation described above plus retry logic that matches status codes rather than substrings, after an early version treated a validation error echoing a $500 row as an HTTP 500.

Grounding was the other hard part. The first check counted the line's label, and agents passed it by quoting the menu. Only the instruction sentence counts now.

## Accomplishments

The arithmetic that fills the form was run against 3,632 real filed Form 990-EZ returns (IRS e-file batch 2026_TEOS_XML_01A, 3,687 files, 3,632 with a checkable Part I). Line 9 was reconstructed in 3,632 of 3,632 (100.00 percent), line 17 in 3,617 of 3,618 (99.97 percent), line 18 in 3,619 of 3,621 (99.94 percent). The three mismatches are in two filed returns whose own totals disagree with their own components, and they are listed in `results/validation.json`.

The recorded demo run on 2026-09-08 classified 54 of 54 rows in 5 batches, with 2 disagreements, the Referee running on 1 batch, 92 tool calls and 577 seconds, all on the free tier.

The output is the real IRS PDF, filled, not a mockup.

## What we learned

Two blind agents plus a referee surface uncertainty better than one confident agent, but only if the disagreement is shown rather than resolved quietly. Structured output is what turns "the agents disagree" into a boolean a graph edge can test. A word-overlap check against the source text is cheap and catches invented rules that read well. And the model should never do arithmetic when Python can be validated against thousands of real filings.

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
