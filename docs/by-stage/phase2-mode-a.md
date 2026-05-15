# Phase 2 — Mode A Depth (N=4,056)

> **Purpose**: decompose the composite Low effect into per-operator drops at
> mechanistic resolution; produce trace-level deep dives that anchor the
> paper's behavioural-signature alignment claims.
> **Status (2026-05-15)**: data frozen 2026-05-02. Used as **depth set** in
> the paper (§5.2 alignment, §5.3 cross-model, trace narratives). Stage 3
> (Phase 6) replicates the headline findings at 48-task breadth.

## Research conclusions

- **L1 landmark paradox**: ~6 elements at SSIM=1.000, yet largest behavioral
  drop (−40pp depth, −28pp breadth). Smallest DOM footprint, largest impact.
- **L11 link→span shows agent adaptation**: 365 DOM changes but only −1.5pp
  drop for Claude (depth) — agent switches to `goto()` URL fallback. Llama 4
  drops −14.6pp on the same operator (no adaptive fallback), proving
  robustness is environment × capability, not environment-only.
- **Three-tier behavioral structure**: 21/26 operators land within ±3pp of
  H-baseline (neutral); only L1, L5 are individually destructive. **Sparsity
  is itself a finding**.
- **GEE confirms cluster-robust significance**: both indicator models
  (destructive vs rest; Low-family vs H-family) yield β<0 with z<−2.0 after
  task-level clustering — operator effect persists after random-intercept
  adjustment.
- **➜ Motivates Phase 3**: 21 individually benign operators yet composite
  produces 55pp collapse — the missing piece is **interaction**.

## Design matrix

```
Claude × {text-only, SoM, CUA} × 26 ops × 13 tasks × 3 reps  =  3,042 cases
Llama 4 × text-only           × 26 ops × 13 tasks × 3 reps  =  1,014 cases
                                                       Total =  4,056
```

| Dimension | Values |
|---|---|
| Tasks | same 13 as Phase 1 (mechanism-coverage hand-pick) |
| Operators | L1–L13, ML1–ML3, H1–H8 + H5a/b/c (the 26 AMT operators) |
| Reps | 3 per cell (reduced from Phase 1's 5 — operator dimension already explodes N) |
| Models | Claude Sonnet 4 (primary), Llama 4 Maverick (cross-model replication) |
| Agents | Claude: text-only / SoM / CUA. Llama: text-only only. |

Operators applied via `src/variants/patches/inject/apply-all-individual.js`
in **individual-mode** (single operator per case, not composite).

## On-disk data (~1.3 GB total)

| Directory | Cases | Model × agent | Date |
|---|--:|---|---|
| `data/mode-a-shard-a/` | 1,638 | Claude × {text, SoM, CUA} (shard A: half tasks) | 2026-05-01 |
| `data/mode-a-shard-b/` | 1,404 | Claude × {text, SoM, CUA} (shard B: half tasks) | 2026-05-01 |
| `data/mode-a-llama4-textonly/` | 1,014 | Llama 4 × text-only (all 13 tasks) | 2026-05-02 |
| **Total** | **4,056** | | |

`mode-a-shard-{a,b}` together = 3,042 = 26 × 13 × 3 × 3 (Claude × 3 archs).
Sharding split was done at the task level for parallelism on 2 burner accounts.

### Mirror: per-step screenshots

| Directory | Size | Contents |
|---|--:|---|
| `data/mode-a-shard-a-screenshots/` | 503 MB | per-step CUA screenshots for shard A |
| `data/mode-a-shard-b-screenshots/` | 508 MB | per-step CUA screenshots for shard B |

These are NOT part of the SSIM analysis; they are CUA-action visualisations
used in §5.5 trace narratives. Reconstructable from the trace JSONs.

### Per-experiment file layout

Same dual-layout convention as Phase 1: `<run-uuid>/cases/*.json` flat +
`track-a/runs/<uuid>/cases/<case>/{trace-attempt-1.json, scan-result.json}`
per-case dir.

## Ground-truth corrections

3 tasks are subject to GT corrections (Magento Docker drift / GitLab external
URL). Defined in `analysis/_constants.py:GT_CORRECTIONS`; metadata source
`scripts/amt/ground-truth-corrections.json`. Applied uniformly by
`analysis/lib/load.py:apply_gt_corrections()`.

| task_id | task | original GT | additional valid |
|---|---|---|---|
| 41 | Top search term in store | "hollister" | "abomin", "abdomin" |
| 198 | Most recent cancelled order customer | "Lily Potter" | "Veronica Costello" |
| 293 | SSH clone command for Super_Awesome_Robot | "metis.lti.cs.cmu.edu:2222/…" | "10.0.1.50:2222/…" |

Phase 6 Stage 3 excluded state-mutation tasks via Gate 6, eliminating this
class of confound for the breadth set.

## Derived artefacts (`results/amt/`)

| File | Producer |
|---|---|
| `results/amt/behavioral_signature_matrix.csv` | per-operator success rates × 3 archs × 2 models |
| `results/amt/dom_signature_matrix.csv` | 12-dim DOM signature (see Phase 4) |
| `results/amt/signature_alignment.csv` | DOM × behavioural alignment classification |
| `results/amt/signature_alignment_report.md` | narrative of L1 / L11 / L5 alignment categories |
| `results/amt/statistics_report.md` | inferential tests (Fisher exact + Holm-Bonferroni) |

## How to audit

```sh
make audit-mode-a
# python -m analysis.stages.phase2_mode_a  (equivalent)
```

Verifier asserts:
- `mode-a-shard-{a,b}` Claude case count = 3,042
- `mode-a-llama4-textonly` Llama 4 case count = 1,014
- per-arch split for Claude: text-only / vision-only / cua each = 1,014
- 26 operators each appear in Claude text-only (no missing, no unexpected)

## Paper sections

- **§5.2 Signature alignment** — `tab:dom-sig` per-op DOM signatures + `figure6_alignment_scatter` (DOM-magnitude × behavioural-drop scatter).
- **§5.3 Cross-model replication** — Mode A Claude vs Mode A Llama 4 (depth column); the 5/5 bottom-operator overlap on Claude that motivates Stage 3 trust.
- **§5.5 Vision findings (phantom bids)** — Mode A SoM trace narratives.
- **§5.5 L1 / L5 / L11 trace narratives** — `docs/analysis/mode-a-{landmark-paradox,L5-shadow-dom,L11-L6-llama4-vulnerability,L12-task29}-*.md`.

## Known caveats

- **CUA depth baseline is depressed (48.2%)**: 5 of 13 tasks exceed CUA's
  coordinate-action capability. Composite CUA (93.8% baseline) used for
  primary decomposition; Mode A CUA is supplementary.
- **L11 depth signal weaker than breadth** — Mode A: Claude +1.5pp / Llama
  +14.6pp. Stage 3 (breadth) refines to +2.3pp / +14.1pp. Both data points
  are reported; paper now leads with the breadth numbers.
- **GT corrections accept both old and new ground truth**: zero
  disagreements observed on 78 affected cases per task.
