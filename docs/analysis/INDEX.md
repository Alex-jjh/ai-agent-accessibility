# `docs/analysis/` — Per-Stage Index of 48 Deep-Dive Reports

> **What this is**: a stage classification of every file in this directory.
> The files themselves are kept as-is (frozen historical analysis); this
> INDEX provides discoverability without breaking cross-references.
>
> **What's NOT here**: per-phase main entries — those live in
> [`docs/by-stage/phase{1..6_stage4b}.md`](../by-stage/). This INDEX
> points from those main entries down to specific deep-dives.

## Quick navigation

| Stage | Files | Status |
|---|--:|---|
| Pre-AMT historical (frozen) | 13 | banner-marked, retained for provenance |
| Phase 1 — Composite | 12 | active reference for §5.1 |
| Phase 2 — Mode A depth | 11 | banner-marked stale (Stage 3 superseded) |
| Phase 3 — C.2 composition | 2 | banner-marked stale |
| Phase 4 — DOM signatures | 2 | active reference |
| Phase 5 — Smoker / task selection | 3 | active reference for §4 |
| Phase 6 — Stage 3 breadth | 0 | (no deep-dives yet — see `results/stage3/*-download-audit.md`) |
| Phase 6 — Stage 4b SSIM | 4 | active reference for §5.3 |
| Sundry / smoke / debug | 1 | retained for provenance |

**Total**: 48 files.

---

## §1 — Pre-AMT Historical (Pilot 3 / Pilot 4 / Plan D era)

Frozen 2026-04-14. Reports the pre-Plan-D pilot work that surfaced the
"goto escape" bug and motivated the variant-injection redesign. Useful
for understanding architectural decisions; not cited in current paper.

| File | Topic |
|---|---|
| `pilot3b-190-analysis.md` | Pilot 3b 190-case partial analysis |
| `pilot3b-190-textonly-deep-dive.md` | Pilot 3b-190 text-only agent |
| `pilot3b-190-trace-deep-dive.md` | Pilot 3b-190 trace deep dive |
| `pilot3b-190-vision-deep-dive.md` | Pilot 3b-190 vision-only agent |
| `pilot3b-textonly-analysis.md` | Pilot 3b text-only agent |
| `pilot3b-trace-deep-dive.md` | Pilot 3b trace deep dive |
| `pilot4-52-analysis.md` | Pilot 4 first-52 partial run (pre-hang fix) |
| `pilot4-cross-pilot-stats.md` | Pilot 3a vs Pilot 4 statistical comparison |
| `pilot4-deep-dives.md` | Pilot 4 deep-dive analysis |
| `pilot4-full-analysis.md` | Pilot 4 full 240/240 cases |
| `pilot4-cua-analysis.md` | Pilot 4 CUA pure-vision agent |
| `pilot4-vision-only-deep-dive.md` | Pilot 4 vision-only agent |
| `pilot4-plan-d-verification.md` | Plan D goto() persistence verification |

---

## §2 — Phase 1 / Composite (Expansion era)

Active references for paper §5.1 composite study. Document the 13-task
composite findings on Claude × {text, SoM, CUA} and Llama 4 × text.

| File | Topic |
|---|---|
| `expansion-claude-trace-deep-dive.md` | Claude expansion trace analysis on gitlab:308 + admin:94 low |
| `expansion-cross-agent-comparison.md` | 7 tasks × 4 variants × 4 agents comparison |
| `expansion-cua-full-deep-dive.md` | CUA full expansion experiment |
| `expansion-llama4-admin198-deep-dive.md` | Llama 4 admin:198 cross-model sensitivity |
| `expansion-llama4-admin4-deep-dive.md` | Llama 4 admin:4 total collapse |
| `expansion-llama4-ecom24-26-deep-dive.md` | Llama 4 ecommerce 24 / 26 |
| `expansion-llama4-reddit29-deep-dive.md` | Llama 4 reddit:29 paradoxical inversion |
| `expansion-phase2-smoke-deep-dive.md` | Phase 2 smoke pre-flight (admin + shopping) |
| `expansion-som-full-deep-dive.md` | SoM full expansion experiment |
| `expansion-som-smoke-deep-dive.md` | SoM smoke pre-flight |
| `expansion-vision-full-analysis.md` | SoM + CUA on 7 expansion tasks |
| `expansion-vision-smoke-deep-dive.md` | CUA expansion smoke trace analysis |

---

## §3 — Phase 2 / Mode A depth

Banner-marked frozen 2026-05-15 (commit `82d3e05`). Mode A is now the
*depth* complement to Stage 3 breadth; deep-dive reports remain accurate
mechanistically but their headline numbers (e.g. "C.2 = 2,188") have
been corrected — see banners.

| File | Topic |
|---|---|
| `mode-a-analysis.md` | Top-level Mode A report (3,042 Claude + 1,014 Llama 4) |
| `mode-a-B4-manual-review-taskbook.md` | F_UNK manual review (B.4) |
| `mode-a-D4-figure-plan.md` | D.4 figure plan for AMT paper |
| `mode-a-L1-cross-agent-trace-report.md` | L1 cross-agent trace evidence (landmark paradox) |
| `mode-a-L11-L6-llama4-vulnerability-analysis.md` | Why L11+L6 hit Llama 4 harder than Claude |
| `mode-a-L12-task29-trace-analysis.md` | L12 × task 29 trace-level failures |
| `mode-a-L5-shadow-dom-trace-report.md` | L5 Shadow DOM ghost-button trace |
| `mode-a-landmark-paradox-trace-report.md` | The landmark paradox — full trace evidence |
| `mode-a-task67-forced-simplification-deep-dive.md` | Task 67 forced-simplification narrative |
| `mode-a-docker-confounds.md` | Docker state confound audit (frozen banner) |

---

## §4 — Phase 3 / C.2 composition

Banner-marked frozen 2026-05-15 (commit `82d3e05`).

| File | Topic |
|---|---|
| `mode-a-C1-composition-targets.md` | C.1 — operator selection & interaction predictions |
| `mode-a-C2-composition-analysis.md` | C.2 full analysis: 28 pairs, 15 super-additive (frozen banner) |

---

## §5 — Phase 4 / DOM signatures

Active reference for paper §5.2 alignment. Cross-references with Phase 6
behavioral signatures.

| File | Topic |
|---|---|
| `mode-a-D3-signature-alignment.md` | AMT signature alignment (DOM × behavioral) |
| `mode-a-D4-figure-plan.md` *(also listed in §3)* | D.4 figure plan including alignment scatter |

---

## §6 — Phase 5 / Smoker / Task Selection

Active reference for paper §4 task funnel. Pre-registered Stage 3 task
selection protocol.

| File | Topic |
|---|---|
| `task-selection-methodology.md` | Stage 3 7-gate inclusion protocol (paper §4 drop-in) |
| `smoker-full-trace-audit.md` | Smoker full-dataset trace audit (2026-05-08) |
| `smoker-shard-b-trace-audit.md` | Smoker shard B pre–Stage-3 audit (2026-05-06) |

---

## §7 — Phase 6 / Stage 3 breadth

No deep-dive reports yet in `docs/analysis/`. Stage 3 audit reports live
in `results/stage3/`:

- `results/stage3/claude-download-audit.md` — final Claude audit
- `results/stage3/llama-download-audit.md` — final Llama 4 audit
- `results/stage3/sanity-{claude,llama}.txt` — completeness checks
- `results/stage3/pathological-{claude,llama}.txt` — pathological-task flags
- `results/stage3/rate-limit-audit-{claude,llama}.md` — Bedrock 429 confound

---

## §8 — Phase 6 / Stage 4b SSIM

Active references for paper §5.3 visual control.

| File | Topic |
|---|---|
| `visual-equivalence-architecture.md` | Architecture of the SSIM replay pipeline |
| `visual-equivalence-decision-memo.md` | Frozen 2026-04-22 decision memo (C++ path; banner) |
| `visual-equivalence-plan.md` | v2 URL-replay experiment plan |
| `visual-equivalence-validation.md` | SSIM validation findings (replaces CUA) |

---

## §9 — Sundry / Smoke / Debug

Retained for provenance.

| File | Topic |
|---|---|
| `gitlab-smoke-analysis.md` | GitLab smoke test (2026-04-12) |
| `psl-expanded-smoke-analysis.md` | Pure-Semantic-Low variant smoke (BrowserGym divergence finding) |
| `reinject-smoke-analysis.md` | Reinject-smoke debug analysis |

---

## File-count reconciliation

```
   §1 Pre-AMT historical:           13 files
   §2 Phase 1 / Composite:          12 files
   §3 Phase 2 / Mode A depth:       10 files (mode-a-D4 also in §5)
   §4 Phase 3 / C.2:                 2 files
   §5 Phase 4 / DOM signatures:      2 files (one shared with §3)
   §6 Phase 5 / Smoker:              3 files
   §7 Phase 6 / Stage 3:             0 files (lives in results/stage3/)
   §8 Phase 6 / Stage 4b:            4 files
   §9 Sundry / smoke:                3 files
   ────────────────────────────────────────
   Total unique:                    48 files (cross-references = +1)
```

---

## Maintenance

- When a new analysis report lands here, classify it into one of §1–§9.
- Banner stale files when their data version is superseded (e.g. C.2's
  "2,188" → "2,184" in 2026-05-15).
- Don't move files into stage subdirectories — breaks git blame, breaks
  cross-references in trace reports.
