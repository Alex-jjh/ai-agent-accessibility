# Experiment Data Inventory

> **Snapshot date**: 2026-05-14
> **Total**: ~10.5 GB on disk, 22 experiment directories, ~22.5 k case JSON files (across phases).
> **Scope**: top-level directories under `data/`. Per-row schema lives in `data-schema.md`.

This file is the **authoritative directory index**. The original
`data/README.md` predates Mode A / C.2 / Stage 3 and only covers the
N=1,040 composite study; do not rely on it for current state.

`data/` itself is **not modified** by the 2026-05-14 archival pass.
data.zip (~2.9 GB) at the repo root is the user's verified full
backup; both are retained.

## Quick stats

| Phase | Directories | Cases (JSON) | Disk | Paper § |
|---|---|---:|---:|---|
| Phase 1 — Composite (N=1,040) | 6 (pilot4-* + expansion-*) | 1,040¹ | ~383 MB | §5.1 composite |
| Phase 2 — Mode A depth (N=4,056) | 3 (mode-a-shard-{a,b}, mode-a-llama4-textonly) | 4,056 | 1.3 GB | §5.2 alignment, §5.3 cross-model (depth column) |
| Phase 3 — C.2 composition (N=2,184) | 2 (c2-composition-shard-{a,b}) | 2,184 | 709 MB | §5.4 composition |
| Phase 4 — DOM signature audit | 1 (amt-audit-batch) | n/a (per-URL audit JSON) | 225 MB | §5.2 D-rows |
| Phase 6 — Stage 3 breadth (N=7,488) | 2 (stage3-{claude,llama}) | 7,488 | 5.1 GB | §5.1–5.3 (primary) |
| Phase 6 — Stage 4b SSIM | 1 (stage4b-ssim-replay) | n/a (9,408 PNGs + manifest) | 699 MB | §5.3 visual control |
| Reference / triangulation | 1 (a11y-cua) | n/a (Griffith + A11y-CUA inputs) | 11 MB | §5.5 triangulation |
| Smoker (gate) | 2 (smoker-shard-{a,b}) | 2,052 | 1.7 GB | §4 task funnel narrative |
| Mirrors / re-derivable | 3 (mode-a-shard-{a,b}-screenshots, visual-equivalence) | n/a (screenshots) | 1.0 GB | (visual mirror, no JSON) |
| Superseded (archive/) | many | ~600+ | 252 MB | exclusion provenance only |

## §1 Production data — used in paper (DO NOT DELETE)

These directories' case JSON files feed the published numbers via
`analysis/export_combined_data.py` → `results/combined-experiment.csv`
or, for Stage 3, via per-experiment CSVs under `results/stage3/`.

| Dir | Cases | Phase | Model × agent | Description | Paper § |
|---|--:|---|---|---|---|
| `pilot4-full/` | 240 | 1 composite | Claude × text+SoM | 6 tasks × 4 variants × 5 reps | §5.1 |
| `pilot4-cua/` | 120¹ | 1 composite | Claude × CUA | 6 tasks × 4 variants × 5 reps | §5.1 |
| `expansion-claude/` | 140 | 1 composite | Claude × text | 7 new tasks × 4 variants × 5 reps | §5.1 |
| `expansion-llama4/` | 260 | 1 composite | Llama 4 × text | 13 tasks × 4 variants × 5 reps | §5.1, §5.3 |
| `expansion-som/` | 140 | 1 composite | Claude × SoM | 7 new tasks × 4 variants × 5 reps | §5.1 |
| `expansion-cua/` | 140 | 1 composite | Claude × CUA | 7 new tasks × 4 variants × 5 reps | §5.1 |
| `mode-a-shard-a/` + `mode-a-shard-b/` | 1,638 + 1,404 = 3,042 | 2 depth | Claude × {text, SoM, CUA} | 13 tasks × 26 ops × 3 archs × 3 reps | §5.2 alignment, §5.3 (depth) |
| `mode-a-llama4-textonly/` | 1,014 | 2 depth | Llama 4 × text | 13 tasks × 26 ops × 3 reps | §5.3 cross-model (depth) |
| `c2-composition-shard-a/` + `c2-composition-shard-b/` | 1,092 + 1,092 = 2,184 | 3 composition | Claude × {text, CUA} | 28 pairs × 13 tasks × 2 archs × 3 reps | §5.4 |
| `stage3-claude/` | 3,744 | 6 breadth ★ primary | Claude × text | 48 tasks × 26 ops × 3 reps | §5.1–§5.3 |
| `stage3-llama/` | 3,744 | 6 breadth ★ primary | Llama 4 × text | 48 tasks × 26 ops × 3 reps | §5.1–§5.3 |
| `stage4b-ssim-replay/` | 9,408 PNGs | 6 breadth | (replay only) | 336 URLs × 28 variants visual capture | §5.3 SSIM control |
| `amt-audit-batch/` | per-URL JSON | 4 DOM signature | (audit only) | DOM/visual signature inputs for Mode A | §5.2 D-rows |
| `a11y-cua/` | dataset directories | reference | (Griffith + A11y-CUA) | Human baseline + cross-study triangulation inputs | §5.5 |

¹ pilot4-cua holds **121** files on disk because `ecommerce_high_23` has
6 attempts (one was a hung-bridge retry from a stale UUID). The export
script (`analysis/lib/load.py:_select_largest_uuid`) selects the UUID with
the most files (120), restoring the design N=1,040 in the CSV.

**Stage 4b is the only single-source-of-truth dir**: burner S3 expired
2026-05-12. Off-platform copies live (a) on Google Drive, (b) inside
data.zip, (c) the local `data/stage4b-ssim-replay/`. SHA-256 manifest at
`data/stage4b-ssim-replay.sha256` (9,410 lines, 2.1 MB) lets a future
restore verify integrity.

## §2 Smoker (Stage 1 base-solvability gate)

Required to support the §4 narrative on the 7-gate funnel that produced
the 48-task Stage 3 set. Cases are not used in any reported success
rate, but the exclusion table cites them.

| Dir | Cases | Description | Cited in |
|---|--:|---|---|
| `smoker-shard-a/` | 1,122 | shopping_admin (182) + shopping (192) at base × text × 3 reps | F11 task funnel, §4 task selection |
| `smoker-shard-b/` | 930 | reddit (114) + gitlab (196) at base × text × 3 reps | F11 task funnel, §4 task selection |

Output: `results/smoker/passing-tasks.json` (48 tasks) and
`results/smoker/exclusion-report.md`.

## §3 Mirror / re-derivable

Retained because they are referenced by tooling, but content is
reconstructable from §1 sources.

| Dir | Source | Why kept |
|---|---|---|
| `mode-a-shard-a-screenshots/` (503 MB) + `mode-a-shard-b-screenshots/` (508 MB) | Mode A Claude × CUA per-step screenshots | Read by `scripts/screenshot-audit/`; also human review fodder for §5.3 phantom-bid trace narrative |
| `visual-equivalence/` (31 MB) | Phase 7 ablation-replay & click-probe outputs | Static; referenced by `analysis/visual_equivalence_analysis.py` (now superseded by Stage 4b SSIM replay). |

## §4 Superseded — `data/archive/`

Pre-Plan-D pilots and dev smokes. Kept for provenance per
`docs/project-phases.md`; not loaded by any analysis script that
produces paper numbers.

| Dir | Type | Cases | Notes |
|---|---|--:|---|
| `archive/pilot3a/` | superseded | 120 | Pre-Plan D. Discovered goto-escape bug. |
| `archive/pilot3b/` | superseded | 240 | Confirmed goto-escape; led to Plan D. |
| `archive/pilot3b-190/` | partial | 190 | Pilot 3b incomplete run (pre-vision fix) |
| `archive/pilot4-52/` | partial | 52 | Pilot 4 pre-hang-fix (same run ID as pilot4-full) |
| `archive/reinject-smoke{,-v2,-v3,-v4}/` | debug | ~4 each | Variant injection debugging |
| `archive/gitlab-smoke/` | smoke | 12 | Phase 1 GitLab validation |
| `archive/expansion-phase2-smoke/` | smoke | 16 | Phase 2 admin+shopping |
| `archive/expansion-{som,cua}-smoke/` | smoke | 28 each | SoM/CUA validation |
| `archive/llama4-smoke/` | smoke | 4 | Llama 4 Bedrock chain check |
| `archive/task188-smoke/` | smoke | 4 | Task 188 replacement |
| `archive/psl-expanded-smoke/` | smoke | 6 | PSL variant (BrowserGym divergence finding) |
| `archive/b1-smoke/`, `archive/amt-batch.log`, `archive/amt-dom-signatures/` | misc | — | Various utility runs |

## §5 Two-layer file layout per experiment (BOTH retained)

Every production experiment dir has the same internal shape, with the
case data stored **twice** in different layouts. Both layouts have
active readers; deletion of either breaks an analysis path.

| Path | Format | Read by |
|---|---|---|
| `<exp>/<run-uuid>/cases/<case>.json` | Flat case JSON, ~96 KB each, full trace + outcome inline | `analysis/export_combined_data.py`, `analysis/run_statistics.py`, `analysis/amt_statistics.py`, most `scripts/amt/*.py` |
| `<exp>/track-a/runs/<run-uuid>/cases/<case>/{trace-attempt-1.json, scan-result.json}` | Per-case sub-directory split | `analysis/cua_failure_trace_validation.py`, `analysis/semantic_density.py`, `scripts/amt/extract-l1-traces.py` |
| `<exp>/exports/{experiment-data, failure-classifications, scan-metrics, trace-summaries}.csv` | CSV exports | downstream stats, paper number verifier |
| `<exp>/<run>.log` (e.g. `stage3.log`) | runner log | grep-only |

Verified 2026-05-14 by a repo-wide grep for `track-a/runs` and
`trace-attempt-1.json`.

## §6 Backup posture (as of 2026-05-14)

| Source | Location | Verified |
|---|---|---|
| Full `data/` snapshot | `data.zip` (~2.9 GB at repo root, gitignored) | User-confirmed |
| Stage 4b only | `data/stage4b-ssim-replay/` local + `data.zip` + Google Drive | Local file count = 9,410; SHA-256 manifest at `data/stage4b-ssim-replay.sha256` |
| Burner S3 | **dead** (2026-05-11 / 2026-05-12 expirations passed) | n/a |

A `pre-archival-2026-05-14` git tag in this repo + `paper/` repo marks the state at the time of this inventory and serves as the rollback anchor for the consolidation pass that produced this file.

## See also

- `docs/data-schema.md` — per-row CSV column reference
- `docs/project-phases.md` — narrative timeline the directory names map onto
- `docs/handoff-2026-05-11.md` — most recent handoff (what's next)
- `docs/repo-cleanup-plan.md` — 2026-05-02 root-directory cleanup (executed)
- `data/README.md` — legacy README, narrower scope (Phase 1 only)
