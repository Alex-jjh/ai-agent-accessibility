# Key Numbers — Single Source of Truth for Paper

All numbers in the paper MUST reference this file. Generated from
`results/combined-experiment.csv` via `analysis/verify_all_data_points.py`.

Last verified: 2026-04-14

## Experiment Design

- Total cases: **N=1,040**
- Tasks: **13** (4 apps, 11 templates, 5 shallow / 5 medium / 3 deep)
- Variants: **4** (low, medium-low, base, high)
- Agent types: **3** (text-only, vision-only/SoM, CUA)
- Models: **2** (Claude Sonnet, Llama 4 Maverick)
- Repetitions: **5** per cell

## Task Selection Funnel

- WebArena v1.0 pool: **812** tasks
- Stage 1 (site availability): **684** remaining (excluded map=112, wikipedia=16)
- Stage 2 (sole string_match eval): **231** remaining
- Stage 3 (info retrieval, manual review): **~210** remaining
- Stage 4 (ground truth stable, manual review): **~209** remaining
- Stage 5 (stratified sampling): **13** selected + 3 backups
- Stage 6 (smoke validation): **13** final (task 124 replaced by backup 188)
- All 13 tasks: sole eval_type = string_match (no mixed eval_types)

## Primary Statistical Results

### Cochran-Armitage Trend Test (pre-specified primary endpoint)
- Text-only Claude (13 tasks): **Z=6.635, p<0.000001**
- Text-only Llama 4: **Z=4.609, p=0.000004**
- CUA Claude: **Z=5.254, p<0.000001**
- SoM Claude: **Z=3.555, p=0.000378**

### Success Rates by Variant (text-only Claude, 13 tasks, n=65/variant)
- low: **25/65 (38.5%)**
- medium-low: **65/65 (100.0%)**
- base: **61/65 (93.8%)**
- high: **58/65 (89.2%)**

### Success Rates by Variant (text-only Llama 4, 13 tasks, n=65/variant)
- low: **24/65 (36.9%)**
- medium-low: **40/65 (61.5%)**
- base: **46/65 (70.8%)**
- high: **49/65 (75.4%)**

### Success Rates by Variant (CUA Claude, 13 tasks, n=65/variant)
- low: **38/65 (58.5%)**
- medium-low: **64/65 (98.5%)**
- base: **61/65 (93.8%)**
- high: **62/65 (95.4%)**

### Success Rates by Variant (SoM Claude, 13 tasks, n=65/variant)
- low: **3/65 (4.6%)**
- medium-low: **18/65 (27.7%)**
- base: **18/65 (27.7%)**
- high: **21/65 (32.3%)**

## Causal Decomposition (13 tasks, Claude only)

| Subset | Text drop | CUA drop | Semantic pathway |
|--------|-----------|----------|-----------------|
| All 13 tasks | **55.4pp** | **35.4pp** | **20.0pp** |
| Pilot 4 (6 tasks) | 63.3pp | 30.0pp | 33.3pp |
| Expansion (7 tasks) | 48.6pp | 40.0pp | 8.6pp |

**The one true number for the paper**: 20.0pp semantic pathway (all 13 tasks).

Interpretation: DOM semantic degradation independently contributes ~20pp to
agent failure, beyond the ~35pp from functional breakage (href removal).
The two pathways are comparable in magnitude, not one dominant and one minor.

## Cross-Model Replication

- Claude low vs base: chi2=44.52, p<0.000001, V=0.585, OR=0.04
- Llama 4 low vs base: chi2=14.98, p=0.000109, V=0.339, OR=0.24
- Both models: low < base (effect generalizes)

## Sensitivity Analyses

- Excluding low-infeasible tasks: chi2=4.16, **p=0.041**, V=0.244
- Excluding reddit:67: chi2=53.49, **p<0.000001**, V=0.668
- Token inflation (text-only): low median 97K vs base 40K, **p<0.000001**

## Base vs High (Asymmetric Effect)

- Claude 13-task: base **93.8%** vs high **89.2%** (4.6pp, not significant)
- Llama 4: base **70.8%** vs high **75.4%** (high > base, normal direction)
- Interpretation: asymmetric — degradation hurts significantly, enhancement
  provides marginal gain

## Correction Log

### 2026-04-14: Data audit corrections
| Claim | Old value | New value | Root cause |
|-------|-----------|-----------|------------|
| map tasks | 128 | **112** | Miscounted from task-site-mapping.json |
| Stage 1 output | 668 | **684** | Cascading from map count error |
| string_match tasks | 328 | **241** | Counted "includes SM" vs "primary SM" |
| Cochran-Armitage Z | 5.893 | **6.635** | Old: run_statistics.py on partial data; New: full 13-task |
| Text-only drop | 48.6pp | **55.4pp** | Old: expansion-only 7 tasks; New: all 13 tasks |
| CUA drop | 40.0pp | **35.4pp** | Old: expansion-only 7 tasks; New: all 13 tasks |
| Semantic pathway | 8.6pp | **20.0pp** | Composition effect: Pilot 4 tasks have more semantic-only degradation |

Root cause of 8.6→20 shift: NOT apples-to-oranges. Each subset used consistent
text/CUA comparison. The difference is task composition:
- Expansion 7 tasks: CUA low=51.4% (high functional breakage on admin/gitlab sidebar)
- Pilot 4 6 tasks: CUA low=66.7% (less functional breakage, more semantic-only)
- Combined: weighted average produces 20pp semantic pathway

## Authoritative Paper Values (whitelist for verify harness)

These are the ONLY numerical claims that should appear in paper/*.tex files.
Any value not on this list that looks like an experimental result is suspect.

### Experiment Design
- N=1,040 (total cases)
- 13 tasks
- 4 variants (low, medium-low, base, high)
- 3 agent types (text-only, vision-only/SoM, CUA)
- 2 models (Claude Sonnet, Llama 4 Maverick)
- 5 repetitions per cell

### Primary Endpoint
- Cochran-Armitage Z=6.635, p<10^-6 (text-only Claude)
- Cramér's V=0.585

### Success Rates (text-only Claude)
- low: 38.5%
- medium-low: 100.0%
- base: 93.8%
- high: 89.2%

### Success Rates (text-only Llama 4)
- low: 36.9%
- medium-low: 61.5%
- base: 70.8%
- high: 75.4%

### Success Rates (CUA Claude)
- low: 58.5%
- medium-low: 98.5%
- base: 93.8%
- high: 95.4%

### Success Rates (SoM Claude)
- low: 4.6%
- medium-low: 27.7%
- base: 27.7%
- high: 32.3%

### Causal Decomposition (all 13 tasks, Claude)
- Text-only drop: 55.4pp
- CUA drop: 35.4pp
- Semantic pathway: 20.0pp

### Step Function
- low → medium-low: +61.5pp (text-only Claude)

### Token Inflation
- low median: 97K
- base median: 40K
- extreme: 608K
- Wilcoxon p<10^-6

### Cross-Model
- Claude low vs base: chi2=44.52, p<10^-6, V=0.585, OR=0.04
- Llama 4 low vs base: chi2=14.98, p=0.000109, V=0.339, OR=0.24

### Asymmetric Effect
- base 93.8% vs high 89.2% (4.6pp, not significant)

### Ecological Validity
- 34 sites audited
- 83.3% with L3 structural violations

### Task Selection Funnel
- 812 total WebArena tasks
- 684 after Stage 1
- 231 sole string_match (Stage 2)
- 13 final tasks, 11 templates, 4 apps
- 5 shallow / 5 medium / 3 deep

### Forbidden Old Values (must NOT appear in paper)
- N=240 (old pilot-only sample size)
- N=360 (old pilot-only sample size)
- 86.7% / 23.3% (old text-only base/low)
- +76.7pp (old step function)
- 33.3pp / 30.0pp (old causal decomposition)
- 63.3pp / 48.6pp (old text-only drops)
- 8.6pp / 40.0pp (old semantic/CUA pathway)
- chi2=24.31 / V=0.637 (old chi-square test)
- 172K vs 135K (old token inflation)
- 6 tasks (old experiment design)
- 0% SoM success (old pilot-4-only SoM)

## Non-Monotonicity Detail (Task 67)

- task_67_claude_text_base_rate: **20% (1/5)**
- task_67_claude_text_ml_rate: **100% (5/5)**
- non_monotonic_task_count: **1 / 13** (task 67 only)
- Other 12 tasks: medium-low = base for Claude text-only (all 100%/100%)

## Majority-Vote Sensitivity

- Cells with between-rep variance: **48/208 (23.1%)**
- Claude text-only Low-vs-rest (majority vote): Z=4.005, **p=0.000062** (preserves)
- Claude CUA Low-vs-rest (majority vote): Z=3.474, **p=0.000513** (preserves)
