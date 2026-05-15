"""
Statistical helpers used across stage verifiers.

Originally lived inline in `amt_statistics.py`; extracted 2026-05-15 so
`stage3_statistics.py`, `phase*_*.py` stage modules, and any future verifier
can import them without circular dependency on amt_statistics.
"""
import math

from scipy import stats


def wilson_ci(successes: int, total: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    z = stats.norm.ppf(1 - alpha / 2)
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return max(0, center - margin), min(1, center + margin)


def odds_ratio_ci(a: int, b: int, c: int, d: int, alpha: float = 0.05) -> tuple[float, float, float]:
    """Odds ratio with Woolf logit 95% CI. Returns (OR, lo, hi).

    Applies Haldane-Anscombe correction (+0.5) when any cell is zero.
    """
    if min(a, b, c, d) == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    OR = (a * d) / (b * c)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    z = stats.norm.ppf(1 - alpha / 2)
    lo = math.exp(math.log(OR) - z * se)
    hi = math.exp(math.log(OR) + z * se)
    return OR, lo, hi


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for two proportions."""
    phi1 = 2 * math.asin(math.sqrt(p1))
    phi2 = 2 * math.asin(math.sqrt(p2))
    return phi1 - phi2


def mantel_haenszel_or(tables: list) -> float:
    """Mantel-Haenszel common OR across a list of 2×2 tables."""
    num = sum(t[0][0] * t[1][1] / sum(sum(row) for row in t) for t in tables)
    den = sum(t[0][1] * t[1][0] / sum(sum(row) for row in t) for t in tables)
    return num / den if den > 0 else float("inf")


def breslow_day(tables: list, or_mh: float) -> tuple[float, int, float]:
    """Breslow-Day test for OR homogeneity across strata.

    Returns (BD statistic, df, p-value).
    """
    BD = 0.0
    for t in tables:
        a, b = t[0]
        c, d = t[1]
        n1, n2 = a + b, c + d
        m1 = a + c
        A_coef = 1 - or_mh
        B_coef = or_mh * (n1 + m1) + n2 - m1
        C_coef = -or_mh * n1 * m1
        if abs(A_coef) < 1e-10:
            if B_coef == 0:
                continue
            a_e = -C_coef / B_coef
        else:
            disc = B_coef**2 - 4 * A_coef * C_coef
            if disc < 0:
                continue
            r1 = (-B_coef + math.sqrt(disc)) / (2 * A_coef)
            r2 = (-B_coef - math.sqrt(disc)) / (2 * A_coef)
            a_e = r1 if 0 < r1 < min(n1, m1) else r2
        b_e = n1 - a_e
        c_e = m1 - a_e
        d_e = n2 - c_e
        if any(x <= 0 for x in [a_e, b_e, c_e, d_e]):
            continue
        var_a = 1 / (1 / a_e + 1 / b_e + 1 / c_e + 1 / d_e)
        BD += (a - a_e) ** 2 * var_a
    df = len(tables) - 1
    p = 1 - stats.chi2.cdf(BD, df)
    return BD, df, p
