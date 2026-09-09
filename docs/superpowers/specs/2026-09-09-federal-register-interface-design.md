# NinetyNinety interface: the Federal Register direction

Date: 2026-09-09
Surface: `app.py`, the hosted Streamlit application at https://ninetyninety.streamlit.app
Not in scope: `index.html` and `technical.html` on GitHub Pages, which were approved separately.

## Why the current interface is wrong

The app opens on a marketing scroll: hero, marquee, proof bento, sticky agent
cards, closing call to action, and only then the product. That structure is the
default shape of an AI generated landing page, and it is the reason the page
reads as generated rather than designed.

It is also wrong for the judging. The rules say a judge may score on the text
description, the images and the video alone, so the app has to photograph well
in a single frame. A four section scroll does not. Criterion 2 asks for "a
complete, coherent product experience, not just a technical proof of concept",
which rewards the product being present, not a brochure in front of it. And the
marketing job is already done by the GitHub Pages landing, so the app was
duplicating a surface that exists.

## The design read

Product UI for two readers at once: a volunteer treasurer of a small nonprofit,
and a panel of AWS judges. The subject is a United States federal tax return.
The language is a federal filing, executed with obsessive craft.

Three design skills were consulted and they disagreed. `design-taste-frontend`
states that public sector and trust first constraints override aesthetic
preference, and its own system map sends this brief to USWDS.
`ui-ux-pro-max` independently returned the "Accessible and Ethical" profile,
whose stated best fit is government, with an explicit instruction to avoid
ornament, low contrast and AI gradients. `high-end-visual-design` argues for
OLED black, large radii, pill buttons and eyebrow tags; it is a landing page
agency skill and is the outlier here. Its craft rules are kept, which are custom
easing curves, nested enclosures, no generic gray borders and no harsh shadows.
Its aesthetic prescriptions are rejected.

Dials: variance 5, motion 3, density 8. Dense because this is a form, quiet
because it is a tax document, balanced because it is a product and not an
experiment.

## Foundations

Typeface: **Public Sans**, the typeface the United States Web Design System
commissioned for federal government use, variable 100 to 900 on Google Fonts.
This is the point of the whole design. The tool that drafts a federal form is
set in the federal typeface. Figures are IBM Plex Mono with tabular numerals, so
every column of money aligns.

Palette, every pair measured rather than assumed:

| Token | Value | Contrast |
|---|---|---|
| paper | `#FFFFFF` | ground for the form |
| ground | `#F4F5F6` | page behind the form |
| ink | `#1B1B1B` | 17.2:1 on paper |
| muted | `#565C65` | 6.7:1 on paper |
| accent, the only one | `#005EA2` | 6.7:1 on paper, 6.7:1 white on it |
| notice, semantic only | `#B50909` | 7.0:1 on paper |
| rule, decorative hairline | `#DFE1E2` | not text |
| control border | `#8D9297` | 3.1:1, meets the interactive minimum |

Radius is 0 throughout, 2px on controls. A federal form has corners. This is the
shape consistency lock, and it is also what separates the page from every
rounded card on Devpost.

Motion is 200ms on `cubic-bezier(.2,0,0,1)`, used for control feedback and the
loading skeleton only. No scroll driven theatre. Reduced motion collapses it.

## Structure

One screen, no marketing scroll.

1. **Masthead.** The page chrome is the form's own header: the wordmark, then
   "Form 990-EZ", "Return of Organization Exempt From Income Tax", and
   "OMB No. 1545-0047" set in the hierarchy the real form uses. Sticky, 64px, a
   hairline underneath. It tells the visitor what this is in one glance and it
   is the first thing in any screenshot.

2. **Control bar.** One row: ledger upload, demo toggle, organisation, EIN, and
   the two buttons. Labels sit above their inputs, never inside them.

3. **Empty state.** Before anything is run the page shows the real drafted form
   page with annotation callouts pointing at three real lines, explaining what
   the reader is about to get. It is composed rather than blank, and it is the
   frame that goes in the Devpost gallery.

4. **The draft, two panes.**
   - Left: Part I set as the actual form. A boxed line number, the IRS label, a
     dotted leader, the amount right aligned in tabular figures, section bands
     for Revenue and Expenses, and the accountant's double rule under each
     total. A red DRAFT notice.
   - Right: the decision record. Adjudications first, then the graph that ran,
     then the trace.

5. **Adjudication record.** The differentiator, and currently buried in a
   sidebar note. Each disagreement becomes a three column record: Preparer,
   Reviewer, Referee, each with the line it chose and the IRS sentence it
   quoted, and the column that won carries an "ON THE FORM" stamp. This is the
   only part of the product no other entry will have, so it gets the treatment.

6. **Footer.** Thin, last, after the results.

## What is deliberately not here

No hero. No marquee. No bento. No sticky cards. No eyebrow labels. No scroll
cues. No decorative dots. No em dashes. No gradient. No glass. No icon library,
because the page needs no icons.

## Testing

The behavioural tests in `tests/test_app.py` must keep passing untouched:
HTML escaping of agent output, the worker thread, the row cap and the run lock,
the footer coming after the tool, the empty ledger error, temp directory
cleanup. The CSS assertions in that file are rewritten against the new tokens.
Layout is verified in Chromium against the deployed app at 1920, 1440, 1024 and
390 pixels, as the previous round was.
