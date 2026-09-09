# App hero: the transformation strip

Date: 2026-09-09
Surface: `app.py` presentation only. Nothing in `src/ninetyninety/` changes.
Amends: `2026-09-09-federal-register-interface-design.md`, which stands. That
spec set the direction (a federal document, not a marketing scroll). This one
replaces the hero inside that direction.

## Problem

The app's first screen is a scanned JPEG of a whole Form 990-EZ page
(`assets/draft-page1.jpg`) at roughly 578×750px, beside a column of paragraphs.

The stated complaint is that the form image covers too much space and the page
looks plain. Shrinking the image does not fix that and makes it worse: the
image is the only element on the page carrying any mass. The real fault is
visual weight, measured on the live app:

- Body copy is `--muted` (#565C65) at 0.79–0.95rem nearly everywhere.
- The type scale jumps from 0.98rem straight to the 2.1–3.5rem `h1`.
- Every division on the page is the same 1px hairline.
- The pitch sits *below* the upload controls, so the page argues for itself
  after it has already asked for a file.

## Decisions

1. The one loud element is a **transformation strip**: one real recorded ledger
   row becoming the form line it lands on, with the IRS sentence that put it
   there. The scanned JPEG leaves the app.
2. The strip is **static, one row**. No carousel, no timer. A rotating hero
   would steal the single loud element and is the generic default.
3. Below it: controls, then a quiet three-column explainer band built from the
   existing `STEPS` copy.
4. Weight is added **without a new hue**. Same palette, same typefaces. Public
   Sans is the USWDS federal face; that is the argument of the whole design.

## The content is real

`results/demo_run.json`, written by `scripts/dump_run.py` from a real Gemini
run, carries every classified row as `source_row`, `date` (`YYYY-MM-DD`),
`description`, `amount`, the model's quoted `rule`, and its `why`. The strip
renders one of those rows verbatim. Nothing on the hero is invented.

## Page structure

Everything below is emitted inside the existing `with body:` block, so the
masthead band, the zone rules and the content column share one width.

```
██ NinetyNinety   Form 990-EZ   Return of Org…      OMB No. 1545-0047 ██
                                                          solid ink band

A bank export goes in. This comes back.                    h1, unchanged
Every figure on the drafted form cites the transactions…   p.hero-lede

┌──────────────────────┐        ┌────────────────────────────┐
│ 2025-01-08           │        │ Line 1                     │
│ ONLINE DONATION      │───────▶│ Contributions, gifts,      │
│ STRIPE PAYOUT        │        │ grants, and similar        │
│ BATCH 4471           │        │ amounts received           │
│                1,250 │        │ ─────────────────────────  │
└──────────────────────┘        │ this row            1,250  │
  one row of a bank export      │ ─────────────────────────  │
                                │ "Voluntary transfers where │
                                │  the donor receives…"      │
                                └────────────────────────────┘
                                  the line, and the instruction
                                  that put it there

Line 9 rebuilt exactly in 3,632 of 3,632 returns checked from the IRS
e-file corpus. Line 17: 3,617 of 3,618. Line 18: 3,619 of 3,621.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  3px ink rule

Draft a return
Upload a CSV…                                              p.lede, as today
[Upload CSV]  ☑ demo ledger        Org name        EIN
[ Draft a return ]      [ Replay the recorded run ]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌─ when a draft exists: the result view, unchanged ─┐
  └─ otherwise: the explainer band ───────────────────┘

Two agents read every  │ A referee settles only │ Python adds up,
row, blind to each     │ the rows they read     │ never the model
other                  │ differently
```

The hero stays on screen after a run. It is roughly 250px; removing it once
results appear would leave the result view as flat as the page this spec fixes.

## The fold budget

The parent spec argues the app must open on the product, not a brochure,
because a judge may score from a single screenshot. A hero above the controls
works against that, so it is constrained rather than left to grow:

| Region | Budget |
|---|---|
| Masthead band | ~70px |
| Hero strip, `h1` through the proof line | ≤ 260px |
| Zone rule + section heading + lede | ~90px |
| **Controls fully visible by** | **≤ 620px** |

At a 900px viewport the whole control strip, both buttons included, stays above
the fold. The number is checked by browser measurement during implementation;
CI guards only the ordering (see Tests).

The strip is the product, not a brochure: a real row, a real line, a real
quoted instruction. It is not the marquee/bento/sticky-card scroll the parent
spec rejected, and the ban on those stays in force.

## Five corrections to the first draft of this design

Recorded because each would have shipped a visible defect.

**1. The hero must not print a line total.** The draft drew `Line 1   1,250`.
Line 1's real total in the recorded run is **9,100** across six transactions;
1,250 is only the Stripe row's own amount. Rendered that way the front page of
a tax tool states a wrong figure — the exact failure the product argues it
prevents. The destination card is labelled `this row   1,250`, and no line
total appears on the hero at all.

**2. The proof line names line 9.** The draft compressed it to "3,632 of 3,632
returns rebuilt exactly", which claims whole returns matched.
`results/validation.json` says: batch of 3,687 returns; **line 9** matched
3,632 of 3,632 checked; line 17 3,617 of 3,618; line 18 3,619 of 3,621. The
copy keeps both "line 9" and "checked".

**3. Two functions at two call sites.** `empty_state()` is deleted and replaced
by `hero()` (the strip, emitted directly after the masthead and above the
controls) and `explainer()` (the three-column band, emitted at the current
`empty_state()` call site, still only when no draft exists).

**4. `p.lede` is not retokenized.** It has four call sites — `app.py:293`
(hero), `:388` (controls copy), `:492` ("Read N transactions"), `:601`
(adjudication intro). Enlarging it to 1.3rem would enlarge all four and undo
the control-strip height that commit `6745fb5` was written to fix. The hero
lede gets its own class, `p.hero-lede`.

**5. The masthead moves inside `body`.** It is emitted at `app.py:315`,
*outside* the `[1, 12, 1]` pad columns, so it spans ~1256px while everything
below spans ~1066px (measured live). As a hairline that is invisible; filled
solid ink it becomes a bar overhanging the content by ~95px each side. Moving
the `st.markdown(masthead(), …)` call inside `with body:` is a smaller fix than
re-plumbing the column widths.

## Changes to `app.py`

| Change | Detail |
|---|---|
| New `hero()` | Renders the strip from one row of `results/demo_run.json`, loaded once at module level beside `report` and guarded with `if path.exists()` — the idiom `report` already uses at `:248-251`. If the file is absent the strip is omitted and the page still boots. |
| New `explainer()` | The existing `STEPS` tuple as a three-column band. Copy unchanged. |
| Deleted | `empty_state()`; the `.intro`, `.sheet` and `.cert` rules; the `asset()` helper and `import base64` — each had exactly one user. `.steps`/`.step` survive, restyled from a stacked list into the three-column band. |
| Moved | `st.markdown(masthead(), …)` from `:315` into `with body:`. |
| CSS | `.mast` becomes a solid ink band with reversed type. New `p.hero-lede` at 1.3rem in `--ink`. New `.lands` block for the strip. New `.zone` 3px ink rule between regions. Primary copy moves from `--muted` to `--ink`; `--muted` is kept for captions, rules and the form's own small print. Hairlines survive **only inside** the form sheet, where they are the form's own device. |
| Untouched | Every result view — form sheet, provenance expanders, graph, adjudication record. They inherit the tokens. `assets/draft-page1.jpg` stays on disk; `index.html:22` and `:271` still use it. |

The strip's wrapper class is `.lands`, not `.hero`. `tests/test_app.py:153`
bans `class="hero"` deliberately, to stop the app drifting back into the
marketing page that was rejected twice. That guard stays intact.

## Tests

Two existing tests are rewritten, because the thing they pin is being removed.

- `test_the_app_opens_on_the_product_not_a_marketing_scroll` (`:153`) — keeps
  banning `hero`, `marq`, `bento`, `card`, `act` and `position:sticky`. Its
  masthead assertion currently reads the fixed index `at.markdown[1]`; the
  masthead moves, so it matches on content across the rendered markdown.
- `test_the_empty_state_shows_the_real_drafted_form_and_then_makes_way`
  (`:189`) becomes
  `test_the_strip_shows_a_real_recorded_row_and_the_band_makes_way`: the strip
  carries a description and a rule that appear verbatim in
  `results/demo_run.json`, and the explainer band is gone once a draft exists.

Five added:

- The destination card labels the row's own amount and does not print the line
  total. Guards correction 1.
- The proof line contains "line 9" and does not contain "returns rebuilt
  exactly". Guards correction 2.
- `p.lede` keeps its current font size and the hero uses `p.hero-lede`. Guards
  correction 4.
- The page renders with `results/demo_run.json` absent: strip omitted, no
  traceback.
- Ordering guard for the fold budget: the two buttons render before the
  explainer band's copy. `AppTest` is headless and has no layout engine, and
  the repo's only Playwright tests (`tests/test_landing_pages.py`) load static
  `file://` pages rather than a running Streamlit server, so the 620px figure
  itself is verified by browser measurement during implementation, not in CI.

## Out of scope

- The two audit notes not accepted: two columns reading as "winner" in the
  adjudication record, and the all-caps label stack.
- `index.html` and `technical.html`.
- Any change to classification, grounding, arithmetic or the PDF.
