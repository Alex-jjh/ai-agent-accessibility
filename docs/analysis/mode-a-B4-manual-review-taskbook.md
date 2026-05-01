# B.4 Manual Review Task Book — F_UNK Cases

**Date**: 2026-05-01
**Total failures**: 1,670 / 4,056 cases
**Auto-classified**: 1,336 (80.0%)
**F_UNK (needs manual review)**: 334 (20.0%)
**Estimated review time**: ~4-6 hours (many are batch-classifiable)

---

## Auto-Classification Summary

| Category | Count | Avg Conf | Description |
|----------|-------|----------|-------------|
| F_ARC | 525 | 0.92 | Architecture limitation (SoM phantom bids, CUA no URL bar) |
| F_FMT | 230 | 0.80 | Answer format mismatch (correct content, wrong format) |
| F_MOD | 226 | 0.71 | Model capability (can't do the task regardless of operator) |
| F_COF | 160 | 0.90 | Context overflow (token limit / LLM call failure) |
| F_PCT | 93 | 0.84 | Partial correct (found some but not all info) |
| F_NAV | 73 | 0.82 | Navigation failure (can't reach target page) |
| F_AMB | 24 | 0.90 | Ambiguous/stochastic (task 29 baseline noise) |
| F_SIF | 5 | 0.85 | Structural infeasibility (task impossible under operator) |
| **F_UNK** | **334** | **0.50** | **Needs manual review** |

---

## F_UNK Breakdown by Batch

### Batch 1: CUA × task 41 — 37 cases (BULK: F_MOD or F_FMT)

CUA answers wrong product names for task 41 (top search term). CUA navigates
the storefront and reports products it sees, not the search term from admin.
**Suggested classification**: F_ARC (CUA can't access admin search terms page).
**Review action**: Spot-check 3 answers. If all are product names → bulk F_ARC.

### Batch 2: CUA × task 67 — 38 cases (BULK: F_PCT)

CUA answers book lists but misses some books or includes wrong ones.
**Suggested classification**: F_PCT (partial correct — found some books, not all).
**Review action**: Spot-check 3 answers. If all are partial book lists → bulk F_PCT.

### Batch 3: SoM × task 23 — 73 cases (BULK: F_PCT or F_ARC)

SoM answers include "Rachel" but miss "T. Gannon" or vice versa. Some answers
include garbled text from screenshot OCR.
**Suggested classification**: F_PCT if partial names found, F_ARC if garbled.
**Review action**: Check if answer contains "Rachel" and/or "T. Gannon". Split accordingly.

### Batch 4: SoM × task 198 — 48 cases (BULK: F_ARC)

SoM answers wrong customer names (hallucinated from screenshot). Text-only gets
"Veronica Costello" correctly. SoM reads names from blurry screenshot text.
**Suggested classification**: F_ARC (SoM screenshot OCR limitation).
**Review action**: Spot-check 3. If all are wrong names → bulk F_ARC.

### Batch 5: SoM × task 26 — 35 cases (BULK: F_PCT or F_ARC)

SoM finds some reviewers but not all. Similar to Batch 3.
**Suggested classification**: F_PCT.
**Review action**: Check answer content.

### Batch 6: CUA × task 29 — 24 cases (BULK: F_AMB or F_PCT)

CUA answers "0" for task 29 (correct is "1"). Same baseline noise as text-only.
**Suggested classification**: F_AMB (task 29 counting noise).
**Review action**: If answer is "0" → F_AMB. If other → individual review.

### Batch 7: SoM × task 293 — 17 cases (BULK: F_ARC)

SoM answers "/" or garbled text. Can't read SSH clone URL from screenshot.
**Suggested classification**: F_ARC.
**Review action**: Spot-check 3.

### Batch 8: SoM × task 29 — 14 cases (BULK: F_ARC or F_PCT)

SoM answers wrong numbers (14, 200, 7 instead of 1). Misreading vote counts
from screenshot.
**Suggested classification**: F_ARC (screenshot OCR).
**Review action**: Check if answers are numbers → F_ARC.

### Batch 9: CUA × task 293 — 9 cases (NEEDS INDIVIDUAL REVIEW)

Some CUA answers have the correct URL but missing "git clone" prefix.
Need to check if GT correction should be expanded.
**Review action**: Check each answer against GT.

### Batch 10: CUA × task 94 — 6 cases (BULK: F_ARC)

CUA can't find invoice via guest order lookup. Architecture limitation.
**Suggested classification**: F_ARC.

### Batch 11: Remaining individual cases — 33 cases (INDIVIDUAL REVIEW)

- Claude text-only × task 198 × L5: 3 cases — wrong customer names (L5 ghost buttons)
- Claude text-only × task 23 × L1: 1 case — reviews section not loading
- Claude text-only × task 26 × L1: 2 cases — reviews not accessible
- Claude text-only × task 293: 4 cases — navigation failure
- Claude text-only × task 67: 4 cases — partial book lists
- SoM × task 188: 2 cases — login credential message
- SoM × task 67: 8 cases — partial book lists
- Llama 4 × various: 7 cases — individual review needed
- CUA × task 24: 1 case — product page review access
- CUA × task 198: 1 case — admin access failure

---

## Review Workflow

### Phase 1: Bulk classification (~30 min)
Batches 1-8 and 10 (296 cases). Spot-check 3 per batch, apply bulk label.

### Phase 2: Individual review (~2-3 hours)
Batch 9 (9 cases) + Batch 11 (33 cases) = 42 cases.
For each: read answer, classify, note reason.

### Phase 3: Validation (~30 min)
Random sample 20 auto-classified cases, verify labels match.

### Output
- `data/mode-a-failure-taxonomy.json`: all 1,670 failures with category labels
- Update `mode-a-analysis.md` with final taxonomy distribution

---

## Priority

This task book is **not blocking** the compositional study (C.2) or paper writing.
The failure taxonomy enriches §5.1 (per-operator behavioral drops) but the core
results (success rates, operator ranking, cross-model comparison) are already complete.

**Recommended timing**: Do Phase 1 (bulk) now, Phase 2 (individual) during paper
writing when you need to cite specific failure examples.
