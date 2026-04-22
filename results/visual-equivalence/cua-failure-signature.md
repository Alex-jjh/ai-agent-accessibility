# CUA Failure Trace Validation — link→span signature

Scanned 522 CUA traces.

- Low variant: 130 (54 failures, 76 successes)
- Base variant: 130 (8 failures)

## Signature definition

A trace shows the link→span signature (strict) when:
- variant = low
- outcome != success (timeout or explicit failure)
- >= 8 successful left_click actions in the trace
- >= 90% of those clicks produced NO url change (inert)
- agent clicked the same 30x30 px region >= 3 times (loop)

This matches the predicted cross-layer failure: CUA clicks on blue-underlined
pixels (which LOOK like links because patch 11 preserves inline style + cursor
on <span>), but the DOM a[href]->span substitution means the click does nothing,
the URL never updates, and the agent loops on the same coordinates.

Why the strict threshold: many intra-app interactions (dropdowns, filters, form
fills) legitimately don't change URL. A loose `inert_clicks >= 2` test fires
on successful base-variant runs too. Requiring >= 90% inert + loop + outcome=fail
isolates the specific failure mode where every click on a former link is silent.

## Signature prevalence

| Subset | Total | With signature | Fraction |
|--------|-------|----------------|----------|
| Low failures | 54 | 42 | 77.8% |
| Low successes (≥2 inert clicks) | 76 | 66 | 86.8% |
| Base failures (≥2 inert clicks) | 8 | 8 | 100.0% |

## Inert click fraction by variant & outcome

| Variant | Outcome | N | Mean inert fraction | Mean inert clicks |
|---------|---------|---|--------------------|-------------------|
| base | success | 122 | 100.00% | 3.95 |
| base | timeout | 8 | 97.55% | 16.00 |
| high | success | 126 | 100.00% | 4.27 |
| high | timeout | 6 | 98.40% | 20.00 |
| low | failure | 2 | 100.00% | 12.00 |
| low | success | 76 | 89.47% | 4.00 |
| low | timeout | 52 | 97.94% | 11.38 |
| medium-low | success | 128 | 100.00% | 4.44 |
| medium-low | timeout | 2 | 100.00% | 7.00 |

## Low-variant failure breakdown by task

| Task | Low failures | Link→span sig | Signature rate | Total inert / total clicks |
|------|--------------|---------------|----------------|----------------------------|
| 24 | 2 | 2 | 100.0% | 18 / 20 |
| 26 | 2 | 0 | 0.0% | 12 / 12 |
| 29 | 10 | 8 | 80.0% | 128 / 132 |
| 67 | 6 | 4 | 66.7% | 66 / 68 |
| 94 | 8 | 8 | 100.0% | 102 / 106 |
| 198 | 10 | 10 | 100.0% | 108 / 108 |
| 293 | 6 | 6 | 100.0% | 74 / 74 |
| 308 | 10 | 4 | 40.0% | 108 / 110 |

## Representative signature cases (first 5)

- **ecommerce:admin:low:198:0:1:trace-attempt-1** (task 198): 13/13 clicks inert, 30 total steps
- **ecommerce:admin:low:198:0:2:trace-attempt-2** (task 198): 9/9 clicks inert, 30 total steps
- **ecommerce:admin:low:198:0:3:trace-attempt-3** (task 198): 10/10 clicks inert, 30 total steps
- **ecommerce:admin:low:198:0:4:trace-attempt-4** (task 198): 11/11 clicks inert, 30 total steps
- **ecommerce:admin:low:198:0:5:trace-attempt-5** (task 198): 11/11 clicks inert, 30 total steps

---
CSV: `results\visual-equivalence\cua-failure-signature.csv`
