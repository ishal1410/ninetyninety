# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Existing: Python + Streamlit (`app.py`) for the tool. Landing surface: static `index.html` (any CSS/JS), hosted on GitHub Pages, linking to the Streamlit app. Decided by the user 2026-09-08.

## Users
Primary for the landing surface: volunteer treasurers of small US nonprofits (gross receipts under $200k) with a bank CSV export and no bookkeeper, and the officer who signs the return. Judges of the AWS "Agents for Humans" hackathon read the same page and score it on criteria 2, 3 and 5; the engineering material they need for criteria 1 and 4 lives on `technical.html`, the README and the architecture diagram.

## Product Purpose
Turn a raw bank-transaction CSV into a drafted IRS Form 990-EZ where every Part I line cites the transactions behind it and the IRS rule that put them there. Success for judges: the Strands graph and the real filled IRS PDF are both visible and believable within one viewport, then runnable live.

## Positioning
Two blind Strands agents (Preparer, Reviewer) classify each row in parallel; a Referee node runs only on disagreement; Python, never the model, does the arithmetic and word-checks every quoted rule against the IRS instruction text. Nothing is resolved silently. Existing filing tools start after the books are categorised; this does the categorising.

## Operating Context
Judges open the Devpost entry, the repo README, the demo video, and the live URL. Treasurers upload `date, description, amount` CSV, wait several minutes (Gemini free tier, batches of 12), read the draft, download the PDF.

## Capabilities and Constraints
- Strands `GraphBuilder` graph per batch: Preparer + Reviewer entry nodes, conditional Referee edge, real `@tool line_guidance`, pydantic structured output.
- Per-batch trace on screen: nodes run, per-node ms, tool calls, whether Referee ran.
- Real `f990ez.pdf` AcroForm filled; "DRAFT, NOT A FILING" on every page. An officer must review and sign; e-filing requires an Authorized IRS e-File Provider. This disclaimer must stay on the tool surface.
- Model: Google Gemini free tier only (zero budget). Runs take minutes.
- Streamlit strips `<script>`; the tool page is CSS-only.
- No em or en dashes in copy (project rule).
- Licence MIT. "New projects only" rule: no reuse of prior project code.

## Brand Commitments
Name: NinetyNinety. No logo. No fixed palette or type (v1-v6 all rejected; none is binding). Voice: plain, factual, no hype.

## Evidence on Hand
- Validation against 3,687 real filed 990-EZ returns: line 9 3,632/3,632 (100.00%), line 17 3,617/3,618 (99.97%), line 18 3,619/3,621 (99.94%). `results/validation.json`.
- Live run 2026-09-07: 54/54 rows, 4 disagreements, Referee ran on 2 batches, 93 tool calls.
- Real filled DRAFT PDF renders: `assets/draft-page1.jpg`, `assets/draft-partI.jpg`, `assets/draft-totals.jpg`.
- Architecture diagram `docs/architecture.png`. Demo ledger `fixtures/demo_ledger.csv`.
- No testimonials, no customers, no press. Do not fabricate any.

## Product Principles
1. Prove, never claim: show the form being drafted and the graph that drafted it.
2. Disagreement is the feature: surface Preparer vs Reviewer vs Referee, never hide it.
3. Python does the maths; the model only classifies.
4. Nothing on the page the repo cannot back with a file.
5. The visitor must be able to run it themselves in one click.

## Accessibility & Inclusion
Judges may review on laptops at 1280-1600 wide and on phones. Keyboard-reachable CTA, real text (no text in images) for the proof numbers.
