# Statistical Analysis Plan — CHI 2027

## Data Structure

- N=1,040 cases (binary outcome: success/failure)
- IV: variant (ordinal, 4 levels: low=0, ml=1, base=2, high=3)
- Grouping: task (13 levels), agent_type (3 levels), model (2 levels)
- 5 repetitions per cell

## Pre-Registration of Endpoints

Primary and secondary endpoints were defined prior to statistical analysis
(documented in this file and in the research proposal v6.2).

**Primary endpoint**: Cochran-Armitage trend test on text-only Claude (13 tasks,
4 ordered variants, binary success). This is the single pre-specified test that
requires no multiple comparison correction.

**Secondary endpoints** (exploratory, Bonferroni-corrected where applicable):
- Cross-model replication (Llama 4 Cochran-Armitage)
- Cross-architecture replication (CUA, SoM Cochran-Armitage)
- GEE mixed-effects models (variant as continuous predictor)
- Interaction effects (agent × variant, model × variant)
- Sensitivity analyses (exclude infeasible tasks, exclude reddit:67)

All other pairwise comparisons are exploratory and reported with both
uncorrected and Bonferroni-corrected p-values.

## Analysis Hierarchy (from simple to complex)

### Level 1: Descriptive Statistics
- Task × Variant × Agent success rate matrix
- Per-variant aggregate success rates with 95% Wilson CIs
- Token consumption by variant (mean, median, IQR)
- Failure type distribution by variant and agent

### Level 2: Pairwise Comparisons (Primary Evidence)

**2a. χ² tests with Fisher's exact (small cells)**
- Primary: low vs base, per agent type
- Secondary: all pairwise variant comparisons
- Effect size: Cramér's V
- Multiple comparison correction: Bonferroni (6 pairwise × 3 agents = 18 tests)

**2b. Cochran-Armitage trend test**
- Tests for monotonic trend in success proportion across ordered variant levels
- More powerful than χ² when ordinal structure is expected
- One test per agent type (3 tests total)
- This is the IDEAL test for our design: binary outcome × ordinal IV

### Level 3: Mixed-Effects Models (Accounting for Clustering)

**3a. GLMM (Generalized Linear Mixed Model)**
- DV: success (binary, Bernoulli)
- Fixed effects: variant_ordinal (linear trend)
- Random intercepts: (1|task_id) — accounts for task difficulty variation
- Link: logit
- Library: statsmodels BinomialBayesMixedGLM or GEE fallback
- This is the gold standard for clustered binary data in HCI

**3b. GEE (Generalized Estimating Equations)**
- Same specification as GLMM but population-averaged (not subject-specific)
- Exchangeable correlation structure, clustered on task_id
- More robust to misspecification of random effects distribution
- Report both GLMM and GEE; if they agree, results are robust

### Level 4: Interaction Effects

**4a. Agent type × Variant interaction**
- Tests whether the a11y gradient differs across agent types
- Expected: text-only shows strongest gradient, CUA moderate, SoM weakest
- Fixed: variant_ordinal + agent_type + variant_ordinal:agent_type
- Random: (1|task_id)

**4b. Model × Variant interaction (text-only only)**
- Tests whether Claude vs Llama 4 show different gradients
- Fixed: variant_ordinal + model + variant_ordinal:model
- Random: (1|task_id)

### Level 5: Sensitivity Analyses

**5a. Excluding infeasible tasks at low**
- Re-run Level 2-3 excluding tasks where low is structurally infeasible
- If effect persists → a11y degrades even feasible tasks

**5b. Excluding reddit:67 (context overflow confound)**
- reddit:67 has base<ml due to context overflow, not a11y
- Re-run to check robustness

**5c. Token consumption analysis**
- Wilcoxon rank-sum: low vs base tokens (non-parametric, skewed distribution)
- Linear mixed model: log(tokens) ~ variant + (1|task_id)

### Level 6: Cross-Model Replication

**6a. Breslow-Day test for homogeneity of odds ratios**
- Tests whether the low-vs-base OR is consistent across Claude and Llama 4
- If p>0.05 → effect is homogeneous across models (good for generalizability)

**6b. Mantel-Haenszel combined OR**
- Pooled odds ratio across models, stratified by task
- More powerful than separate per-model tests

## Implementation Notes

### Python Libraries
- scipy.stats: χ², Fisher's exact, Cochran-Armitage, Wilcoxon, Breslow-Day
- statsmodels: GEE, GLM, BinomialBayesMixedGLM
- numpy/pandas: data manipulation
- No R dependency (avoid pymer4/lme4 complexity)

### Cochran-Armitage Implementation
scipy.stats doesn't have Cochran-Armitage directly. Implement manually:
- Z = Σ(ti × ni1) - n1 × Σ(ti × ni) / n
- Variance from null hypothesis
- Or use proportions_ztest with trend weights

### Multiple Comparison Strategy
- Primary comparison (low vs base): no correction needed (pre-specified)
- All pairwise: Bonferroni correction
- Report both corrected and uncorrected p-values

### Reporting Standards (APA/CHI)
- Report: test statistic, df, p-value, effect size, 95% CI
- For χ²: χ²(df, N=n) = X.XX, p = .XXX, V = .XX
- For GLMM: β = X.XX, SE = X.XX, z = X.XX, p = .XXX, OR = X.XX [CI]
- For Cochran-Armitage: Z = X.XX, p = .XXX (one-sided for monotonic trend)
