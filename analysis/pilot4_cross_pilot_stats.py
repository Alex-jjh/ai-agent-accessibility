#!/usr/bin/env python3
"""
Cross-Pilot Statistical Comparison: Pilot 3a vs Pilot 4
========================================================
Paper-ready analysis for CHI/ASSETS submission.

Pilot 3a: First clean text-only run (120 cases, 4 variants × 6 tasks × 5 reps)
Pilot 4:  Canonical run with Plan D injection (240 cases: 120 text + 120 vision)

Statistical tests:
  - Chi-square (2×2) with Cramér's V
  - Fisher's exact test for small cells
  - Cochran-Armitage trend test (ordered variants)
  - Cohen's h for pairwise effect sizes
  - Odds ratios with 95% CI
  - Breslow-Day test for homogeneity of odds ratios
  - Cross-pilot correlation and agreement
  - Sensitivity analysis excluding reddit:67 (suspected F_AMB)
"""

import json
import glob
import math
import sys
import os
from pathlib import Path
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────────────

P4_TRACE_GLOB = "data/pilot4-full/track-a/runs/f4929214-3d48-443b-a859-dd013a737d50/cases/*/trace-attempt-1.json"
P3A_TRACE_GLOB = "data/pilot3a/track-a/runs/9fb3cd72-aa44-40f0-9cc6-52289ff25b4d/cases/*/trace-attempt-1.json"
OUTPUT_PATH = "data/pilot4-cross-pilot-stats.md"

VARIANT_ORDER = ['low', 'medium-low', 'base', 'high']
VARIANT_SCORES = {'low': 0, 'medium-low': 1, 'base': 2, 'high': 3}

# ── Pilot 3a reference data (from steering context) ──────────────────────────

P3A_REFERENCE = {
    'low':        {'success': 6,  'total': 30},
    'medium-low': {'success': 26, 'total': 30},
    'base':       {'success': 27, 'total': 30},
    'high':       {'success': 28, 'total': 30},
}
P3A_OVERALL = {'success': 87, 'total': 120}

# ── Data Loading ──────────────────────────────────────────────────────────────

def parse_case_name(case_name):
    """Parse case directory name into components.
    Format: {site}_{variant}_{taskId}_{configIndex}_{rep}
    Sites can have underscores (e.g., ecommerce_admin).
    """
    variants = ['base', 'low', 'high', 'medium-low']
    for v in variants:
        idx = case_name.find(f'_{v}_')
        if idx >= 0:
            site = case_name[:idx]
            rest = case_name[idx + len(v) + 2:]
            parts = rest.split('_')
            if len(parts) >= 3:
                return {
                    'site': site, 'variant': v,
                    'taskId': parts[0], 'configIndex': int(parts[1]),
                    'rep': int(parts[2])
                }
    return None


def load_traces(glob_pattern, label=""):
    """Load all trace JSON files matching the glob pattern."""
    traces = []
    for fp in sorted(glob.glob(glob_pattern)):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            parts = Path(fp).parts
            case_idx = parts.index('cases') + 1 if 'cases' in parts else -1
            case_name = parts[case_idx] if case_idx > 0 else 'unknown'
            data['_caseName'] = case_name
            data['_filePath'] = fp
            parsed = parse_case_name(case_name)
            if parsed:
                data['_parsed'] = parsed
            traces.append(data)
        except Exception as e:
            print(f"ERROR loading {fp}: {e}", file=sys.stderr)
    print(f"Loaded {len(traces)} traces from {label or glob_pattern}", file=sys.stderr)
    return traces


def is_success(trace):
    """Determine if a trace represents a successful task completion."""
    # Check top-level success field first
    if 'success' in trace:
        return bool(trace['success'])
    # Fall back to outcome field
    outcome = trace.get('outcome', '')
    if outcome:
        return outcome == 'success'
    # Check nested trace object (Pilot 3a format)
    inner = trace.get('trace', {})
    if 'success' in inner:
        return bool(inner['success'])
    if inner.get('outcome', '') == 'success':
        return True
    # Check taskOutcome
    task_outcome = trace.get('taskOutcome', {})
    if task_outcome.get('outcome', '') == 'success':
        return True
    return False


def split_by_config(traces):
    """Split traces into text-only (configIndex=0) and vision-only (configIndex=1)."""
    text_only = []
    vision_only = []
    for t in traces:
        p = t.get('_parsed')
        if not p:
            continue
        if p['configIndex'] == 0:
            text_only.append(t)
        elif p['configIndex'] == 1:
            vision_only.append(t)
    return text_only, vision_only


def compute_variant_rates(traces):
    """Compute success rates per variant."""
    counts = defaultdict(lambda: {'success': 0, 'total': 0})
    for t in traces:
        p = t.get('_parsed')
        if not p:
            continue
        v = p['variant']
        counts[v]['total'] += 1
        if is_success(t):
            counts[v]['success'] += 1
    return dict(counts)


def compute_task_variant_cells(traces):
    """Compute success rates per (task, variant) cell."""
    cells = defaultdict(lambda: {'success': 0, 'total': 0})
    for t in traces:
        p = t.get('_parsed')
        if not p:
            continue
        key = (f"{p['site']}:{p['taskId']}", p['variant'])
        cells[key]['total'] += 1
        if is_success(t):
            cells[key]['success'] += 1
    return dict(cells)


# ── Statistical Functions ─────────────────────────────────────────────────────

def normal_cdf(x):
    """Standard normal CDF using error function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def chi2_p_value(chi2, df):
    """Approximate chi-square p-value using incomplete gamma function."""
    if chi2 <= 0:
        return 1.0
    if df == 1:
        return 2 * (1 - normal_cdf(math.sqrt(chi2)))
    k = df / 2.0
    x = chi2 / 2.0
    s = 1.0 / k
    term = 1.0 / k
    for i in range(1, 300):
        term *= x / (k + i)
        s += term
        if abs(term) < 1e-15:
            break
    p_lower = math.exp(-x + k * math.log(x) - math.lgamma(k)) * s
    return max(0, 1 - p_lower)


def chi_square_2x2(a, b, c, d):
    """Chi-square test for 2×2 contingency table.
    Returns (chi2, p_value, cramers_v).
    Table layout:
        | success | failure |
    g1  |    a    |    b    |
    g2  |    c    |    d    |
    """
    n = a + b + c + d
    if n == 0:
        return 0, 1.0, 0
    ea = (a + b) * (a + c) / n
    eb = (a + b) * (b + d) / n
    ec = (c + d) * (a + c) / n
    ed = (c + d) * (b + d) / n
    chi2 = sum((o - e) ** 2 / e for o, e in [(a, ea), (b, eb), (c, ec), (d, ed)] if e > 0)
    p = chi2_p_value(chi2, 1)
    v = math.sqrt(chi2 / n) if n > 0 else 0
    return chi2, p, v


def fisher_exact_2x2(a, b, c, d):
    """Fisher's exact test (two-sided) for 2×2 table."""
    n = a + b + c + d
    r1 = a + b
    r2 = c + d
    c1 = a + c

    def log_comb(n, k):
        if k < 0 or k > n:
            return float('-inf')
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)

    p_obs = math.exp(log_comb(r1, a) + log_comb(r2, c) - log_comb(n, c1))
    p_val = 0
    for i in range(min(r1, c1) + 1):
        j = r1 - i
        k = c1 - i
        l = r2 - k
        if j >= 0 and k >= 0 and l >= 0:
            p_i = math.exp(log_comb(r1, i) + log_comb(r2, k) - log_comb(n, c1))
            if p_i <= p_obs + 1e-10:
                p_val += p_i
    return min(p_val, 1.0)


def odds_ratio_ci(a, b, c, d, alpha=0.05):
    """Compute odds ratio with 95% CI (Woolf logit method).
    Returns (OR, lower, upper). Uses 0.5 correction for zero cells.
    """
    aa = a + 0.5
    bb = b + 0.5
    cc = c + 0.5
    dd = d + 0.5
    OR = (aa * dd) / (bb * cc)
    log_or = math.log(OR)
    se = math.sqrt(1/aa + 1/bb + 1/cc + 1/dd)
    z = 1.96  # for 95% CI
    lower = math.exp(log_or - z * se)
    upper = math.exp(log_or + z * se)
    return OR, lower, upper


def cohens_h(p1, p2):
    """Cohen's h effect size for comparing two proportions.
    h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
    """
    p1 = max(0.001, min(0.999, p1))
    p2 = max(0.001, min(0.999, p2))
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def cochran_armitage_trend(variant_data, variant_order, scores=None):
    """Cochran-Armitage trend test for ordered proportions.
    variant_data: dict of variant -> {success, total}
    variant_order: list of variant names in order
    scores: optional dict of variant -> numeric score (default: 0,1,2,3)
    Returns (Z, p_value).
    """
    if scores is None:
        scores = {v: i for i, v in enumerate(variant_order)}

    N = sum(variant_data[v]['total'] for v in variant_order if v in variant_data)
    if N == 0:
        return 0, 1.0

    p_bar = sum(variant_data[v]['success'] for v in variant_order if v in variant_data) / N
    t_bar = sum(scores[v] * variant_data[v]['total'] for v in variant_order if v in variant_data) / N

    numerator = 0
    for v in variant_order:
        if v not in variant_data:
            continue
        d = variant_data[v]
        numerator += d['total'] * scores[v] * (d['success'] / d['total'] - p_bar)

    denominator_sq = p_bar * (1 - p_bar) * sum(
        variant_data[v]['total'] * (scores[v] - t_bar) ** 2
        for v in variant_order if v in variant_data
    )

    if denominator_sq <= 0:
        return 0, 1.0

    Z = numerator / math.sqrt(denominator_sq)
    p = 2 * (1 - normal_cdf(abs(Z)))
    return Z, p


def breslow_day_test(tables):
    """Breslow-Day test for homogeneity of odds ratios across K 2×2 tables.
    tables: list of (a, b, c, d) tuples.
    Returns (statistic, p_value, df).
    """
    K = len(tables)
    if K < 2:
        return 0, 1.0, 0

    # Compute Mantel-Haenszel common OR
    R = 0
    S = 0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n == 0:
            continue
        R += a * d / n
        S += b * c / n
    if S == 0:
        return 0, 1.0, K - 1
    OR_mh = R / S

    # For each table, compute expected 'a' under common OR
    BD = 0
    for a, b, c, d in tables:
        n = a + b + c + d
        r1 = a + b
        c1 = a + c
        if n == 0 or r1 == 0 or c1 == 0:
            continue

        # Solve quadratic for expected a under OR_mh
        # OR_mh = a_exp * (n - r1 - c1 + a_exp) / ((r1 - a_exp) * (c1 - a_exp))
        A = OR_mh - 1
        B = -(r1 + c1) * OR_mh - (n - r1 - c1)
        C = OR_mh * r1 * c1

        if abs(A) < 1e-10:
            # OR ≈ 1, linear case
            a_exp = r1 * c1 / n
        else:
            disc = B * B - 4 * A * C
            if disc < 0:
                continue
            a_exp = (-B - math.sqrt(disc)) / (2 * A)

        # Variance of a under null
        b_exp = r1 - a_exp
        c_exp = c1 - a_exp
        d_exp = n - r1 - c1 + a_exp
        denom = 1/max(a_exp, 0.01) + 1/max(b_exp, 0.01) + 1/max(c_exp, 0.01) + 1/max(d_exp, 0.01)
        var_a = 1.0 / denom if denom > 0 else 1.0

        BD += (a - a_exp) ** 2 / var_a

    p = chi2_p_value(BD, K - 1)
    return BD, p, K - 1


def format_p(p):
    """Format p-value for paper presentation."""
    if p < 0.0001:
        return "p<0.0001"
    elif p < 0.001:
        return f"p={p:.4f}"
    elif p < 0.01:
        return f"p={p:.3f}"
    else:
        return f"p={p:.3f}"


def format_pct(n, total):
    """Format as percentage with fraction."""
    pct = 100 * n / total if total > 0 else 0
    return f"{n}/{total} ({pct:.1f}%)"


# ── Report Generation ─────────────────────────────────────────────────────────

def generate_report(p4_text, p4_vision, p3a_traces):
    """Generate the full cross-pilot statistical comparison report."""
    lines = []
    w = lines.append

    w("# Cross-Pilot Statistical Comparison: Pilot 3a vs Pilot 4")
    w("")
    w("**Purpose:** Verify that the core accessibility-performance gradient replicates")
    w("across independent experimental runs with different variant injection mechanisms.")
    w("")

    # ── Pilot 4 text-only variant rates ──
    p4_rates = compute_variant_rates(p4_text)
    p4_vision_rates = compute_variant_rates(p4_vision)

    # ── Pilot 3a rates (from loaded traces or reference) ──
    if p3a_traces:
        p3a_rates = compute_variant_rates(p3a_traces)
    else:
        p3a_rates = P3A_REFERENCE

    # ── Section 1: Side-by-side comparison ──
    w("## 1. Per-Variant Success Rates\n")
    w("| Variant | Pilot 3a | Pilot 4 (text) | Pilot 4 (vision) | Δ (3a vs 4-text) |")
    w("|---------|----------|----------------|------------------|------------------|")
    for v in VARIANT_ORDER:
        p3 = p3a_rates.get(v, {'success': 0, 'total': 0})
        p4 = p4_rates.get(v, {'success': 0, 'total': 0})
        pv = p4_vision_rates.get(v, {'success': 0, 'total': 0})
        r3 = p3['success'] / p3['total'] * 100 if p3['total'] > 0 else 0
        r4 = p4['success'] / p4['total'] * 100 if p4['total'] > 0 else 0
        rv = pv['success'] / pv['total'] * 100 if pv['total'] > 0 else 0
        w(f"| {v} | {format_pct(p3['success'], p3['total'])} | {format_pct(p4['success'], p4['total'])} | {format_pct(pv['success'], pv['total'])} | {r4-r3:+.1f}pp |")
    w("")

    # ── Section 2: Chi-square tests ──
    w("## 2. Primary Statistical Tests\n")

    # Low vs Base — Pilot 4
    p4_low = p4_rates.get('low', {'success': 0, 'total': 0})
    p4_base = p4_rates.get('base', {'success': 0, 'total': 0})
    ls, lf = p4_low['success'], p4_low['total'] - p4_low['success']
    bs, bf = p4_base['success'], p4_base['total'] - p4_base['success']
    chi2, p, cv = chi_square_2x2(ls, lf, bs, bf)
    pf = fisher_exact_2x2(ls, lf, bs, bf)
    OR, ci_lo, ci_hi = odds_ratio_ci(ls, lf, bs, bf)
    h = cohens_h(p4_low['success']/max(p4_low['total'],1), p4_base['success']/max(p4_base['total'],1))

    w("### Pilot 4: Low vs Base (text-only)\n")
    w(f"- Low: {format_pct(ls, ls+lf)}")
    w(f"- Base: {format_pct(bs, bs+bf)}")
    w(f"- χ²={chi2:.2f}, {format_p(p)}, Cramér's V={cv:.3f}")
    w(f"- Fisher's exact {format_p(pf)}")
    w(f"- OR={OR:.2f} (95% CI: {ci_lo:.2f}–{ci_hi:.2f})")
    w(f"- Cohen's h={h:.3f} ({'large' if abs(h)>0.8 else 'medium' if abs(h)>0.5 else 'small'})")
    w("")

    # Low vs Base — Pilot 3a
    p3_low = p3a_rates.get('low', {'success': 0, 'total': 0})
    p3_base = p3a_rates.get('base', {'success': 0, 'total': 0})
    ls3, lf3 = p3_low['success'], p3_low['total'] - p3_low['success']
    bs3, bf3 = p3_base['success'], p3_base['total'] - p3_base['success']
    chi2_3, p_3, cv_3 = chi_square_2x2(ls3, lf3, bs3, bf3)
    pf_3 = fisher_exact_2x2(ls3, lf3, bs3, bf3)
    OR_3, ci_lo_3, ci_hi_3 = odds_ratio_ci(ls3, lf3, bs3, bf3)
    h_3 = cohens_h(p3_low['success']/max(p3_low['total'],1), p3_base['success']/max(p3_base['total'],1))

    w("### Pilot 3a: Low vs Base (text-only)\n")
    w(f"- Low: {format_pct(ls3, ls3+lf3)}")
    w(f"- Base: {format_pct(bs3, bs3+bf3)}")
    w(f"- χ²={chi2_3:.2f}, {format_p(p_3)}, Cramér's V={cv_3:.3f}")
    w(f"- Fisher's exact {format_p(pf_3)}")
    w(f"- OR={OR_3:.2f} (95% CI: {ci_lo_3:.2f}–{ci_hi_3:.2f})")
    w(f"- Cohen's h={h_3:.3f} ({'large' if abs(h_3)>0.8 else 'medium' if abs(h_3)>0.5 else 'small'})")
    w("")

    # ── Section 3: Cochran-Armitage trend test ──
    w("## 3. Cochran-Armitage Trend Test\n")
    Z4, p_ca4 = cochran_armitage_trend(p4_rates, VARIANT_ORDER)
    w(f"**Pilot 4 (text-only):** Z={Z4:.3f}, {format_p(p_ca4)}")
    if p3a_traces:
        Z3, p_ca3 = cochran_armitage_trend(p3a_rates, VARIANT_ORDER)
        w(f"**Pilot 3a:** Z={Z3:.3f}, {format_p(p_ca3)}")
    w("")

    # ── Section 4: Pairwise effect sizes ──
    w("## 4. Pairwise Effect Sizes (Cohen's h)\n")
    w("| Comparison | Pilot 3a h | Pilot 4 h | Interpretation |")
    w("|------------|-----------|-----------|----------------|")
    pairs = [('low', 'medium-low'), ('low', 'base'), ('low', 'high'),
             ('medium-low', 'base'), ('base', 'high')]
    for v1, v2 in pairs:
        r3_1 = p3a_rates.get(v1, {'success':0,'total':1})
        r3_2 = p3a_rates.get(v2, {'success':0,'total':1})
        r4_1 = p4_rates.get(v1, {'success':0,'total':1})
        r4_2 = p4_rates.get(v2, {'success':0,'total':1})
        h3 = cohens_h(r3_1['success']/max(r3_1['total'],1), r3_2['success']/max(r3_2['total'],1))
        h4 = cohens_h(r4_1['success']/max(r4_1['total'],1), r4_2['success']/max(r4_2['total'],1))
        interp = "large" if max(abs(h3), abs(h4)) > 0.8 else "medium" if max(abs(h3), abs(h4)) > 0.5 else "small"
        w(f"| {v1} vs {v2} | {h3:+.3f} | {h4:+.3f} | {interp} |")
    w("")

    # ── Section 5: Breslow-Day homogeneity ──
    w("## 5. Breslow-Day Test (Homogeneity of ORs across tasks)\n")
    p4_cells = compute_task_variant_cells(p4_text)
    tasks = sorted(set(k[0] for k in p4_cells.keys()))
    tables = []
    for task in tasks:
        low_cell = p4_cells.get((task, 'low'), {'success': 0, 'total': 0})
        base_cell = p4_cells.get((task, 'base'), {'success': 0, 'total': 0})
        a = low_cell['success']
        b = low_cell['total'] - a
        c = base_cell['success']
        d = base_cell['total'] - c
        if (a+b) > 0 and (c+d) > 0:
            tables.append((a, b, c, d))
    if len(tables) >= 2:
        bd_stat, bd_p, bd_df = breslow_day_test(tables)
        w(f"- Statistic={bd_stat:.2f}, df={bd_df}, {format_p(bd_p)}")
        if bd_p < 0.05:
            w("- **Heterogeneous:** Effect size varies significantly across tasks")
        else:
            w("- **Homogeneous:** Effect size is consistent across tasks")
    w("")

    # ── Section 6: Sensitivity excluding reddit:67 ──
    w("## 6. Sensitivity Analysis (excluding reddit:67)\n")
    p4_text_no67 = [t for t in p4_text
                    if not (t.get('_parsed', {}).get('site') == 'reddit'
                            and t.get('_parsed', {}).get('taskId') == '67')]
    rates_no67 = compute_variant_rates(p4_text_no67)
    low_no67 = rates_no67.get('low', {'success':0,'total':0})
    base_no67 = rates_no67.get('base', {'success':0,'total':0})
    if low_no67['total'] > 0 and base_no67['total'] > 0:
        ls_n, lf_n = low_no67['success'], low_no67['total'] - low_no67['success']
        bs_n, bf_n = base_no67['success'], base_no67['total'] - base_no67['success']
        chi2_n, p_n, cv_n = chi_square_2x2(ls_n, lf_n, bs_n, bf_n)
        w(f"- Low (excl 67): {format_pct(ls_n, ls_n+lf_n)}")
        w(f"- Base (excl 67): {format_pct(bs_n, bs_n+bf_n)}")
        w(f"- χ²={chi2_n:.2f}, {format_p(p_n)}, V={cv_n:.3f}")
        w(f"- **Still significant:** {'YES' if p_n < 0.05 else 'NO'}")
    w("")

    # ── Section 7: Interaction effect (text vs vision) ──
    w("## 7. Interaction Effect: Text-Only vs Vision-Only\n")
    tg = 0
    vg = 0
    p4_low_t = p4_rates.get('low', {'success':0,'total':1})
    p4_base_t = p4_rates.get('base', {'success':0,'total':1})
    p4_low_v = p4_vision_rates.get('low', {'success':0,'total':1})
    p4_base_v = p4_vision_rates.get('base', {'success':0,'total':1})
    if p4_low_t['total'] > 0 and p4_base_t['total'] > 0:
        tg = p4_base_t['success']/p4_base_t['total']*100 - p4_low_t['success']/p4_low_t['total']*100
    if p4_low_v['total'] > 0 and p4_base_v['total'] > 0:
        vg = p4_base_v['success']/p4_base_v['total']*100 - p4_low_v['success']/p4_low_v['total']*100
    w(f"- Text-only gradient (base-low): {tg:.1f}pp")
    w(f"- Vision-only gradient (base-low): {vg:.1f}pp")
    w(f"- **Interaction:** {tg-vg:.1f}pp")
    w("")
    if tg > 20 and vg < tg * 0.5:
        w("Text-only shows a substantially larger gradient than vision-only,")
        w("supporting the a11y tree as the primary causal mechanism.")
    w("")

    # ── Section 8: Summary ──
    w("## 8. Summary for Paper\n")
    w("| Metric | Pilot 3a | Pilot 4 |")
    w("|--------|----------|---------|")
    p3_overall_r = sum(p3a_rates[v]['success'] for v in VARIANT_ORDER if v in p3a_rates) / max(sum(p3a_rates[v]['total'] for v in VARIANT_ORDER if v in p3a_rates), 1) * 100
    p4_overall_r = sum(p4_rates[v]['success'] for v in VARIANT_ORDER if v in p4_rates) / max(sum(p4_rates[v]['total'] for v in VARIANT_ORDER if v in p4_rates), 1) * 100
    w(f"| Overall text-only | {p3_overall_r:.1f}% | {p4_overall_r:.1f}% |")
    w(f"| Low rate | {p3a_rates.get('low',{}).get('success',0)/max(p3a_rates.get('low',{}).get('total',1),1)*100:.1f}% | {p4_rates.get('low',{}).get('success',0)/max(p4_rates.get('low',{}).get('total',1),1)*100:.1f}% |")
    w(f"| Base rate | {p3a_rates.get('base',{}).get('success',0)/max(p3a_rates.get('base',{}).get('total',1),1)*100:.1f}% | {p4_rates.get('base',{}).get('success',0)/max(p4_rates.get('base',{}).get('total',1),1)*100:.1f}% |")
    w(f"| Low vs Base χ² | {chi2_3:.2f} | {chi2:.2f} |")
    w(f"| Low vs Base p | {format_p(p_3)} | {format_p(p)} |")
    w(f"| Cramér's V | {cv_3:.3f} | {cv:.3f} |")
    w("")

    return '\n'.join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load Pilot 4 traces
    p4_traces = load_traces(P4_TRACE_GLOB, "Pilot 4")
    if not p4_traces:
        # Try alternate path
        alt_glob = "data/pilot4-full/track-a/runs/*/cases/*/trace-attempt-*.json"
        p4_traces = load_traces(alt_glob, "Pilot 4 (alt)")
    if not p4_traces:
        print("ERROR: No Pilot 4 traces found", file=sys.stderr)
        sys.exit(1)

    p4_text, p4_vision = split_by_config(p4_traces)
    print(f"Pilot 4: {len(p4_text)} text-only, {len(p4_vision)} vision-only", file=sys.stderr)

    # Load Pilot 3a traces
    p3a_traces = load_traces(P3A_TRACE_GLOB, "Pilot 3a")
    if not p3a_traces:
        # Try loading from case JSON files
        alt_3a = "data/pilot3a/9fb3cd72-aa44-40f0-9cc6-52289ff25b4d/cases/*.json"
        p3a_traces = load_traces(alt_3a, "Pilot 3a (case JSON)")
    print(f"Pilot 3a: {len(p3a_traces)} traces", file=sys.stderr)

    report = generate_report(p4_text, p4_vision, p3a_traces)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport written to {OUTPUT_PATH}", file=sys.stderr)


if __name__ == '__main__':
    main()