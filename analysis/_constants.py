"""
Single source of truth for paper-critical numbers.
=====================================================

Every N count, success rate, drop magnitude, or p-value cited in the paper
should be defined here and imported everywhere else (verifiers, stage
modules, paper_consistency_audit, etc.).

When a number changes:
  1. Update the constant here.
  2. Re-run `make verify-all` — failing assertions will surface every
     downstream location that needs updating.
  3. Re-run `latexmk` in paper/ to refresh PDF.

This file MUST NOT import from analysis/lib/, analysis/stages/, or any
other in-tree module — it should be importable in isolation.
"""

# ============================================================
# Stage / phase N counts
# ============================================================
# Phase 1 — Composite variant study (4 variants × 13 tasks × ...)
N_COMPOSITE = 1040          # after dedup (pilot4-cua/ecommerce_high_23 had 6 attempts on disk; export keeps first 5)

# Phase 2 — Mode A depth (13 tasks × 26 ops × 3 reps)
N_MODE_A_CLAUDE = 3042      # 3 archs × 26 ops × 13 tasks × 3 reps
N_MODE_A_LLAMA = 1014       # 1 arch  × 26 ops × 13 tasks × 3 reps
N_MODE_A = N_MODE_A_CLAUDE + N_MODE_A_LLAMA  # 4056

# Phase 3 — C.2 compositional study (28 pairs × 13 tasks × 2 archs × 3 reps)
N_C2 = 2184  # 28 × 13 × 2 × 3 = 2,184. NOTE: pre-2026-05-15 the paper / handoffs / docs misstated this as 2,188 due to an arithmetic error; data on disk has always been 2,184.

# Phase 4 — DOM signature audit
# (no case JSONs; per-URL audit JSON only)

# Phase 5 — Smoker (Stage 1 base-solvability gate)
N_SMOKER_SHARD_A = 1122     # shopping_admin (182) + shopping (192), each at base × text × 3 reps
N_SMOKER_SHARD_B = 930      # reddit (114) + gitlab (196), each at base × text × 3 reps
N_SMOKER = N_SMOKER_SHARD_A + N_SMOKER_SHARD_B  # 2052

SMOKER_TOTAL_TASKS = 684    # all deployed-app tasks (4 apps)
SMOKER_PASSING_TASKS = 48   # after 7-gate inclusion protocol
SMOKER_PASSING_BY_APP = {
    "ecommerce": 22,
    "ecommerce_admin": 12,
    "gitlab": 13,
    "reddit": 1,
}

# Phase 6 — Stage 3 breadth (48 tasks × 26 ops × 3 reps × 2 models)
N_STAGE3_CLAUDE = 3744
N_STAGE3_LLAMA = 3744
N_STAGE3 = N_STAGE3_CLAUDE + N_STAGE3_LLAMA  # 7488

# Phase 6 — Stage 4b SSIM trace-URL replay
N_STAGE4B_URLS = 336        # unique URLs from Stage 3 traces
N_STAGE4B_VARIANTS = 28     # base + base2 + 26 AMT operators
N_STAGE4B_CAPTURES = N_STAGE4B_URLS * N_STAGE4B_VARIANTS  # 9408

# Grand total
N_TOTAL = N_COMPOSITE + N_MODE_A + N_C2 + N_STAGE3  # 14,768
# (1,040 + 4,056 + 2,184 + 7,488 = 14,768. Paper said 14,772 pre-2026-05-15
# due to a +4 C.2 arithmetic typo combined with an earlier upstream off-by-one;
# corrected in commit "paper: correct N counts (14,772→14,768)".)

# ============================================================
# AMT operators (paper §3.1)
# ============================================================
LOW_OPS = [f"L{i}" for i in range(1, 14)]                          # L1..L13
MIDLOW_OPS = [f"ML{i}" for i in range(1, 4)]                       # ML1..ML3
HIGH_OPS = ["H1", "H2", "H3", "H4", "H5a", "H5b", "H5c", "H6", "H7", "H8"]
ALL_OPS = LOW_OPS + MIDLOW_OPS + HIGH_OPS                          # 26 operators
assert len(ALL_OPS) == 26

# ============================================================
# Paper claims — Phase 1 composite (§5.1)
# ============================================================
COMPOSITE_TEXT_ONLY_CLAUDE = {
    "low": 0.385,
    "medium-low": 1.000,
    "base": 0.938,
    "high": 0.892,
}
COMPOSITE_TEXT_ONLY_LLAMA = {
    "low": 0.369,
    "medium-low": 0.615,
    "base": 0.708,
    "high": 0.754,
}
COMPOSITE_CUA_CLAUDE = {
    "low": 0.585,
    "medium-low": 0.985,
    "base": 0.938,
    "high": 0.954,
}
COMPOSITE_SOM_CLAUDE = {
    "low": 0.046,
    "medium-low": 0.277,
    "base": 0.277,
    "high": 0.323,
}

# Cochran-Armitage trend test (composite, Claude text-only)
COMPOSITE_CA_Z_CLAUDE = 9.83
COMPOSITE_CA_P_THRESHOLD = 1e-19

# Token inflation (Wilcoxon, low vs base, Claude text-only)
COMPOSITE_TOKEN_LOW_MEDIAN = 97000
COMPOSITE_TOKEN_BASE_MEDIAN = 40000
COMPOSITE_TOKEN_INFLATION_RATIO = 2.4

# ============================================================
# Paper claims — Phase 6 Stage 3 (§5.1–5.3, primary breadth dataset)
# ============================================================
STAGE3_OVERALL_CLAUDE = 0.895
STAGE3_OVERALL_LLAMA = 0.674

# H-baseline (used as comparison for per-operator drop)
STAGE3_H_BASELINE_CLAUDE = 0.919

# Per-operator drops (breadth set, Claude text-only, vs H-baseline)
# Only operators significant after Holm-Bonferroni or otherwise cited
STAGE3_DROPS_BREADTH_CLAUDE = {
    "L1": -28.0,        # landmark→div, p<0.001
    "L9": -12.7,        # table→div, p<0.001
    "L5": -11.3,        # Shadow DOM, p<0.001
    "L12": -7.8,        # duplicate IDs, p=0.041 marginal
}

# Per-operator drops (breadth set, Llama 4 text-only, vs H-baseline)
STAGE3_DROPS_BREADTH_LLAMA = {
    "L1": -24.5,
    "L9": -16.8,
    "L5": -14.1,
    "L11": -14.1,
    "ML2": -10.0,
}

# Cross-model L11 adaptive recovery gap (paper §5.3)
L11_DROP_BREADTH_CLAUDE = 2.3   # +pp = recovery (improvement vs H-baseline)
L11_DROP_BREADTH_LLAMA = 14.1   # -pp behavior

# Mode A depth (kept for reference; paper now anchors on breadth)
L1_DROP_DEPTH = -40.0
L11_DROP_DEPTH_CLAUDE = 1.5
L11_DROP_DEPTH_LLAMA = 14.6

# ============================================================
# Paper claims — Phase 3 C.2 composition (§5.4)
# ============================================================
C2_PAIRS_TESTED = 28
C2_SUPER_ADDITIVE = 15      # 15/28 super-additive
C2_ADDITIVE = 9
C2_SUB_ADDITIVE = 4
C2_BINOMIAL_P = 0.019

# Named interaction patterns (paper §5.4)
C2_L11_AMPLIFIER_INTERACTIONS = {
    "L6+L11": 24.1,
    "L9+L11": 19.0,
    "L4+L11": 13.8,
    "L5+L11": 11.3,
    "L1+L11": 8.7,
}

# ============================================================
# Paper claims — Stage 4b SSIM (§5.3 visual control)
# ============================================================
SSIM_THRESHOLD = 0.99           # operators below this are "visually changed"

# Operators with median SSIM < 0.99 in the Stage 4b aggregate
# (verified 2026-05-15 against results/stage3/visual-equiv/ssim-per-operator.csv).
# This is the empirical SSIM finding and is the single source of truth for
# any paper claim about "visually distinguishable" operators.
#
# Note on L9: paper §3 places L9 (table flatten) in the "structural Tier 3"
# narrative category, but its aggregate median SSIM is 1.0 because L9 only
# changes pages that contain tables — most of the 336 URLs do not, so the
# operator is a per-page no-op in those cases. The narrative classification
# (structural vs. annotative vs. decorative) is independent of the SSIM
# magnitude claim.
SSIM_CHANGED_OPS = ["L5", "L6", "L11"]

# Per-operator median SSIM sentinels (paper §4.117 + appendix Table 2)
SSIM_MEDIAN_SENTINELS = {
    "L5": 0.834,
    "L6": 0.889,
    "L11": 0.979,
}

SSIM_BASELINE_NOISE_MAX = 0.001  # base-vs-base2 deterministic-render noise floor

# ============================================================
# Tier / severity prevalence (§4.4 ecological audit)
# ============================================================
ECOLOGICAL_AUDIT_SITES = 34
ECOLOGICAL_TIER3_PCT = 82.4

# ============================================================
# Tolerances for assertion checks
# ============================================================
RATE_TOL_PP = 0.5           # paper rates printed to 1 decimal; allow ±0.5pp
RATE_TOL_FRAC = 0.005       # absolute tolerance on fractional rates
COUNT_TOL_ABS = 0           # exact match on N counts
P_VALUE_LOG_TOL = 1.0       # allow 1 order of magnitude on p-value claims

# ============================================================
# GT corrections (Docker-drift tasks — applied identically across all phases)
# ============================================================
GT_CORRECTIONS = {
    "41": ["abomin", "abdomin"],
    "198": ["veronica costello"],
    "293": ["git clone ssh://git@10.0.1.50:2222/convexegg/super_awesome_robot.git"],
}


def all_phase_ns():
    """Map phase id → (label, expected N)."""
    return {
        "phase1_composite": ("Phase 1 — Composite", N_COMPOSITE),
        "phase2_mode_a": ("Phase 2 — Mode A depth", N_MODE_A),
        "phase3_c2": ("Phase 3 — C.2 composition", N_C2),
        "phase5_smoker": ("Phase 5 — Smoker gate", N_SMOKER),
        "phase6_stage3": ("Phase 6 — Stage 3 breadth", N_STAGE3),
        "phase6_stage4b": ("Phase 6 — Stage 4b SSIM", N_STAGE4B_CAPTURES),
    }
