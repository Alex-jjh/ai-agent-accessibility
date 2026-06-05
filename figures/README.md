# Paper Figures — CHI/ASSETS 2027 AMT Submission

**Unified numbering (2026-06-05).** Figures are now named `fig1`–`fig10` by
their order of appearance in the paper, plus `figA1` for the appendix. The old
mixed scheme (`F1`/`F4`/`figure3_`/`figureA1`) is retired; superseded files are
in `archive/`.

`paper/figN_*.png` is what the PDF pulls in; the platform copy under
`figures/` is the source. Data figures regenerate from CSVs; conceptual figures
are GPT-Image or hand-drawn and regenerate manually.

## Figure inventory (in paper order)

| Fig | Paper § | Title | Source | Generator | Data freshness | Owner to refresh |
|----|---------|-------|--------|-----------|----------------|------------------|
| **fig1** | §1 intro | AMT framework teaser | GPT-Image | `prompts/F1_amt_framework.md` | conceptual | **USER** — prompt updated to 2/13/9/2 (42%) + "10 High"; re-prompt & drop in `paper/fig1_amt_framework.png` |
| **fig2** | §4 | Three-agent architecture | legacy matplotlib | `archive/generate_figure3_simplified.py` | conceptual, OK | none (stable) |
| **fig3** | §4 | Task-selection funnel 684→48 | matplotlib | `generate_fig3_task_funnel.py` | current (smoker) | none (verified) |
| **fig4** | §4 | Severity Tier 1/2/3 framework | legacy matplotlib | `archive/generate_remaining_figures.py` | **STALE** | **USER** — shows old "L1/L2/L3" labels + 83.3%/30-site; must say Tier 1/2/3 + 82.4%/28-of-34 |
| **fig5** | §5.1 | Causal decomposition schematic | hand-drawn | none | **STALE** | **USER** — "Δ23pp"→20.0pp, drop "L3" label, add CIs |
| **fig6** | §5.1 | Token-inflation violin | matplotlib (no committed script) | — | current, OK | none (pixels correct: 103K/42K/2.4×) |
| **fig7** | §5.1 | Per-operator behavioral drop | matplotlib | `generate_fig7_behavioral_drop.py` | **FIXED → current Stage 3** | done (was crashing; now reads stage3 CSV, L1=−28pp) |
| **fig8** | §5.2 | Signature alignment scatter | matplotlib | `generate_fig8_alignment_scatter.py` | **FIXED → 42.3%** | done (was rendering a wrong 12/26; now 2/13/9/2 = 11/26) |
| **fig9** | §5.4 | Compositional super-additivity | matplotlib | `generate_fig9_composition.py` | **FIXED → 15/9/4** | done (was hardcoded 14/9/5; now computed live, p=0.019) |
| **fig10** | §5.3 | Cross-model Claude vs Llama 4 | matplotlib | `generate_fig10_cross_model.py` | **NEW, promoted to main** | done (Stage 3; L11 +2.3 vs +14.1; Sonnet 4 label) |
| **figA1** | App. B | Full layer architecture | legacy matplotlib | `archive/generate_figure5.py` (renamed) | **STALE** | **USER** — "Sonnet 3.5"→Sonnet 4, Pilot-4 rates, "63.3pp" decomposition all stale |

## Data-figure regeneration

All data figures read from `results/` and are reproducible:

```bash
python3 figures/generate_fig3_task_funnel.py       # → fig3 (smoker funnel)
python3 figures/generate_fig7_behavioral_drop.py   # → fig7 (Stage 3 per-op drop)
python3 figures/generate_fig8_alignment_scatter.py # → fig8 (alignment 42.3%)
python3 figures/generate_fig9_composition.py       # → fig9 (15/9/4 super-additive)
python3 figures/generate_fig10_cross_model.py      # → fig10 (cross-model gap)
# then copy figures/figN_*.{png,pdf} into paper/
```

`fig7` and `fig10` depend on `results/stage3/cross-model-stage3.csv`, emitted by:

```bash
python3 -m analysis.stage3_statistics   # writes per-operator + cross-model CSVs
```

## Conceptual / hand-drawn figures (USER regenerates)

- **fig1** (GPT-Image): prompt at `prompts/F1_amt_framework.md` — already updated
  to the corrected alignment counts. Re-run through GPT Image 2, sanity-check
  glyphs, save as `paper/fig1_amt_framework.png`.
- **fig4, fig5, figA1**: legacy/hand-drawn with stale embedded numbers (see the
  STALE rows above). Either redraw in a vector editor or re-script. The corrected
  values they must show:
  - fig4 severity: Tier 1/2/3 (not L1/L2/L3); Tier-3 prevalence **82.4% (28/34)**.
  - fig5 causal: functional **35.4pp [15.4,55.4]**, semantic **20.0pp [−13.8,52.3]**,
    text-only total **55.4pp**; label "Tier 3 Structural" (not "L3"); show CIs.
  - figA1: model **Claude Sonnet 4**; composite low rates text-only **38.5%** /
    SoM **4.6%** / CUA **58.5%**; decomposition **55.4pp = 35.4 functional + 20.0 semantic**.

## Supplementary candidates (generated, NOT in PDF)

Kept under their old names; promote/drop per the user's call. All Mode-A based.

- `F5_dom_heatmap.{png,pdf}` (+ `generate_F5_dom_heatmap.py`) — 26-op × DOM-dim heatmap.
- `F9_task_heatmap.{png,pdf}` (+ `generate_F9_task_heatmap.py`) — per-task × per-op heatmap.
- `F1_amt_framework_gpt_v1.png`, `F2_injection_gpt_v1.png`, `F3_page_variant_gpt_v1.png`
  — GPT-Image concept figures; F2/F3 prompts in `prompts/`.

## Style guide

- Font DejaVu Sans 8pt base (matplotlib); DPI 300 raster, vector PDF preferred.
- Family colors: Low `#C0392B`, Midlow `#E67E22`, High `#27AE60`, base/neutral `#2471A3`.
- CHI column width: single 3.33", double 7". Min 7pt at print size. No chartjunk.

## archive/

Superseded scripts and renders (pre-unification or pre-data-correction):
old `generate_F4/F6/F7/F8_*.py` and their renders, `generate_figure2.py`,
`figure2_main_results.png`, plus the pre-AMT severity/layer figures.
