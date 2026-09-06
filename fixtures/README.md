# Fixtures

`demo_ledger.csv` is a **synthetic, illustrative** transaction ledger for a
made-up community organisation. The descriptions are deliberately raw
bank-statement text with no category column: abbreviations, vendor codes,
ALL CAPS, refunds, and a few rows that could reasonably land on more than one
Form 990-EZ line. Sorting that mess out is the agents' job.

Nothing in this file is a real organisation, person, bank, or transaction.

**The accuracy numbers published by this project do not come from this file.**
They come from re-computing thousands of real, publicly filed Form 990-EZ
returns in the IRS e-file XML corpus (`scripts/validate.py`,
`results/validation.json`).
