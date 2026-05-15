# `results/by-stage/` — Per-Stage Results Index

**This directory does not duplicate data.** It indexes where each stage's
derived artefacts live in the existing `results/` layout (which predates
the by-stage reorg).

For data sources, audit scripts, and paper § references see
[`docs/by-stage/`](../../docs/by-stage/).

| Stage | Verifier writes | Other artefacts |
|---|---|---|
| Phase 1 — Composite | `key-numbers.json` (via `verify_all`) | `results/combined-experiment.csv`, `results/stats/*`, `results/bootstrap_decomposition.csv`, `results/breslow_day_cross_model.txt`, `results/majority_vote_*.csv` |
| Phase 2 — Mode A depth | `key-numbers.json` | `results/amt/{behavioral_signature_matrix.csv, statistics_report.md, signature_alignment*}` |
| Phase 3 — C.2 composition | `key-numbers.json` | `results/amt/statistics_report.md` § "Composition" |
| Phase 4 — DOM signatures | `key-numbers.json` | `results/amt/dom_signature_matrix.csv`, `results/amt/dom-signatures/` |
| Phase 5 — Smoker | `key-numbers.json` | `results/smoker/{passing-tasks.json, exclusion-report.md, filter-summary.csv}` |
| Phase 6 — Stage 3 | `key-numbers.json` | `results/stage3/{*-download-audit.md, sanity-*.txt, pathological-*.txt, rate-limit-audit-*.md, per-operator-stage3.csv, statistics_report.md}` |
| Phase 6 — Stage 4b | `key-numbers.json` | `results/stage3/visual-equiv/{ssim-per-{operator,url}.csv, ssim-audit-candidates.md, stage3-urls*}` |

## key-numbers.json (single audit output)

Generated at the end of every `make verify-all` run. JSON schema:

```json
{
  "generated_at": "2026-05-15T...",
  "all_passed": true,
  "stages": {
    "phase1_composite": {
      "label": "...",
      "passed": true,
      "n_passed": 12,
      "n_failed": 0,
      "assertions": [{"name": "...", "expected": ..., "actual": ..., "passed": true}, ...]
    },
    ...
  }
}
```

Consumers:
- Paper consistency audit (`analysis/paper_consistency_audit.py`) reads it
  to cross-check paper *.tex against verified numbers.
- Future CI (when added) checks `all_passed == true`.

## Pre-V&V snapshot

`_pre-vv-snapshot.csv` is a copy of `results/combined-experiment.csv` taken
before the 2026-05-15 V&V refactor — kept as a rollback aid alongside the
`pre-vv-2026-05-15` git tag.
