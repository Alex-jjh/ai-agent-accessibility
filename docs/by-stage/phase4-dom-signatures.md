# Phase 4 — DOM Signature Audit (26 ops × 12 dims)

> **Purpose**: characterise each AMT operator's *DOM-level effect* (independent
> of agent behaviour) via a 12-dimensional signature. Together with the
> behavioural signature (Mode A / Stage 3), this enables paper §5.2 alignment.
> **Status (2026-05-15)**: data frozen 2026-04-30 (Mode A audit) and
> 2026-05-11 (Stage 4b SSIM). Used in §5.2 and `tab:dom-sig` appendix.

## Research conclusions

- **Per-operator DOM fingerprint** in 12 dims across 4 categories: D (DOM
  structure), A (Accessibility tree roles/names/state), V (Visual SSIM +
  bbox + contrast), F (Functional interactivity).
- **DOM magnitude does NOT predict behavioral drop**: Spearman ρ=0.426,
  p≈0.10 (NS) on the 16 operators with valid Fisher tests. This **misalignment
  is the central finding** — large changes (L11: 365 tag changes) can be
  benign, tiny changes (L1: 5.6 changes) can be catastrophic.
- **L1 / L5 / L11 contrast underwrites alignment scatter** (paper §5.2
  Fig 6): L1 (5.6 changes, SSIM=1.0, large drop), L5 (337 changes, SSIM=0.803,
  large drop), L11 (365 changes, SSIM=0.976, small drop) — three corners of
  the alignment plot.
- **Visual confounds excluded**: 23/26 operators have median SSIM ≥ 0.99 in
  aggregate — their behavioral drops cannot be attributed to visual
  misperception.
- **➜ Cross-references with Phase 2/6 behavioral signatures** to produce
  the paper's 4-quadrant alignment classification (aligned-active,
  aligned-null, agent-adaptation, structural-criticality).

## What it measures

Per operator, on each of 39 sample URLs (13 tasks × 3 page loads), capture
the page **before** and **after** applying the operator and compute:

| Dim | Name | Source |
|---|---|---|
| D1 | total tag changes | `document.querySelectorAll('*').length` delta |
| D2 | added / removed nodes | DOM mutation observer count |
| D3 | node-count delta | post − pre |
| A1 | roles changed | Chrome DevTools `Accessibility.getFullAXTree` diff |
| A2 | accessible-name changes | same source |
| A3 | total ARIA state changes | aria-* attribute diff |
| V1 | SSIM | `skimage.metrics.structural_similarity` (full-page screenshot) |
| V2 | max bounding-box shift (px) | layout diff |
| V3 | mean contrast delta | foreground/background lightness shift |
| F1 | interactive-count delta | `<button>, <a href>, <input>, [tabindex≥0]` delta |
| F2 | inline-handler delta | `onclick=`/`onkeydown=` count delta |
| F3 | focusable-count delta | tab-order set diff |

**12-dim, 26 operators, 39 samples per (op, dim) cell.**

## On-disk data (~225 MB, no case JSONs)

| Directory | Contents |
|---|---|
| `data/amt-audit-batch/batch-t<task>-r<rep>/` | per (task, rep) audit run: `audit.json` + `run.log` + `screenshots/` |
| `data/amt-audit-batch/smoke-{admin,gitlab,reddit,shopping,ssim-test}/` | one-off validation batches |

`batch-t<task>-r<rep>/audit.json` schema:
```json
{
  "task": "t4",
  "rep": 1,
  "operators": {
    "L1": { "D1": 11.2, "A1": 5.6, "A2": 5.6, "V1": 1.0, "F1": 0.0, ... },
    "L2": { ... },
    ...
  }
}
```

## Derived artefacts

| File | Producer |
|---|---|
| `results/amt/dom_signature_matrix.csv` | `scripts/amt/amt-signature-analysis.py` averages 39 samples per cell |
| `results/amt/dom-signatures/` | per-task per-op JSON dumps (raw audit detail) |

Table sentinels (paper appendix `tab:dom-sig`):

| Op | D1 | A1 | A2 | V1 (SSIM) | F1 |
|---|--:|--:|--:|--:|--:|
| L1 | 11.2 | 5.6 | 5.6 | 1.000 | 0.0 |
| L5 | 337.7 | 20.2 | 31.4 | 0.803 | −105.5 |
| L11 | 364.6 | 94.5 | 108.0 | 0.976 | −182.3 |

(The full 26-op table is in paper appendix Table 2.)

## How to audit

```sh
make audit-dom
```

Verifier asserts:
- exactly 26 rows in `results/amt/dom_signature_matrix.csv`
- all 26 AMT operators present (set equality)
- L1, L5, L11 sentinel values within tolerance of paper appendix

## Paper sections

- **§5.2 Signature alignment** — pairs DOM signature with behavioural
  signature; the L1 (DOM-minimal, behaviour-active) vs L11 (DOM-active,
  behaviour-null) contrast is the headline of the alignment scatter
  (`figure6_alignment_scatter`).
- **Appendix Table 2 (`tab:dom-sig`)** — full 26-op × 6-dim numeric table.
- **§4.117 visual-equivalence audit** — uses V1 (SSIM) as the visual
  control argument; superseded by Stage 4b at scale.

## Relationship to Stage 4b

Phase 4 audit uses **per-page captures over Mode A's 13 tasks** (39 samples).
Phase 6 Stage 4b is the **breadth re-do**: 336 unique URLs from Stage 3
traces, captured under all 28 variants (base + base2 + 26 ops). Stage 4b
produces a richer SSIM distribution at 9× the URL count.

For paper claims about visual equivalence:
- **L1, L11 SSIM, per-op median trends**: cite Stage 4b (current / primary).
- **Per-(task, op) DOM signature in `tab:dom-sig`**: cite Phase 4 audit.

## Known caveats

- **39 samples per cell is small** — per-task variance is high; we report
  means without per-task CIs.
- **D2/D3 may double-count**: a `replaceChild` shows up as both removed
  and added.
- **Some operators are pure no-ops on tasks without the relevant element**
  (L9 on pages with no table, L8 on pages with no `tabindex`). Aggregate
  averages dilute these operators' signature.
