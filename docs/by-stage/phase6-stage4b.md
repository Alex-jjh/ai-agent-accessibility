# Phase 6 — Stage 4b SSIM Trace-URL Replay (9,408 PNGs) ★ VISUAL TRUTH

> **Purpose**: provide a quantitative visual control replacing the original
> CUA-based "visual equivalence" argument. Captures every URL the Stage 3
> agents observed under base + base2 + 26 AMT operators, computes SSIM /
> pHash / WCAG-contrast deltas vs base.
> **Status (2026-05-15)**: data frozen 2026-05-11. **Single source of truth
> for all visual-equivalence / SSIM claims** (per user directive). Older
> captures under `data/visual-equivalence/` are deprecated — see that
> directory's `STATUS.md`.

## Research conclusions

- **Single source of truth for visual equivalence**: 336 unique URLs from
  Stage 3 traces × 28 variants (base + base2 + 26 operators) = 9,408 captures.
  Exhaustive pixel-level coverage replaces earlier 13-task CUA-based argument.
- **3 operators visually distinguishable** (median SSIM < 0.99): L5 (0.834),
  L6 (0.889), L11 (0.979). 23 operators visually indistinguishable — their
  behavioral drops are NOT due to visual misperception.
- **Baseline noise floor < 0.001** (base vs base2 deterministic-render
  check) → wide margin for true signal vs. rendering jitter.
- **L9 narrative-vs-SSIM reconciliation**: paper §3 places L9 in "structural
  Tier 3" narrative category; aggregate SSIM=1.000 because L9 only affects
  table-bearing pages (most of 336 URLs unaffected). Narrative classification
  is independent of SSIM-magnitude claim; both correct in their respective
  contexts.
- **➜ Replaces CUA visual control at substantially greater rigor**: 336 URLs
  × pixel-level diff vs 13 tasks × indirect CUA performance. Underwrites
  paper §4.117 visual-equivalence audit and §5.3 SSIM analysis.

## Why this exists

Earlier visual-equivalence runs (Phase 7, April 2026) used 13 hand-picked
URLs and a 13-element `patch_01..13` numbering that does not map to the
26 AMT operators. After AMT was formalised, those captures became
unanalysable for the operator-resolved SSIM claims the paper makes.
Stage 4b is the **redo at scale and at the right operator granularity**.

## Design

```
336 unique URLs  ×  28 variants  =  9,408 captures
```

| Dimension | Values |
|---|---|
| URLs | 336 unique URLs the Stage 3 Claude agent visited at least once. Extracted by `scripts/stage3/extract-stage3-urls.py` from the per-step `agentConfig.targetUrl`. |
| Variants (28 total) | `base` + `base2` (independent re-capture for noise floor) + 26 AMT operators (`L1..L13`, `ML1..ML3`, `H1..H8`, `H5a/b/c`) |
| Captures | one PNG per (URL, variant) cell; no agent action, just navigate + apply variant + screenshot |

Run by `scripts/stage3/replay-stage3-urls.py` on burner B (2026-05-11).

## On-disk data (~699 MB)

| Path | Size | Contents |
|---|--:|---|
| `data/stage4b-ssim-replay/` | 699 MB | one slug-named subdirectory per URL |
| `data/stage4b-ssim-replay/<slug>/` | ~28 PNGs | `base.png`, `base2.png`, `L1.png`, …, `H8.png` |
| `data/stage4b-ssim-replay/manifest.jsonl` | 9,408 lines | one JSON per capture |
| `data/stage4b-ssim-replay/replay.log` | runner stdout |
| `data/stage4b-ssim-replay.sha256` | 2.1 MB | 9,410 lines (PNGs + manifest + log) — integrity manifest |

### Slug naming
```
<app>__<url-path-flattened>__<8-char-hash>
e.g. shopping_admin__admin-admin-dashboard__81d2a7c3
     gitlab__primer-design-graphs-main__f2f4fff3
```

### `manifest.jsonl` per-line schema
```json
{
  "url": "http://10.0.1.50:7780/admin/admin/dashboard/",
  "variant": "L5",
  "screenshot": "/.../shopping_admin__admin-admin-dashboard__81d2a7c3/L5.png",
  "success": true,
  "error": null,
  "elapsed_s": 3.75,
  "final_url": "http://10.0.1.50:7780/admin/admin/dashboard/",
  "title": "Dashboard / Magento Admin",
  "dom_changes": 8,
  "attempts": 1,
  "session_lost": false,
  "slug": "shopping_admin__admin-admin-dashboard__81d2a7c3",
  "app": "shopping_admin",
  "visits": 48,
  "rep": 0
}
```

The fields `session_lost`, `final_url`, and `title` are **load-bearing for
login-contamination detection** — Magento admin sessions can silently expire
mid-replay, returning the login page instead of the target. The verifier
reports the contamination rate as a non-failing health metric.

## Derived artefacts (`results/stage3/visual-equiv/`)

| File | Producer | Schema |
|---|---|---|
| `ssim-per-url.csv` | `scripts/stage3/ssim-analysis.py` | one row per (slug, op) — slug, operator, family, ssim, phash_dist (9,073 rows = 336 URLs × ~27 ops minus a few replay failures) |
| `ssim-per-operator.csv` | same | aggregated: operator, family, n_urls, ssim_{mean, median, p10, p25, p75, p90}, ssim_std, ssim_min, phash_mean, delta_from_noise, cohens_d, wilcoxon_p, visual_change |
| `stage3-urls.csv` | `scripts/stage3/extract-stage3-urls.py` | per-step URL provenance from Stage 3 traces (1,197 rows) |
| `stage3-urls-dedup.csv` | same | one row per unique URL with visit count |
| `stage3-urls-summary.md` | same | URL set design + cost estimate |
| `ssim-audit-candidates.md` | manual | 20 (operator, URL) pairs flagged for human visual spot-check |

## Headline findings (paper §4.117 + §5.3)

### Operators with median SSIM < 0.99
The empirical set is exactly **{L5, L6, L11}**:

| Op | Median SSIM | Family | Mechanism |
|---|--:|---|---|
| L5 | 0.834 | Low | Shadow DOM wrap → buttons lose styling |
| L6 | 0.889 | Low | heading→div → font sizes shrink |
| L11 | 0.979 | Low | link→span → minor underline/colour shift |

### All other 23 operators: median SSIM ≥ 0.99
Visually indistinguishable in aggregate. Per-page diffs may show local
changes (e.g. L9 on table-bearing pages, L1 on landmark-rich pages), but
the median across 336 URLs is at noise floor.

### Baseline noise
`base` vs `base2`: median SSIM ≈ 1.000 (deterministic rendering verified).

### Note on L9 narrative vs L9 SSIM
Paper §3 places L9 (table flatten) in the "structural Tier 3" *narrative*
category. Its aggregate median SSIM is 1.0 because **L9 only affects pages
containing tables** (Magento admin reports, GitLab tree views) — most of
the 336 URLs are unaffected, so the aggregate signal washes out. The
narrative classification (structural / annotative / decorative) is
independent of the SSIM-magnitude claim, and both are correct in their
respective contexts.

## How to audit

```sh
make audit-stage4b
# python -m analysis.stages.phase6_stage4b
```

Verifier asserts:
- 9,408 PNGs on disk
- `manifest.jsonl` has 9,408 lines
- 336 unique URLs
- 28 variants present (base + base2 + 26 ops), set equality
- per-operator capture count = 336 (uniform)
- per-operator median SSIM matches sentinels (L5 ≈ 0.834, L6 ≈ 0.889, L11 ≈ 0.979)
- `{L5, L6, L11}` is exactly the set with median SSIM < 0.99
- login-contamination rate reported (informational, non-failing)

## Paper sections

- **§4.117 Visual-equivalence audit** — the SSIM control argument (replacing
  earlier CUA-based reasoning).
- **§5.3 SSIM analysis** — `figure F10_trace_url_ssim` (operator-distribution
  violin plot, sorted by median).
- **`docs/analysis/visual-equivalence-validation.md`** — narrative draft for §5.3.

## Backup posture

This is the **only single-source-of-truth dataset** as of 2026-05-15:
- Local: `data/stage4b-ssim-replay/` (699 MB)
- Backup 1: Google Drive (user-uploaded, 2026-05-11)
- Backup 2: `data.zip` at repo root (full data/ snapshot, ~2.9 GB)
- S3: **dead** (burner accounts expired 2026-05-12)

SHA-256 manifest at `data/stage4b-ssim-replay.sha256` (9,410 lines, 2.1 MB)
allows future restore verification.

## Known caveats

- **Login contamination on a subset of admin captures**: Magento admin
  session occasionally expires mid-replay; manifest flags via
  `session_lost` / `title contains 'login'`. The contamination rate is
  reported by the verifier as an informational metric. A login-filtered
  re-aggregation would tighten L9's signal but is **not currently planned**
  — the paper claim is the aggregate, not the login-filtered subset.
- **Per-URL visit count is uneven** (1 to 48 visits). Captures aren't
  weighted by visit count; SSIM aggregates are equal-URL-weighted.
- **Older Phase 7 captures (`data/visual-equivalence/`) are NOT consulted**.
  See that directory's `STATUS.md`.
- **`scripts/visual-equiv/audit-phase-b-{admin,all}.py` are deprecated**.
  Their login-detection logic is informally reproduced in the verifier.
