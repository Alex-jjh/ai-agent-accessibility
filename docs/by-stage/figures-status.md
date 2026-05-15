# Figure Status Inventory (paper rebuild)

> Inventory of every paper figure: where it lives, what data it depends on,
> and what its status is post-2026-05-15 V&V audit. **User will redraw all
> figures separately**; this doc is a checklist of which to refresh and why.

## Status legend

| Status | Meaning |
|---|---|
| ✅ **OK** | data unchanged since v1; current PNG still accurate |
| 🔄 **REFRESH** | data source updated (Stage 3 supersedes Mode A); regenerate from current CSV |
| ⚠️ **REVIEW** | conceptual figure; paper text changed → caption/labels may need update |
| 🆕 **REDRAW** | major change needed (Stage 3 overlay, caption rewording, etc.) |
| 📁 **SUPPLEMENTARY** | generated but unused in main paper; candidate for supplementary materials |

---

## Paper-referenced (10 figures)

These appear via `\includegraphics` in `main.tex` or `sections/*.tex`.

### Conceptual figures (no data dependency)

| Figure | Status | Action needed |
|---|---|---|
| `F1_amt_framework.png` (intro) | ⚠️ REVIEW | Caption uses N=14,772 / 2,188 (now 14,768 / 2,184). User redraws + caption update. |
| `figure3_three_agent_arch.png` (§4) | ✅ OK | Pure architecture diagram; no N or rate. |
| `figure3_severity_framework.png` (§4) | ⚠️ REVIEW | Tier 1/2/3 framework; check for any "L1/L2/L3 tier" residual labels (was renamed). |
| `figureA1_full_layer_architecture.png` (appendix) | ✅ OK | Architecture diagram; no data values. |

### Auto-generated figures

| Figure | Status | Generator | Data source | Action needed |
|---|---|---|---|---|
| `F4_behavioral_drop.png` (§5.1) | 🔄 REFRESH | `figures/generate_F4_behavioral_drop.py` | `results/stage3/per-operator-stage3.csv` (P0 archival switched to Stage 3) | Re-run generator with current Stage 3 data; verify L1=−28pp / L9=−12.7pp / L5=−11.3pp / L12=−7.8pp ranking; 22 NS operators clustered. |
| `F6_alignment_scatter.png` (§5.2) | 🆕 REDRAW | `figures/generate_F6_alignment_scatter.py` | `results/amt/{dom_signature_matrix,behavioral_signature_matrix}.csv` | Currently uses Mode A behavioral data only. Should overlay Stage 3 drops to match paper's "breadth/depth" framing. ρ = 0.426 NS already verified. |
| `F8_composition.png` (§5.4) | 🔄 REFRESH | `figures/generate_F8_composition.py` | `results/amt/statistics_report.md` § Composition (15 super-additive / 9 additive / 4 sub-additive) | Verify all 28 pairs labeled; binomial p=0.019; L11+L6=+24.1pp interaction is the visual anchor. |
| `F11_task_funnel.png` (§4) | ✅ OK | `figures/generate_F11_task_funnel.py` | `results/smoker/{passing-tasks.json, exclusion-report.md}` | Phase 5 unchanged. Caption: ensure 5/13 Mode A convergence detail (not 10/13). |
| `figure5_causal_decomposition.png` (§5.1) | ✅ OK | (presumably manual) | `results/bootstrap_decomposition.csv` | Functional 35.4 [15.4, 55.4] / semantic 20.0 [-13.8, 52.3] — unchanged. |
| `figure6_token_violin.png` (§5.1) | 🔄 REFRESH | (manual / matplotlib) | per-case tokens from `combined-experiment.csv` | Caption: paper now says "Mann-Whitney U p ≈ 1.3e-4" (was "Wilcoxon p<10⁻⁶"). Figure itself OK — distribution unchanged; only the annotation. |

---

## Generated but NOT paper-referenced (5 figures)

These exist in `figures/` (and copies in `paper/`) but are not `\includegraphics`d.

| Figure | Status | Generator | Notes |
|---|---|---|---|
| `F2_injection.png` | 📁 SUPPLEMENTARY | (manual GPT/Image2) | Concept of variant injection; could be supplementary or remove |
| `F3_page_variant.png` | 📁 SUPPLEMENTARY | (manual) | Side-by-side base vs low; supplementary candidate |
| `F5_dom_heatmap.png` | 📁 SUPPLEMENTARY | `figures/generate_F5_dom_heatmap.py` | Per-op × DOM-dim heatmap; uses Mode A — would need Stage 3 overlay if added to paper |
| `F7_cross_model.png` | 📁 SUPPLEMENTARY | `figures/generate_F7_cross_model.py` | Cross-model comparison; uses Mode A — would need Stage 3 numbers |
| `F9_task_heatmap.png` | 📁 SUPPLEMENTARY | `figures/generate_F9_task_heatmap.py` | Per-task × per-op heatmap; Mode A only |

User decision: include in supplementary materials package, or delete.

---

## Files inventory

```
figures/                                 ← in ai-agent-accessibility repo
├── generate_F11_task_funnel.py
├── generate_F4_behavioral_drop.py
├── generate_F5_dom_heatmap.py
├── generate_F6_alignment_scatter.py
├── generate_F7_cross_model.py
├── generate_F8_composition.py
├── generate_F9_task_heatmap.py
└── generate_figure2.py                  ← legacy

paper/                                   ← in paper repo
├── F1_amt_framework.png
├── F2_injection.png
├── F3_page_variant.png
├── F4_behavioral_drop.png
├── F5_dom_heatmap.png
├── F6_alignment_scatter.png
├── F7_cross_model.png
├── F8_composition.png
├── F9_task_heatmap.png
├── F11_task_funnel.png
├── figure3_severity_framework.png
├── figure3_three_agent_arch.png
├── figure5_causal_decomposition.png
├── figure6_token_violin.png
├── figureA1_full_layer_architecture.png
├── figure4_main_results.png             ← unreferenced, possibly stale
└── table2_per_task_heatmap.png          ← unreferenced
```

## Workflow

User-led:

1. Decide which 🔄 REFRESH figures need full redraw vs minor caption tweak.
2. For 🆕 REDRAW (F6 alignment scatter), decide breadth-vs-depth overlay style.
3. Re-run any auto-generators that the user wants to keep:
   ```sh
   PYTHON=python3 python3 figures/generate_F4_behavioral_drop.py
   # etc.
   ```
4. Replace the corresponding `paper/*.png` with new files.
5. Update captions in `paper/sections/*.tex` if any numerical claim moved.
6. `cd paper && latexmk -pdf main.tex` → confirm new PDF.
7. Run `make pre-submit` again to confirm V&V still GREEN.

## Number-to-figure cross-reference

For convenience when redrawing:

| Number | Source | Used in figure(s) |
|---|---|---|
| 14,768 cases (total) | `_constants.N_TOTAL` | F1 caption (if mentioned) |
| 1,040 composite | `_constants.N_COMPOSITE` | F1, figure5 caption |
| 4,056 Mode A | `_constants.N_MODE_A` | F1, figure5 caption |
| 7,488 Stage 3 | `_constants.N_STAGE3` | F4 (data), F1 caption |
| 2,184 C.2 | `_constants.N_C2` | F8 (data), F1 caption |
| 9,408 SSIM PNGs | `_constants.N_STAGE4B_CAPTURES` | F1 caption |
| L1 −28.0pp Claude breadth | per-operator-stage3.csv | F4, F6 |
| L11 +2.3pp Claude / −14.1pp Llama 4 | per-operator-stage3.csv | F4, F7 |
| 15/28 super-additive | majority_vote… or stats report | F8 |
| 5/13 Mode A 7-gate convergence | task-selection-methodology §8.1 | F11 caption |
| ρ = 0.426 alignment Spearman | stage3_statistics output | F6 caption |
| Token: 97K low / 40K base, 2.4× | composite stats | figure6_token_violin |
| Bootstrap: functional 35.4 [15.4, 55.4] / semantic 20.0 [-13.8, 52.3] | bootstrap_decomposition.csv | figure5_causal_decomposition |

## Maintenance

When a figure is redrawn:

1. Replace PNG in `paper/`.
2. If caption changes, update `paper/sections/*.tex`.
3. Run `make pre-submit` — verify-all should still PASS (data didn't move).
4. Note in this file: change status to ✅ OK with date.

When a new auto-figure is added:

1. Generator under `figures/`.
2. Output PNG to `paper/`.
3. Add row to "Paper-referenced" or "Supplementary" table above.
4. If it depends on `_constants.py` values, document the dependency in
   the cross-reference table.
