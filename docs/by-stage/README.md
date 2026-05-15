# Stage-Organized Documentation

> **Single index of every experimental phase.** One file per stage.
> Numbers, dirs, scripts, paper sections all linked; no narrative duplication.

The project comprises **6 phases** producing **N=14,768 case JSONs +
9,408 visual captures** across **7 datasets**. Each stage doc below answers:

- What ran? (design matrix)
- Where is the data? (paths)
- How do I audit it? (one-liner)
- Where does it appear in the paper? (§ refs)
- What's frozen / what's stale?

| # | Stage | Dataset N | Scripts | Doc |
|---|---|--:|---|---|
| 1 | Phase 1 — Composite variant | 1,040 | `analysis.stages.phase1_composite` | [phase1-composite.md](phase1-composite.md) |
| 2 | Phase 2 — Mode A depth | 4,056 | `analysis.stages.phase2_mode_a` | [phase2-mode-a.md](phase2-mode-a.md) |
| 3 | Phase 3 — C.2 composition | 2,184 | `analysis.stages.phase3_c2` | [phase3-c2.md](phase3-c2.md) |
| 4 | Phase 4 — DOM signature audit | 26 ops × 12 dims | `analysis.stages.phase4_dom_signatures` | [phase4-dom-signatures.md](phase4-dom-signatures.md) |
| 5 | Phase 5 — Smoker (base-solvability gate) | 2,052 | `analysis.stages.phase5_smoker` | [phase5-smoker.md](phase5-smoker.md) |
| 6 | Phase 6 — Stage 3 breadth | 7,488 | `analysis.stages.phase6_stage3` | [phase6-stage3.md](phase6-stage3.md) |
| 7 | Phase 6 — Stage 4b SSIM | 9,408 PNGs | `analysis.stages.phase6_stage4b` | [phase6-stage4b.md](phase6-stage4b.md) |

**Cross-stage audit**: [audit-2026-05-15.md](audit-2026-05-15.md) — full V&V audit narrative + per-stage research conclusions + statistical method coverage matrix + top-line synthesis. Re-runs after `make verify-all`.

**Total experimental N (case JSONs)**: 1,040 + 4,056 + 2,184 + 7,488 = **14,768**.
**Total Stage 4b captures (PNGs)**: 9,408 (visual control, not counted in N).

## Auditing

```sh
# All stages at once
make verify-all

# One stage at a time
make audit-composite     # phase1
make audit-mode-a        # phase2
make audit-c2            # phase3
make audit-dom           # phase4
make audit-smoker        # phase5
make audit-stage3        # phase6
make audit-stage4b       # phase6 visual
```

Each stage independently runnable as `python -m analysis.stages.phase<N>_<id>`.

## Authoritative numbers

`analysis/_constants.py` is the single source of truth. Verifiers read from
it; `make verify-all` writes the audited results to `results/key-numbers.json`.
Paper claims must trace to one of these two files.
