# Level 1: Descriptive Statistics

## 1a. Success Rates by Variant (all agents combined)

Variant         Success  Total     Rate           95% CI
low                  90    260   34.6% [0.291, 0.406]
medium-low          187    260   71.9% [0.662, 0.770]
base                186    260   71.5% [0.658, 0.767]
high                190    260   73.1% [0.674, 0.781]

## 1b. Success Rates by Agent Type × Variant


### cua (N=260)
  low                   38/65 (58.5%) [0.463, 0.696]
  medium-low            64/65 (98.5%) [0.918, 0.997]
  base                  61/65 (93.8%) [0.852, 0.976]
  high                  62/65 (95.4%) [0.873, 0.984]

### text-only (N=520)
  low                  49/130 (37.7%) [0.298, 0.463]
  medium-low          105/130 (80.8%) [0.732, 0.866]
  base                107/130 (82.3%) [0.748, 0.879]
  high                107/130 (82.3%) [0.748, 0.879]

### vision-only (N=260)
  low                     3/65 (4.6%) [0.016, 0.127]
  medium-low            18/65 (27.7%) [0.183, 0.396]
  base                  18/65 (27.7%) [0.183, 0.396]
  high                  21/65 (32.3%) [0.222, 0.444]

## 1c. Success Rates by Model × Variant (text-only only)


### claude-sonnet (N=260)
  low                   25/65 (38.5%) [0.276, 0.506]
  medium-low           65/65 (100.0%) [0.944, 1.000]
  base                  61/65 (93.8%) [0.852, 0.976]
  high                  58/65 (89.2%) [0.794, 0.947]

### llama4-maverick (N=260)
  low                   24/65 (36.9%) [0.262, 0.491]
  medium-low            40/65 (61.5%) [0.494, 0.724]
  base                  46/65 (70.8%) [0.588, 0.804]
  high                  49/65 (75.4%) [0.637, 0.842]

## 1d. Token Consumption by Variant

Variant              Mean     Median              IQR
low               177,363     96,848 [48,433, 310,134]
medium-low         87,569     50,268 [26,672, 105,657]
base              103,334     51,826 [22,926, 115,843]
high              109,373     57,104 [24,954, 114,251]


# Level 2: Pairwise Comparisons

## 2a. Low vs Base — Primary Comparison

  cua (all models):
    low=38/65 (58.5%), base=61/65 (93.8%)
    χ²=22.41, p=0.000002, Fisher p=0.000003, V=0.415, OR=0.09 [0.03,0.28] ***
  cua / claude-sonnet:
    low=38/65 (58.5%), base=61/65 (93.8%)
    χ²=22.41, p=0.000002, Fisher p=0.000003, V=0.415, OR=0.09 [0.03,0.28] ***
  text-only (all models):
    low=49/130 (37.7%), base=107/130 (82.3%)
    χ²=53.91, p=<0.000001, Fisher p=<0.000001, V=0.455, OR=0.13 [0.07,0.23] ***
  text-only / claude-sonnet:
    low=25/65 (38.5%), base=61/65 (93.8%)
    χ²=44.52, p=<0.000001, Fisher p=<0.000001, V=0.585, OR=0.04 [0.01,0.13] ***
  text-only / llama4-maverick:
    low=24/65 (36.9%), base=46/65 (70.8%)
    χ²=14.98, p=0.000109, Fisher p=0.000194, V=0.339, OR=0.24 [0.12,0.50] ***
  vision-only (all models):
    low=3/65 (4.6%), base=18/65 (27.7%)
    χ²=12.78, p=0.000351, Fisher p=0.000559, V=0.314, OR=0.13 [0.04,0.45] ***
  vision-only / claude-sonnet:
    low=3/65 (4.6%), base=18/65 (27.7%)
    χ²=12.78, p=0.000351, Fisher p=0.000559, V=0.314, OR=0.13 [0.04,0.45] ***

## 2b. All Pairwise Comparisons (Bonferroni corrected)

  low vs medium-low: χ²=57.78, p=<0.000001, Bonferroni p=<0.000001
  low vs base: χ²=44.52, p=<0.000001, Bonferroni p=<0.000001
  low vs high: χ²=36.29, p=<0.000001, Bonferroni p=<0.000001
  medium-low vs base: χ²=4.13, p=0.0422, Bonferroni p=0.253
  medium-low vs high: χ²=7.40, p=0.0065, Bonferroni p=0.0392
  base vs high: χ²=0.89, p=0.344, Bonferroni p=1.000

## 2c. Cochran-Armitage Trend Test

  cua (all models): Z=5.607, p=<0.000001 ***
  cua / claude-sonnet: Z=5.607, p=<0.000001 ***
  text-only (all models): Z=7.589, p=<0.000001 ***
  text-only / claude-sonnet: Z=6.635, p=<0.000001 ***
  text-only / llama4-maverick: Z=4.609, p=0.000004 ***
  vision-only (all models): Z=3.555, p=0.000378 ***
  vision-only / claude-sonnet: Z=3.555, p=0.000378 ***


# Level 3: GEE Mixed-Effects Models


## All agents (text-only Claude) (N=260)

            const: β=nan, SE=nan, z=nan, p=nan, OR=nan [nan, nan]
         _variant: β=nan, SE=nan, z=nan, p=nan, OR=nan [nan, nan]
  Correlation: nan

## Text-only Llama 4 (N=260)

            const: β=-0.168, SE=0.394, z=-0.43, p=0.669, OR=0.84 [0.39, 1.83]
         _variant: β=0.563, SE=0.233, z=2.41, p=0.0158, OR=1.76 [1.11, 2.78]
  Correlation: 0.548

## Vision-only (SoM) (N=260)

            const: β=-1.916, SE=0.349, z=-5.49, p=<0.000001, OR=0.15 [0.07, 0.29]
         _variant: β=0.479, SE=0.140, z=3.43, p=0.000597, OR=1.61 [1.23, 2.12]
  Correlation: 0.303

## CUA (N=260)

            const: β=nan, SE=nan, z=nan, p=nan, OR=nan [nan, nan]
         _variant: β=nan, SE=nan, z=nan, p=nan, OR=nan [nan, nan]
  Correlation: nan

## All text-only (both models) (N=520)

            const: β=0.363, SE=0.353, z=1.03, p=0.305, OR=1.44 [0.72, 2.87]
         _variant: β=0.791, SE=0.339, z=2.34, p=0.0195, OR=2.21 [1.14, 4.28]
  Correlation: 0.247


# Level 4: Interaction Effects

## 4a. Agent Type × Variant Interaction (text-only vs CUA, Claude)

            const: β=-79856138335298487582720.000, SE=0.000, p=<0.000001
         _variant: β=204.517, SE=0.000, p=<0.000001
         _is_text: β=79856129046624256131072.000, SE=0.000, p=<0.000001
     _interaction: β=-84.850, SE=0.000, p=<0.000001

  Interaction p=<0.000001 → Significant

## 4b. Model × Variant Interaction (Claude vs Llama 4, text-only)

            const: β=nan, SE=nan, p=nan
         _variant: β=nan, SE=nan, p=nan
       _is_claude: β=nan, SE=nan, p=nan
     _interaction: β=nan, SE=nan, p=nan


# Level 5: Sensitivity Analyses

## 5a. Excluding Low-Infeasible Tasks (23,24,26,198,293,308)

  Feasible only: low=24/35 (68.6%), base=31/35 (88.6%)
  χ²=4.16, p=0.0414, V=0.244

## 5b. Excluding reddit:67 (context overflow confound)

  No reddit:67: low=23/60 (38.3%), base=60/60 (100.0%)
  χ²=53.49, p=<0.000001, V=0.668

## 5c. Token Consumption: Low vs Base (Wilcoxon)

  cua: low median=371,494, base median=137,694, U=3173, p=<0.000001
  text-only: low median=97,480, base median=39,740, U=11628, p=<0.000001
  vision-only: low median=54,083, base median=46,760, U=2210, p=0.652


# Level 6: Cross-Model Replication

Common tasks: [np.int64(4), np.int64(23), np.int64(24), np.int64(26), np.int64(29), np.int64(41), np.int64(67), np.int64(94), np.int64(132), np.int64(188), np.int64(198), np.int64(293), np.int64(308)] (13 tasks)

## 6a. Per-Model Low vs Base (common tasks only)

  claude-sonnet: low=25/65 (38.5%), base=61/65 (93.8%)
    χ²=44.52, p=<0.000001, V=0.585, OR=0.04 [0.01,0.13]
  llama4-maverick: low=24/65 (36.9%), base=46/65 (70.8%)
    χ²=14.98, p=0.000109, V=0.339, OR=0.24 [0.12,0.50]

## 6b. Cross-Model OR Comparison

  Claude OR (low vs base) = 0.04
  Llama 4 OR (low vs base) = 0.24
  Both models show low < base → effect generalizes across model families