# Phase 4b — Ecological Prevalence Probe (34-site Tier-3 audit) ★ EXTERNAL VALIDITY

> **Purpose**: provide an outside-the-lab check that the AMT Low operators
> model conditions that actually occur on real websites. Scans 30 real-world
> sites + 4 WebArena calibration instances with axe-core + custom patch
> probes, then reports the fraction carrying at least one Tier-3 (structural)
> accessibility violation.
> **Status (2026-06-06)**: data frozen 2026-04-13 (`scan-a11y-audit/results/`).
> Distinct corpus from the N=14,768 case study — these are *site* scans, not
> agent runs. Underwrites paper §4 ecological prevalence (Tier-3 82.4%).

## Research conclusions

- **Tier-3 structural violations are common in the wild**: 28/34 sites = 82.4%
  carry at least one structural (Tier-3) violation, matching the three
  structural AMT patches P7 (landmark→div), P9 (thead→div), P11 (link→span).
- **WebArena base ≈ real-world L1/L2 level, L3-clean** — the 4 WebArena
  calibration instances sit below the real-world structural-violation rate,
  confirming that the Low variant patches model the *degraded* end of what
  real-world WCAG-A-failing sites already look like, not a straw-man extreme.
- **Per-patch prevalence** (conservative; JS event delegation inflates the
  true link→span rate): P7 landmark→div is the most common, P9/P11 less so.
- **➜ Counters the "WebArena is a toy benchmark" reviewer attack**: the same
  structural failures the Low operators induce are already present on a
  majority of audited production sites.

## Why this exists

The N=14,768 case study runs agents on a controlled WebArena fork; a reviewer
may object that the Low operators describe degradations that never happen in
the wild. The ecological probe answers that directly by scanning real sites
with the same patch-detection logic, so the prevalence claim and the lab
manipulation share one severity taxonomy.

## Design

```
30 real-world sites + 4 WebArena instances = 34 audited sites
```

| Dimension | Values |
|---|---|
| Sites | 30 real-world sites across 6 sectors (ecommerce, china, saas, media, government) + 4 WebArena Docker instances for calibration |
| Scanner | Playwright + axe-core, plus custom DOM checks for the AMT patches (P11 div-as-link, Shadow DOM boundary, etc.) |
| Severity model | Three-layer framework: L1 decorative / L2 annotation / L3 structural, applied to violation counts |

Run by `scan-a11y-audit/` (2026-04-13, Phase 3 ecological audit subproject).

## On-disk data

| Path | Contents |
|---|---|
| `scan-a11y-audit/results/<site>.json` | one per-site axe-core + custom-probe result JSON (~34 sites; `_`-prefixed files are skipped by the loader) |
| `scan-a11y-audit/analysis.py` | `PATCH_SEVERITY` + `patch_affected` — the single source of truth for Tier-3 classification, shared with the verifier |

This corpus is **separate from** the N=14,768 case JSONs and the
~59k JSON files on disk under `data/`; it lives entirely under
`scan-a11y-audit/`.

## Headline findings (paper §4)

### Tier-3 (structural) prevalence
**28/34 sites = 82.4%** carry at least one Tier-3 structural violation,
triggering one or more of the structural patches P7 / P9 / P11.

### WebArena calibration
The 4 WebArena instances sit at the real-world L1/L2 level and are L3-clean,
anchoring the Low variant as a conservative floor rather than an extreme.

## How to audit

```sh
make audit-ecological
# python -m analysis.stages.phase4b_ecological
```

Verifier (`analysis/stages/phase4b_ecological.py`) asserts **3/3 PASS**:
- audited site count == 34 (`_constants.ECOLOGICAL_AUDIT_SITES`)
- Tier-3 prevalence == 82.4% (`_constants.ECOLOGICAL_TIER3_PCT`, tol 0.1pp)
- sites with ≥1 Tier-3 violation == 28 (exact)

Tier-3 classification is loaded directly from `scan-a11y-audit/analysis.py`
so the verifier and the paper's table generator share one definition.

## Paper sections

- **§4 Ecological prevalence** — Tier-3 82.4% headline; the severity
  distribution across the 34 sites and the WebArena-vs-real-world comparison.
- **`scan-a11y-audit/`** — the Phase 3 ecological audit subproject that
  produced these scans.

## Authoritative numbers

`analysis/_constants.py` is the single source of truth
(`ECOLOGICAL_AUDIT_SITES = 34`, `ECOLOGICAL_TIER3_PCT = 82.4`). The verifier
reads from it; `make verify-all` writes the audited result to
`results/key-numbers.json`.

## See also

- [README.md](README.md) — stage index (this is stage 8)
- [audit-2026-05-15.md](audit-2026-05-15.md) — cross-stage V&V narrative
- `docs/project-phases.md` — Phase 3 ecological-validation narrative
