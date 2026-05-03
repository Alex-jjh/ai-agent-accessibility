# analysis/archive/ — Historical Pilot & Expansion Analysis

These scripts generated analysis reports for earlier experimental iterations
(Pilots 3b, 4, and the task expansion batch). Their outputs are preserved in
`docs/analysis/` as permanent records; the scripts themselves are retained
here for reproducibility.

## Why archived

All of these scripts:
1. Ran against pilot/expansion data (pre-AMT framing)
2. Produced one-off analysis reports that are now finalized in `docs/analysis/`
3. Are not part of the active CHI 2027 AMT paper pipeline

The current AMT paper pipeline uses scripts in `analysis/` (root) and
`scripts/amt/` — see `analysis/README.md` for the active taxonomy.

## What's here

### Pilot 3b (120+120 cases, text-only + vision-only)
- `pilot3b_190_analysis.py` — original Pilot 3b analysis (N=190 before re-run)

### Pilot 4 (240 text+SoM + 120 CUA)
- `pilot4_analysis.py` — canonical Pilot 4 analysis (Plan D variant injection)
- `pilot4_cross_pilot_stats.py` — Pilot 3a vs Pilot 4 statistical comparison
- `pilot4_deep_dives.py` — 6 targeted trace-level investigations
- `pilot4_token_analysis.py` — token inflation analysis (ISSUE-BR-4)

### Expansion batch (7 new tasks × 4 variants × 5 reps × 4 agents)
- `expansion_smoke_comparison.py` — SoM vs CUA smoke test comparison
- `expansion_som_full_deep_dive.py` — all 140 SoM traces, 5 failure modes
- `expansion_cua_full_deep_dive.py` — all 140 CUA traces classified
- `expansion_cross_agent_comparison.py` — 4-agent comparison across 7 tasks

## How to re-run

If needed for regression testing or extended analysis:

```bash
# Activate the analysis venv
source analysis/.venv/bin/activate

# Run an archived script (note the archive/ path)
python3 analysis/archive/pilot4_analysis.py
```

## Active analysis pipeline

See `analysis/README.md` for the current active scripts:
- Paper-wide statistics (`run_statistics.py`, `compute_primary_stats.py`)
- Cross-model tests (`breslow_day.py`)
- Causal decomposition (`bootstrap_decomposition.py`)
- GLMM mixed-effects modeling (`glmm_analysis.py`)
- Visual equivalence (`visual_equivalence_analysis.py`, `visual_equivalence_gallery.py`)
- Data verification (`verify_all_data_points.py`, `paper_consistency_audit.py`)
- Human baseline (`griffith_triangulation.py`)
- Semantic density metric (`semantic_density.py`)
- SSIM helper (`ssim_helper.py`)
- CUA failure validation (`cua_failure_trace_validation.py`)
- Majority vote sensitivity (`majority_vote_sensitivity.py`)
- Combined data export (`export_combined_data.py`)
- Results table generation (`generate_results_tables.py`)
