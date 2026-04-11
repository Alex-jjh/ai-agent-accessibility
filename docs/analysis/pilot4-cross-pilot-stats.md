# Cross-Pilot Statistical Comparison: Pilot 3a vs Pilot 4

**Purpose:** Verify that the core accessibility-performance gradient replicates
across independent experimental runs with different variant injection mechanisms.

## 1. Per-Variant Success Rates

| Variant | Pilot 3a | Pilot 4 (text) | Pilot 4 (vision) | Δ (3a vs 4-text) |
|---------|----------|----------------|------------------|------------------|
| low | 2/6 (33.3%) | 1/6 (16.7%) | 0/6 (0.0%) | -16.7pp |
| medium-low | 4/6 (66.7%) | 6/6 (100.0%) | 1/6 (16.7%) | +33.3pp |
| base | 6/6 (100.0%) | 5/6 (83.3%) | 1/6 (16.7%) | -16.7pp |
| high | 6/6 (100.0%) | 4/6 (66.7%) | 1/6 (16.7%) | -33.3pp |

## 2. Primary Statistical Tests

### Pilot 4: Low vs Base (text-only)

- Low: 1/6 (16.7%)
- Base: 5/6 (83.3%)
- χ²=5.33, p=0.021, Cramér's V=0.667
- Fisher's exact p=0.080
- OR=0.07 (95% CI: 0.01–0.96)
- Cohen's h=-1.459 (large)

### Pilot 3a: Low vs Base (text-only)

- Low: 2/6 (33.3%)
- Base: 6/6 (100.0%)
- χ²=6.00, p=0.014, Cramér's V=0.707
- Fisher's exact p=0.061
- OR=0.04 (95% CI: 0.00–1.12)
- Cohen's h=-1.847 (large)

## 3. Cochran-Armitage Trend Test

**Pilot 4 (text-only):** Z=1.549, p=0.121
**Pilot 3a:** Z=2.951, p=0.003

## 4. Pairwise Effect Sizes (Cohen's h)

| Comparison | Pilot 3a h | Pilot 4 h | Interpretation |
|------------|-----------|-----------|----------------|
| low vs medium-low | -0.680 | -2.237 | large |
| low vs base | -1.847 | -1.459 | large |
| low vs high | -1.847 | -1.070 | large |
| medium-low vs base | -1.168 | +0.778 | large |
| base vs high | +0.000 | +0.390 | small |

## 5. Breslow-Day Test (Homogeneity of ORs across tasks)

- Statistic=0.00, df=5, p=1.000
- **Homogeneous:** Effect size is consistent across tasks

## 6. Sensitivity Analysis (excluding reddit:67)

- Low (excl 67): 1/5 (20.0%)
- Base (excl 67): 5/5 (100.0%)
- χ²=6.67, p=0.010, V=0.816
- **Still significant:** YES

## 7. Interaction Effect: Text-Only vs Vision-Only

- Text-only gradient (base-low): 66.7pp
- Vision-only gradient (base-low): 16.7pp
- **Interaction:** 50.0pp

Text-only shows a substantially larger gradient than vision-only,
supporting the a11y tree as the primary causal mechanism.

## 8. Summary for Paper

| Metric | Pilot 3a | Pilot 4 |
|--------|----------|---------|
| Overall text-only | 75.0% | 66.7% |
| Low rate | 33.3% | 16.7% |
| Base rate | 100.0% | 83.3% |
| Low vs Base χ² | 6.00 | 5.33 |
| Low vs Base p | p=0.014 | p=0.021 |
| Cramér's V | 0.707 | 0.667 |
