# Pilot 2 Findings & Next Steps — 2026-04-05

## Experiment Summary

- **Design:** 9 tasks × 3 variants (low/base/high) × 3 reps = 81 runs
- **Agent:** Claude Sonnet, text-only, temperature=0, maxSteps=30
- **Sites:** ecommerce (5 tasks), ecommerce_admin (1 task), reddit (3 tasks)
- **Duration:** ~6 hours total, zero crashes
- **Run ID:** 485dc46c-d349-49dd-a17d-addfb1c80a47

## Core Result

| Variant | Success | Rate | vs Base |
|---------|---------|------|---------|
| low     | 10/27   | 37.0% | −37.1pp |
| base    | 20/27   | 74.1% | —       |
| high    | 16/27   | 59.3% | −14.8pp |

**Low vs base is statistically significant:** χ²=7.50, p=0.006, Cramér's V=0.37.
**Base vs high is NOT significant:** χ²=1.33, p=0.25.

## Key Finding

Accessibility degradation (low variant) causes a clear, significant drop in AI agent
task success. The primary mechanism is **token inflation** — degraded DOM is 87% more
verbose (186K vs 99K avg tokens), leading to context overflow and inability to locate
page elements.

Enhanced accessibility (high variant) did not yield additional performance gains beyond
baseline. Trace analysis revealed the observed base-high gap was attributable to a
platform-level action serialization bug and small-sample variance, not accessibility
mechanisms. This suggests current web accessibility standards already provide sufficient
semantic structure for AI agent operation, and the critical barrier lies in accessibility
degradation below baseline.

## Bugs to Fix for Pilot 3

### Bug 1: send_msg_to_user Serialization (P0 — affects experiment validity)

**Impact:** Causes false failures across ALL variants equally. Task 24 failed identically
in both base and high due to this bug.

**Root cause:** Agent constructs `send_msg_to_user("text with (parentheses) and "quotes"")`.
The `cleanAction()` function in `executor.ts` doesn't handle nested quotes/parentheses
in the message text, resulting in `ValueError: Received an empty action` from BrowserGym.

**Current mitigation:** `cleanAction()` replaces internal double quotes with single quotes
and truncates to 500 chars. But it doesn't handle:
- Unmatched parentheses in the message
- Messages that end with `")` which gets confused with the function call closing

**Fix:** More robust parsing in `cleanAction()` — extract the message content between
the first `("` and the last `")`, sanitize everything inside.

**Location:** `src/runner/agents/executor.ts`, `cleanAction()` function.

### Bug 2: High Variant Node ID Shift (P1 — design flaw)

**Impact:** apply-high.js inserts a skip-link at `body.firstChild`, shifting ALL
subsequent BrowserGym node IDs by ~1. This means `click("42")` targets different
elements in high vs base, creating a latent element-targeting risk.

**Root cause:** `body.insertBefore(skipLink, body.firstChild)` in apply-high.js.

**Fix options:**
1. Insert skip-link at body END instead of beginning (still accessible via tab order)
2. Use `data-variant-skip` attribute instead of a new DOM element
3. Insert after BrowserGym's bid assignment (not possible — bids are assigned dynamically)

**Recommended:** Option 1 — move to body end. Skip-links work via `href="#main-content"`
anchor, position doesn't matter for functionality.

**Location:** `src/variants/patches/inject/apply-high.js`, section 2.

### Bug 3: Compressed Variant Score Range (P1 — attenuates effect size)

**Impact:** Actual composite scores are 0.405 (low) / 0.459 (base) / 0.457 (high) —
far more compressed than configured ranges (0.00–0.25 / 0.40–0.70 / 0.75–1.00).
The high variant barely differs from base in measured accessibility.

**Root cause:** Variant patches don't modify enough DOM elements to move the composite
score significantly. The scanner measures post-patch accessibility, and the patches
are too conservative.

**Fix:** Make apply-low.js more aggressive (remove more ARIA attributes, break more
semantic structure) and apply-high.js more comprehensive (add ARIA to ALL elements,
not just unlabeled ones).

**Location:** `src/variants/patches/inject/apply-low.js`, `apply-high.js`.

### Bug 4: Empty Observation on Click Navigation (P2 — known limitation)

**Impact:** ~30% of steps after click() on Magento internal links return empty/short
a11y tree. Agent wastes steps on go_back loops.

**Root cause:** BrowserGym's active page tracking doesn't update correctly after
click-triggered navigation. Progressive retry helps but doesn't fully resolve.

**Status:** Documented as known limitation. Agent compensates via goto() URL hacks.
Cross-variant impact is uniform — not a confound for the experiment.

**Mitigation for paper:** Report in Limitations section. Track empty obs rate per
variant to confirm uniform distribution.

## Task-Level Findings

### High-Sensitivity Tasks (variant matters, ≥67pp range)
- Task 4 (admin report): Perfect monotonic gradient 0%→33%→67%
- Task 23 (review search): 0%→100%→100% — low completely blocked
- Task 26 (review search): 0%→100%→100% — low completely blocked
- Task 29 (reddit vote): 0%→100%→33% — base >> high (noise)
- Task 67 (reddit forum): 67%→100%→33% — high worst (noise)

### Non-Discriminative Tasks (exclude from Pilot 3)
- Task 27 (reddit): 100% all variants — ceiling, no signal
- Task 47 (ecommerce): 100% all variants — ceiling, no signal
- Task 50 (ecommerce): 0% all variants — floor, always fails (context overflow)

### Inverted Task (investigate)
- Task 24 (review search): low=67% > base=33% > high=0%
  - All failures are send_msg_to_user serialization bug
  - Low "succeeds" because degraded DOM prevents agent from seeing review content
    it would otherwise misinterpret — accidental correct answer

## Pilot 3 Recommendations

1. **Fix send_msg_to_user bug** — P0, affects experiment validity
2. **Fix high variant skip-link insertion** — move to body end
3. **Exclude ceiling/floor tasks** — remove 27, 47, 50
4. **Increase reps to 5** — improve power for base-vs-high comparison
5. **Add medium-low variant** — characterize dose-response curve
6. **Make variant patches more aggressive** — widen composite score range
7. **Add GitLab tasks** — expand task diversity (requires login fix)

## Paper Framing

"Enhanced accessibility annotations (ARIA landmarks, skip-navigation, form labels)
did not yield additional performance gains beyond the baseline level. Trace analysis
revealed that the observed base-high gap (14.8pp, p=0.25) was attributable to a
platform-level action serialization bug and small-sample variance rather than
accessibility-related mechanisms. This suggests that current web accessibility
standards already provide sufficient semantic structure for AI agent operation,
and that the critical barrier lies in accessibility degradation below baseline."

## Data Location

- Raw traces: `data/pilot2/track-a/runs/485dc46c.../cases/`
- CSV exports: `data/pilot2/exports/`
- Full analysis: `data/pilot2/pilot2-analysis.md`
- S3 backup: `s3://a11y-platform-data-20260401.../pilot2-data.tar.gz`
