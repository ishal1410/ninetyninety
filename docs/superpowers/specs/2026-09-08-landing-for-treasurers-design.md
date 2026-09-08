# Landing page for treasurers

Date: 2026-09-08. Replaces the judge-facing copy of the v10 landing. Visual design unchanged (approved v10: dark, Geist, emerald accent, bezel frames).

## Why
Judging criteria 2 ("a complete, coherent product experience, not just a technical proof of concept"), 3 ("a credible, specific case for solving a real problem for a real audience"), and 5 ("what problem is solved, who it's for, why it matters"). The page was written for judges; the product is for volunteer treasurers of small US nonprofits (README, "Who it is for").

## Reader
The volunteer treasurer of a small US nonprofit (gross receipts under $200,000) who files Form 990-EZ once a year with a bank export and no bookkeeper. The executive director who signs also reads it.

## Decisions (grilling round 1, all recommended answers adopted)
1. CTA reads "Run it on your computer" and scrolls to the README's five commands until the Streamlit app is hosted; `STREAMLIT_URL` flips it to "Draft a return".
2. The three agents keep their names, Preparer, Reviewer, Referee, explained once in plain words. Same vocabulary as README, app, video.
3. Accuracy: one plain sentence plus the three-line table from README, plus the mismatch note.
4. One section "When the readers disagree" shows the real disputes in plain words.
5. Part I line-by-line stays; last column is "How it was decided": "Both agreed on N" or "One disagreement, settled by the Referee".
6. "What this is not": the README's five limitations verbatim.
7. Data note, one sentence: transactions are sent to Google's Gemini API to be sorted; the blank form is fetched once from irs.gov; nothing else leaves the computer.
8. Hackathon appears once, in the footer: "Built with Strands Agents for the AWS Agents for Humans hackathon."

## Page order (index.html)
1. Nav: NinetyNinety, How it works, Accuracy, Get started, CTA.
2. Hero: "Your bank export becomes a Form 990-EZ draft your board can review." Sub: "Upload the year's transactions. Every Part I line is filled, explained, and tied to the IRS instruction that put it there. Rows a human should check are flagged." CTA per decision 1. Drafted form in the bezel with three chips in treasurer words.
3. What you get: the drafted page, then Part I line by line (decision 5), expanding to the transactions and the IRS instruction each follows.
4. How it works: upload; Preparer and Reviewer each sort every transaction independently and cite the IRS instruction; the Referee settles any disagreement; you review flagged rows and download the DRAFT PDF. Python adds the totals, never the model.
5. When the readers disagree (decision 4).
6. Accuracy (decision 3).
7. What this is not (decision 6).
8. Get started: the five commands; the data note (decision 7); one line: hosted version coming.
9. Footer: MIT, GitHub, "How it is built" link to technical.html, hackathon line (decision 8).

## technical.html
Same shell and styles. Holds: the Strands graph diagram with measured wires, the per-batch trace table, models used, tool-call counts, the validation table with the mismatch note, links to README architecture diagram and repo. `build_landing.py` injects the same run JSON into both pages.

## Removed from index.html
Hackathon pill, "Strands graph per batch of twelve rows", trace table, tool calls, wall-time bars, model names, "free Gemini tier", "conditional node" labels, mono metadata.

## Constraints kept
DRAFT disclaimer on the form and in copy. No em or en dashes. Nothing the repo cannot back. No testimonials. Dark theme lock, reduced motion, mobile single column, no horizontal overflow.
