# NinetyNinety demo video: script and shot list

Target length 4:30. Spoken words are in blockquotes and are read verbatim. Everything on screen is a file in this repo or the hosted app. Record with OBS or Windows Game Bar, upload to YouTube as public, paste the link into the Devpost entry.

Depends on: Task 1 (per node model calls in the trace) and Task 2 (the "Replay the recorded run (no model calls)" button). If either is missing when you record, skip the sentence marked with that task.

## Pre-recording checklist

1. Display 1920x1080, browser zoom 125%, one browser window, no other tabs.
2. Hide the bookmarks bar (Ctrl+Shift+B) and close the sidebar; use a clean profile with no extensions.
3. Streamlit: three dot menu, Settings, theme Light; the "Deploy" button and menu stay out of frame.
4. Run the replay path once before recording so the page and the IRS PDF download are warm; do not start a live run unless at least 20 requests per Gemini model id remain that day (the free cap is per model id, see README).
5. Open these tabs in order: https://ninetyninety.streamlit.app, https://ishal1410.github.io/ninetyninety/, https://ishal1410.github.io/ninetyninety/technical.html, https://github.com/ishal1410/ninetyninety, and `docs/architecture.png` in an image viewer at 100%.
6. Have `fixtures/demo_ledger.csv` visible in a File Explorer window at the right of the screen for the drag in shot 3.
7. Open `990-EZ-DRAFT.pdf` (downloaded during the warm up) in a PDF viewer, page 1, zoomed so Part I fills the height.
8. Microphone test: 10 seconds, play back, no fan or keyboard noise; system sounds off, notifications off (Focus assist on).
9. Recording: 1920x1080, 30 fps, system audio off, microphone on; cursor visible, no click highlight.
10. Read the script aloud once with a timer; if it runs past 4:30, cut from shots 4 and 8 first, never from shots 1, 2 and 9.

## Shot list

### Shot 1, 0:00 to 0:35, the problem

On screen: https://ishal1410.github.io/ninetyninety/ hero. Headline "Your bank export becomes a Form 990-EZ draft your board can review." Do not scroll yet.

> Small US nonprofits file Form 990-EZ every year, and most of them have no finance staff. Miss the filing three years in a row and the IRS revokes your tax exempt status automatically. That revocation list holds over a million entries. Filing tools start after the books are categorised. Categorising the books is the actual work, and it is the part nobody helps with.

### Shot 2, 0:35 to 0:50, who it is for

On screen: scroll to "How it works." Step 1, "Upload the year's transactions", is visible.

> NinetyNinety is for volunteer treasurers: the little league, the food pantry, the community band. People with a bank export and no bookkeeper. One CSV in, a drafted return out, every line explained.

### Shot 3, 0:50 to 1:20, upload the CSV in the hosted app

On screen: switch to https://ninetyninety.streamlit.app. The uploader "Transaction ledger as CSV with date, description, amount". Drag `fixtures/demo_ledger.csv` from File Explorer onto it. Untick "Use the synthetic demo ledger instead". Leave "Organisation name for the PDF" and "EIN for the PDF" as they are. Click the primary button "Draft a return".

> This is the hosted app. I upload a year of bank transactions: date, description, amount. Fifty four rows, no categories. The organisation name and EIN go onto the PDF. Draft a return.

### Shot 4, 1:20 to 2:20, the Strands graph running

On screen: the progress bar "Preparer and Reviewer are reading the ledger in parallel" and the grey skeleton form, for about eight seconds. Then a hard cut to the finished page (recorded via the "Replay the recorded run (no model calls)" button, Task 2). Scroll the right column to "The graph that ran" and open the expander "Full Strands trace, 5 graph runs". Point the cursor at batch 5, where the nodes column reads "preparer, reviewer, referee" and the provider column reads "gemini:gemini-3.5-flash-lite".

> Each batch of twelve rows goes through one Strands Agents graph. The Preparer and the Reviewer are two entry nodes of a GraphBuilder graph and run in parallel. Strands hands each of them only the rows, so the Reviewer never sees the Preparer's reasoning. Both call a real Strands tool, line guidance, which returns the IRS instruction text for a Part I line, and both answer with structured output. A live run takes several minutes on the free tier, so I cut to the finished trace. Five graph runs, ninety two tool calls, and per node model calls counted by a Strands hook provider. Batch five is the one where the Referee node ran, and the provider column shows the free tier rotating across Gemini model ids.

The clause "and per node model calls counted by a Strands hook provider" needs Task 1. Without it, say "ninety two tool calls" and stop.

### Shot 5, 2:20 to 3:00, one disagreement expanded

On screen: scroll up the right column to "Agent disagreements, 2". Hold on the first card, "row 51 ACME HARDWARE GALA TABLE SPONSOR". Move the cursor down the four lines as they are named: Preparer line 6d, Reviewer line 1, Referee line 6d, On the form: line 6d.

> Row fifty one, a gala table sponsorship. The Preparer put it on line 6d, fundraising events, and quoted the IRS instruction. The Reviewer, working blind, put it on line 1, contributions, and quoted a different one. The Referee ran, looked up both lines with the tool, chose 6d, and its reason is right there. Python then checked that reason against the IRS sentence the tool returned. Nothing is resolved silently.

### Shot 6, 3:00 to 3:30, the filled DRAFT PDF

On screen: left column, click "Download the PDF, marked DRAFT". Switch to the PDF viewer, page 1 of `990-EZ-DRAFT.pdf`, Part I with the red "DRAFT, NOT A FILING" notice. Cursor on line 9, then 17, then 18. Switch back to the app and open the expander "Line 1, Contributions, gifts, grants, and similar amounts received: $9,100 from 6 rows".

> The amounts land in the fields of the real IRS form. Line 9, total revenue, forty thousand three hundred sixty nine. Line 17, expenses. Line 18, the excess. All three are computed in Python. The model never adds. Every page carries the DRAFT notice and the Paid Preparer block stays blank, because an officer must review and sign. Open any line and each transaction sits beside the rule that put it there.

### Shot 7, 3:30 to 3:55, validation against real returns

On screen: https://ishal1410.github.io/ninetyninety/technical.html, section "Footing checked against filed returns." The table with Line, Checked, Matched, Rate. Cursor on the line 9 row, then on the command `PYTHONPATH=src python scripts/validate.py`.

> Does the arithmetic hold up? The same formmath module that fills the form was run over three thousand six hundred thirty two real 990-EZ returns from the IRS e-file corpus. Line 9 rebuilt on every one. Line 17, 99.97 percent. Line 18, 99.94. The three misses are two filed returns whose own totals disagree with their own line items, listed in results slash validation dot json. One command reproduces it.

### Shot 8, 3:55 to 4:15, architecture

On screen: `docs/architecture.png` full screen. Cursor follows the words as they are spoken.

> The architecture. A Strands Agents GraphBuilder graph with two blind entry nodes, a conditional edge to the Referee, and the line guidance tool. Under it, a Python layer that sums, checks every quoted rule, and fills the PDF. The model is Google Gemini through the Strands GeminiModel; Amazon Bedrock is a one line swap.

### Shot 9, 4:15 to 4:30, close

On screen: https://github.com/ishal1410/ninetyninety, README top, the bold first line visible.

> NinetyNinety, at github dot com slash ishal1410 slash ninetyninety. Built with Strands Agents for the AWS Agents for Humans hackathon, Good Neighbor Agents track. A shoebox of bank transactions becomes a drafted 990-EZ, with every line citing the transactions behind it and the rule that put them there.

## Sources for every number said aloud

- Over a million revocations, three missed filings: README, "The problem".
- 54 rows, 5 graph runs, 92 tool calls, Referee on batch 5, providers gemini-3.5-flash, gemini-3.6-flash, gemini-3.5-flash-lite: `results/demo_run.json` (`meta.rows`, `trace`).
- Row 51, Preparer 6d, Reviewer 1, Referee 6d: `results/demo_run.json` (`disagreements[0]`).
- Line 9 = 40,369, line 17 = 34,946, line 18 = 5,423, line 1 = 9,100 from 6 rows: `results/demo_run.json` (`totals`, `lines`).
- 3,632 returns, 3,632 / 3,632, 99.97, 99.94, three mismatches in two returns: `results/validation.json`.
