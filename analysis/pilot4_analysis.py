#!/usr/bin/env python3
"""Comprehensive analysis of Pilot 4 (240/240 cases) — canonical dataset.

Plan D variant injection (context.route + deferred patch + MutationObserver).
Design: 6 tasks × 4 variants × 2 agents × 5 reps = 240 runs.

Outputs: data/pilot4-full-analysis.md
"""

import json
import glob
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path
import math

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot4-full')
TRACE_GLOB = os.path.join(DATA_DIR, 'track-a', 'runs', '*', 'cases', '*', 'trace-attempt-*.json')

EXPECTED_TASKS = {
    'ecommerce_admin': ['4'],
    'ecommerce': ['23', '24', '26'],
    'reddit': ['29', '67']
}
EXPECTED_VARIANTS = ['low', 'medium-low', 'base', 'high']
EXPECTED_CONFIGS = [0, 1]  # text-only, vision-only
EXPECTED_REPS = [1, 2, 3, 4, 5]

PILOT3A_RATES = {'low': 20.0, 'medium-low': 86.7, 'base': 90.0, 'high': 93.3}

# ── Data Loading ──────────────────────────────────────────────────────────────

def load_all_traces():
    traces = []
    for fp in sorted(glob.glob(TRACE_GLOB)):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            parts = Path(fp).parts
            case_idx = parts.index('cases') + 1 if 'cases' in parts else -1
            data['_caseName'] = parts[case_idx] if case_idx > 0 else 'unknown'
            data['_filePath'] = fp
            traces.append(data)
        except Exception as e:
            print(f"ERROR loading {fp}: {e}", file=sys.stderr)
    return traces

def parse_case_name(case_name):
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
                    'taskId': parts[0], 'configIndex': int(parts[1]), 'rep': int(parts[2])
                }
    return None

def classify_agent(trace):
    config = trace.get('agentConfig', {})
    obs_mode = config.get('observationMode', 'unknown')
    case = parse_case_name(trace.get('_caseName', ''))
    ci = case['configIndex'] if case else -1
    if ci == 0 or obs_mode == 'text-only': return 'text-only'
    if ci == 1 or obs_mode in ('vision-only', 'vision'): return 'vision-only'
    return 'unknown'

# ── Statistical Helpers ───────────────────────────────────────────────────────

def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def chi2_p_value(chi2, df):
    if chi2 <= 0: return 1.0
    if df == 1: return 2 * (1 - normal_cdf(math.sqrt(chi2)))
    k = df / 2.0; x = chi2 / 2.0
    s = 1.0 / k; term = 1.0 / k
    for i in range(1, 200):
        term *= x / (k + i); s += term
        if abs(term) < 1e-12: break
    p_lower = math.exp(-x + k * math.log(x) - math.lgamma(k)) * s
    return max(0, 1 - p_lower)

def chi_square_2x2(a, b, c, d):
    n = a + b + c + d
    if n == 0: return 0, 1.0, 0
    ea = (a+b)*(a+c)/n; eb = (a+b)*(b+d)/n; ec = (c+d)*(a+c)/n; ed = (c+d)*(b+d)/n
    chi2 = sum((o-e)**2/e for o, e in [(a,ea),(b,eb),(c,ec),(d,ed)] if e > 0)
    return chi2, chi2_p_value(chi2, 1), math.sqrt(chi2/n) if n > 0 else 0

def fisher_exact_2x2(a, b, c, d):
    n = a+b+c+d; r1 = a+b; r2 = c+d; c1 = a+c
    def lc(n, k):
        if k < 0 or k > n: return float('-inf')
        return math.lgamma(n+1) - math.lgamma(k+1) - math.lgamma(n-k+1)
    p_obs = math.exp(lc(r1,a) + lc(r2,c) - lc(n,c1))
    p_val = 0
    for i in range(min(r1,c1)+1):
        j=r1-i; k=c1-i; l=r2-k
        if j>=0 and k>=0 and l>=0:
            p_i = math.exp(lc(r1,i) + lc(r2,k) - lc(n,c1))
            if p_i <= p_obs + 1e-10: p_val += p_i
    return min(p_val, 1.0)

def avg(lst): return sum(lst)/len(lst) if lst else 0
def median(lst):
    if not lst: return 0
    s = sorted(lst); n = len(s)
    return (s[n//2-1]+s[n//2])/2 if n%2==0 else s[n//2]


# ── Analysis Sections ─────────────────────────────────────────────────────────

def section_inventory(traces):
    lines = ["## 1. Data Inventory\n"]
    lines.append(f"**Total traces:** {len(traces)}\n")

    ac = Counter(classify_agent(t) for t in traces)
    lines.append(f"**Text-only:** {ac.get('text-only',0)}")
    lines.append(f"**Vision-only:** {ac.get('vision-only',0)}\n")

    # Variant × Agent
    va = defaultdict(lambda: defaultdict(int))
    for t in traces:
        va[t.get('variant','?')][classify_agent(t)] += 1
    lines.append("### Traces per Variant × Agent\n")
    lines.append("| Variant | Text-Only | Vision-Only | Total |")
    lines.append("|---------|-----------|-------------|-------|")
    for v in EXPECTED_VARIANTS:
        tx = va[v].get('text-only',0); vi = va[v].get('vision-only',0)
        lines.append(f"| {v} | {tx} | {vi} | {tx+vi} |")
    lines.append("")

    # Task × Variant × Agent
    tva = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for t in traces:
        c = parse_case_name(t.get('_caseName',''))
        if c:
            tva[f"{c['site']}:{c['taskId']}"][c['variant']][classify_agent(t)] += 1
    lines.append("### Traces per Task × Variant\n")
    lines.append("| Task | Variant | Text | Vision |")
    lines.append("|------|---------|------|--------|")
    for task in sorted(tva):
        for v in EXPECTED_VARIANTS:
            lines.append(f"| {task} | {v} | {tva[task][v].get('text-only',0)} | {tva[task][v].get('vision-only',0)} |")
    lines.append("")

    # Missing cases
    expected = set()
    for site, tasks in EXPECTED_TASKS.items():
        for tid in tasks:
            for v in EXPECTED_VARIANTS:
                for ci in EXPECTED_CONFIGS:
                    for r in EXPECTED_REPS:
                        expected.add(f"{site}_{v}_{tid}_{ci}_{r}")
    found = set()
    for t in traces:
        c = parse_case_name(t.get('_caseName',''))
        if c: found.add(f"{c['site']}_{c['variant']}_{c['taskId']}_{c['configIndex']}_{c['rep']}")
    missing = sorted(expected - found)
    lines.append(f"**Expected:** {len(expected)} | **Found:** {len(found)} | **Missing:** {len(missing)}")
    if missing:
        lines.append("\nMissing cases:")
        for m in missing[:20]: lines.append(f"- `{m}`")
        if len(missing) > 20: lines.append(f"- ... and {len(missing)-20} more")
    lines.append("")
    return '\n'.join(lines)


def section_text_only(traces):
    text = [t for t in traces if classify_agent(t) == 'text-only']
    lines = [f"## 2. Text-Only Results (n={len(text)})\n"]

    vs = defaultdict(lambda: {'s':0,'t':0})
    for t in text:
        v = t.get('variant','?'); vs[v]['t'] += 1
        if t.get('success', False): vs[v]['s'] += 1

    lines.append("### Per-Variant Success Rates\n")
    lines.append("| Variant | Success | Total | Rate | Pilot 3a |")
    lines.append("|---------|---------|-------|------|----------|")
    rates = {}
    for v in EXPECTED_VARIANTS:
        s,t = vs[v]['s'], vs[v]['t']
        r = s/t*100 if t>0 else 0; rates[v] = r
        lines.append(f"| {v} | {s} | {t} | {r:.1f}% | {PILOT3A_RATES.get(v,0):.1f}% |")
    os_ = sum(vs[v]['s'] for v in EXPECTED_VARIANTS)
    ot = sum(vs[v]['t'] for v in EXPECTED_VARIANTS)
    lines.append(f"| **Overall** | **{os_}** | **{ot}** | **{os_/ot*100:.1f}%** | **72.5%** |")
    lines.append("")

    # Task × Variant matrix
    tv = defaultdict(lambda: defaultdict(lambda: {'s':0,'t':0}))
    for t in text:
        c = parse_case_name(t.get('_caseName',''))
        if c:
            k = f"{c['site']}:{c['taskId']}"; v = c['variant']
            tv[k][v]['t'] += 1
            if t.get('success',False): tv[k][v]['s'] += 1
    lines.append("### Task × Variant Matrix\n")
    lines.append("| Task | low | med-low | base | high |")
    lines.append("|------|-----|---------|------|------|")
    for task in sorted(tv):
        row = [task]
        for v in EXPECTED_VARIANTS:
            s,t = tv[task][v]['s'], tv[task][v]['t']
            row.append(f"{s}/{t} ({s/t*100:.0f}%)" if t>0 else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Chi-square low vs base
    ls,lf = vs['low']['s'], vs['low']['t']-vs['low']['s']
    bs,bf = vs['base']['s'], vs['base']['t']-vs['base']['s']
    chi2, p, cv = chi_square_2x2(ls, lf, bs, bf)
    pf = fisher_exact_2x2(ls, lf, bs, bf)
    lines.append("### Chi-Square: Low vs Base\n")
    lines.append(f"- Low: {ls}/{ls+lf} ({ls/(ls+lf)*100:.1f}%)" if ls+lf>0 else "- Low: 0/0")
    lines.append(f"- Base: {bs}/{bs+bf} ({bs/(bs+bf)*100:.1f}%)" if bs+bf>0 else "- Base: 0/0")
    lines.append(f"- χ² = {chi2:.2f}, p = {p:.6f}, Cramér's V = {cv:.3f}")
    lines.append(f"- Fisher's exact p = {pf:.6f}")
    lines.append(f"- **Significant:** {'YES' if p<0.05 else 'NO'}\n")

    # Gradient
    lines.append("### Variant Gradient\n")
    g = rates.get('base',0) - rates.get('low',0)
    tr = rates.get('high',0) - rates.get('low',0)
    step = rates.get('medium-low',0) - rates.get('low',0)
    lines.append(f"- Base - Low gap: {g:.1f}pp")
    lines.append(f"- High - Low range: {tr:.1f}pp")
    lines.append(f"- Low → Medium-Low step: {step:.1f}pp")
    if tr > 0: lines.append(f"- Step fraction: {step/tr*100:.0f}%")
    lines.append("")
    return '\n'.join(lines), rates


def section_vision_only(traces):
    vis = [t for t in traces if classify_agent(t) == 'vision-only']
    lines = [f"## 3. Vision-Only Results (n={len(vis)})\n"]

    vs = defaultdict(lambda: {'s':0,'t':0})
    for t in vis:
        v = t.get('variant','?'); vs[v]['t'] += 1
        if t.get('success',False): vs[v]['s'] += 1

    lines.append("### Per-Variant Success Rates\n")
    lines.append("| Variant | Success | Total | Rate |")
    lines.append("|---------|---------|-------|------|")
    vrates = {}
    for v in EXPECTED_VARIANTS:
        s,t = vs[v]['s'], vs[v]['t']
        r = s/t*100 if t>0 else 0; vrates[v] = r
        lines.append(f"| {v} | {s} | {t} | {r:.1f}% |")
    os_ = sum(vs[v]['s'] for v in EXPECTED_VARIANTS)
    ot = sum(vs[v]['t'] for v in EXPECTED_VARIANTS)
    lines.append(f"| **Overall** | **{os_}** | **{ot}** | **{os_/ot*100:.1f}%** |")
    lines.append("")

    # Task × Variant
    tv = defaultdict(lambda: defaultdict(lambda: {'s':0,'t':0}))
    for t in vis:
        c = parse_case_name(t.get('_caseName',''))
        if c:
            k = f"{c['site']}:{c['taskId']}"; v = c['variant']
            tv[k][v]['t'] += 1
            if t.get('success',False): tv[k][v]['s'] += 1
    lines.append("### Task × Variant Matrix\n")
    lines.append("| Task | low | med-low | base | high |")
    lines.append("|------|-----|---------|------|------|")
    for task in sorted(tv):
        row = [task]
        for v in EXPECTED_VARIANTS:
            s,t = tv[task][v]['s'], tv[task][v]['t']
            row.append(f"{s}/{t} ({s/t*100:.0f}%)" if t>0 else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Chi-square low vs base
    ls,lf = vs['low']['s'], vs['low']['t']-vs['low']['s']
    bs,bf = vs['base']['s'], vs['base']['t']-vs['base']['s']
    if (ls+lf)>0 and (bs+bf)>0:
        chi2, p, cv = chi_square_2x2(ls, lf, bs, bf)
        lines.append("### Chi-Square: Low vs Base\n")
        lines.append(f"- Low: {ls}/{ls+lf} ({ls/(ls+lf)*100:.1f}%)")
        lines.append(f"- Base: {bs}/{bs+bf} ({bs/(bs+bf)*100:.1f}%)")
        lines.append(f"- χ² = {chi2:.2f}, p = {p:.6f}, V = {cv:.3f}")
        lines.append(f"- **Significant:** {'YES' if p<0.05 else 'NO'}\n")
    lines.append("")
    return '\n'.join(lines), vrates


def section_comparison(traces, text_rates, vision_rates):
    lines = ["## 4. Text-Only vs Vision-Only (Causal Inference)\n"]

    lines.append("### Side-by-Side\n")
    lines.append("| Variant | Text-Only | Vision-Only | Δ |")
    lines.append("|---------|-----------|-------------|---|")
    for v in EXPECTED_VARIANTS:
        tr = text_rates.get(v,0); vr = vision_rates.get(v,0)
        lines.append(f"| {v} | {tr:.1f}% | {vr:.1f}% | {tr-vr:+.1f}pp |")
    lines.append("")

    tg = text_rates.get('base',0) - text_rates.get('low',0)
    vg = vision_rates.get('base',0) - vision_rates.get('low',0)
    lines.append("### Interaction Test\n")
    lines.append(f"- Text gradient (base-low): {tg:.1f}pp")
    lines.append(f"- Vision gradient (base-low): {vg:.1f}pp")
    lines.append(f"- **Interaction:** {tg-vg:.1f}pp\n")

    if tg > 20 and abs(vg) < 15:
        lines.append(f"✅ **STRONG CAUSAL EVIDENCE:** Text-only gradient ({tg:.1f}pp) >> Vision gradient ({vg:.1f}pp)")
    elif tg > 20 and vg > 15:
        lines.append(f"⚠️ **MIXED:** Both show gradient. Text={tg:.1f}pp, Vision={vg:.1f}pp")
    else:
        lines.append(f"📊 Text={tg:.1f}pp, Vision={vg:.1f}pp")
    lines.append("")

    # Per-task interaction
    tt = defaultdict(lambda: defaultdict(lambda: {'s':0,'t':0}))
    vt = defaultdict(lambda: defaultdict(lambda: {'s':0,'t':0}))
    for t in traces:
        c = parse_case_name(t.get('_caseName',''))
        if not c: continue
        a = classify_agent(t); k = f"{c['site']}:{c['taskId']}"; v = c['variant']
        d = tt if a=='text-only' else vt
        d[k][v]['t'] += 1
        if t.get('success',False): d[k][v]['s'] += 1

    lines.append("### Per-Task Interaction\n")
    lines.append("| Task | T(base) | T(low) | TΔ | V(base) | V(low) | VΔ | Inter |")
    lines.append("|------|---------|--------|-----|---------|--------|-----|-------|")
    for task in sorted(set(list(tt)+list(vt))):
        def r(d,v):
            s,t = d[v]['s'], d[v]['t']
            return s/t*100 if t>0 else None
        tb=r(tt[task],'base'); tl=r(tt[task],'low')
        vb=r(vt[task],'base'); vl=r(vt[task],'low')
        td = (tb-tl) if tb is not None and tl is not None else None
        vd = (vb-vl) if vb is not None and vl is not None else None
        inter = (td-vd) if td is not None and vd is not None else None
        f = lambda x: f"{x:.0f}%" if x is not None else "—"
        fd = lambda x: f"{x:+.0f}pp" if x is not None else "—"
        lines.append(f"| {task} | {f(tb)} | {f(tl)} | {fd(td)} | {f(vb)} | {f(vl)} | {fd(vd)} | {fd(inter)} |")
    lines.append("")
    return '\n'.join(lines)


def section_tokens(traces):
    lines = ["## 5. Token & Step Analysis\n"]

    m = defaultdict(lambda: defaultdict(lambda: {'tokens':[],'steps':[],'dur':[]}))
    for t in traces:
        a = classify_agent(t); v = t.get('variant','?')
        tok = t.get('totalTokens',0); st = t.get('totalSteps',0); d = t.get('durationMs',0)
        if tok>0: m[a][v]['tokens'].append(tok)
        if st>0: m[a][v]['steps'].append(st)
        if d>0: m[a][v]['dur'].append(d)

    lines.append("### Avg Tokens by Agent × Variant\n")
    lines.append("| Variant | Text Avg | Text Med | Vision Avg | Vision Med |")
    lines.append("|---------|----------|----------|------------|------------|")
    for v in EXPECTED_VARIANTS:
        ta=avg(m['text-only'][v]['tokens']); tm=median(m['text-only'][v]['tokens'])
        va=avg(m['vision-only'][v]['tokens']); vm=median(m['vision-only'][v]['tokens'])
        lines.append(f"| {v} | {ta:,.0f} | {tm:,.0f} | {va:,.0f} | {vm:,.0f} |")
    lines.append("")

    # ISSUE-BR-4 check: high vs base token comparison
    lines.append("### ISSUE-BR-4 Check: High vs Base Token Inflation\n")
    for agent in ['text-only', 'vision-only']:
        ht = m[agent]['high']['tokens']; bt = m[agent]['base']['tokens']
        if ht and bt:
            lines.append(f"**{agent}:** high avg={avg(ht):,.0f}, base avg={avg(bt):,.0f}, "
                        f"Δ={avg(ht)-avg(bt):+,.0f} ({(avg(ht)/avg(bt)-1)*100:+.1f}%)")
    lines.append("")

    # Steps
    lines.append("### Avg Steps by Agent × Variant\n")
    lines.append("| Variant | Text Avg | Vision Avg |")
    lines.append("|---------|----------|------------|")
    for v in EXPECTED_VARIANTS:
        lines.append(f"| {v} | {avg(m['text-only'][v]['steps']):.1f} | {avg(m['vision-only'][v]['steps']):.1f} |")
    lines.append("")

    # Outcome breakdown
    lines.append("### Outcome Breakdown\n")
    oc = defaultdict(lambda: defaultdict(int))
    for t in traces:
        a = classify_agent(t); o = t.get('outcome', 'failure')
        oc[a][o] += 1
    lines.append("| Outcome | Text-Only | Vision-Only |")
    lines.append("|---------|-----------|-------------|")
    for o in ['success','failure','timeout','partial_success']:
        lines.append(f"| {o} | {oc['text-only'].get(o,0)} | {oc['vision-only'].get(o,0)} |")
    lines.append("")
    return '\n'.join(lines)


def section_failures(traces):
    lines = ["## 6. Failure Analysis\n"]

    for agent_type in ['text-only', 'vision-only']:
        fails = [t for t in traces if classify_agent(t)==agent_type and not t.get('success',False)]
        lines.append(f"### {agent_type.title()} Failures (n={len(fails)})\n")

        by_outcome = Counter(f.get('outcome','?') for f in fails)
        lines.append("| Outcome | Count |")
        lines.append("|---------|-------|")
        for o,c in by_outcome.most_common(): lines.append(f"| {o} | {c} |")
        lines.append("")

        by_variant = Counter(f.get('variant','?') for f in fails)
        lines.append("| Variant | Failures |")
        lines.append("|---------|----------|")
        for v in EXPECTED_VARIANTS: lines.append(f"| {v} | {by_variant.get(v,0)} |")
        lines.append("")

        by_task = Counter()
        for f in fails:
            c = parse_case_name(f.get('_caseName',''))
            if c: by_task[f"{c['site']}:{c['taskId']}"] += 1
        lines.append("| Task | Failures |")
        lines.append("|------|----------|")
        for task,cnt in by_task.most_common(): lines.append(f"| {task} | {cnt} |")

        maxed = sum(1 for f in fails if f.get('totalSteps',0) >= 29)
        lines.append(f"\n**Hit step limit (≥29):** {maxed}/{len(fails)}\n")
    return '\n'.join(lines)


def section_plan_d_verification(traces):
    """Verify Plan D variant injection is working — check for goto escape and tablist/tabpanel."""
    lines = ["## 7. Plan D Verification\n"]

    # Check ecom:23 low text-only — should be ~0% (content invisibility)
    ecom23_low_text = [t for t in traces
                       if classify_agent(t)=='text-only'
                       and t.get('variant')=='low'
                       and parse_case_name(t.get('_caseName','')) is not None
                       and parse_case_name(t.get('_caseName',''))['site']=='ecommerce'
                       and parse_case_name(t.get('_caseName',''))['taskId']=='23']
    s = sum(1 for t in ecom23_low_text if t.get('success',False))
    lines.append(f"### ecom:23 low text-only: {s}/{len(ecom23_low_text)}\n")

    # Search for tablist/tabpanel in observations
    for t in ecom23_low_text:
        cn = t.get('_caseName','')
        steps = t.get('steps', [])
        has_tablist = any('tablist' in str(st.get('observation','')) for st in steps)
        has_tabpanel = any('tabpanel' in str(st.get('observation','')) for st in steps)
        lines.append(f"- `{cn}`: success={t.get('success')}, tablist={has_tablist}, tabpanel={has_tabpanel}")
    lines.append("")

    # Check all low text-only by task
    lines.append("### All Low Text-Only Results\n")
    lines.append("| Task | Success | Total | Rate |")
    lines.append("|------|---------|-------|------|")
    low_text = defaultdict(lambda: {'s':0,'t':0})
    for t in traces:
        if classify_agent(t)!='text-only' or t.get('variant')!='low': continue
        c = parse_case_name(t.get('_caseName',''))
        if c:
            k = f"{c['site']}:{c['taskId']}"
            low_text[k]['t'] += 1
            if t.get('success',False): low_text[k]['s'] += 1
    for task in sorted(low_text):
        s,t = low_text[task]['s'], low_text[task]['t']
        lines.append(f"| {task} | {s} | {t} | {s/t*100:.0f}% |")
    lines.append("")

    # Check for goto escape: look for goto() actions in low variant traces
    lines.append("### Goto Escape Check (low variant)\n")
    goto_count = 0
    for t in traces:
        if t.get('variant') != 'low': continue
        for st in t.get('steps', []):
            if 'goto(' in st.get('action', ''):
                goto_count += 1
                cn = t.get('_caseName','')
                lines.append(f"- `{cn}` step {st.get('stepNum')}: {st.get('action','')[:80]}")
                break
    if goto_count == 0:
        lines.append("✅ No goto() escape detected in any low variant trace")
    else:
        lines.append(f"\n⚠️ {goto_count} traces with goto() in low variant")
    lines.append("")
    return '\n'.join(lines)


def section_deep_interpretation(traces, text_rates, vision_rates):
    lines = ["## 8. Deep Interpretation\n"]

    # Non-low comparison
    tnl = {'s':0,'t':0}; vnl = {'s':0,'t':0}
    for t in traces:
        if t.get('variant')=='low': continue
        a = classify_agent(t)
        d = tnl if a=='text-only' else vnl
        d['t'] += 1
        if t.get('success',False): d['s'] += 1
    tr = tnl['s']/tnl['t']*100 if tnl['t']>0 else 0
    vr = vnl['s']/vnl['t']*100 if vnl['t']>0 else 0

    lines.append("### Non-Low Variant Comparison\n")
    lines.append(f"| Agent | Success | Rate |")
    lines.append(f"|-------|---------|------|")
    lines.append(f"| Text-only | {tnl['s']}/{tnl['t']} | {tr:.1f}% |")
    lines.append(f"| Vision-only | {vnl['s']}/{vnl['t']} | {vr:.1f}% |")
    lines.append(f"| **Gap** | | **{tr-vr:.1f}pp** |\n")

    # Comparison with Pilot 3a
    lines.append("### Comparison with Pilot 3a\n")
    lines.append("| Variant | Pilot 3a | Pilot 4 | Δ |")
    lines.append("|---------|----------|---------|---|")
    for v in EXPECTED_VARIANTS:
        p3 = PILOT3A_RATES.get(v,0); p4 = text_rates.get(v,0)
        lines.append(f"| {v} | {p3:.1f}% | {p4:.1f}% | {p4-p3:+.1f}pp |")
    lines.append("")

    # Key findings summary
    lines.append("### Key Findings\n")
    tg = text_rates.get('base',0) - text_rates.get('low',0)
    vg = vision_rates.get('base',0) - vision_rates.get('low',0)
    step = text_rates.get('medium-low',0) - text_rates.get('low',0)
    total = text_rates.get('high',0) - text_rates.get('low',0)

    lines.append(f"1. **Text-only gradient:** low={text_rates.get('low',0):.1f}% → ml={text_rates.get('medium-low',0):.1f}% → base={text_rates.get('base',0):.1f}% → high={text_rates.get('high',0):.1f}%")
    lines.append(f"2. **Step function:** low→ml jump = {step:.1f}pp ({step/total*100:.0f}% of total)" if total>0 else "2. N/A")
    lines.append(f"3. **Vision-only overall:** {sum(1 for t in traces if classify_agent(t)=='vision-only' and t.get('success',False))}/{sum(1 for t in traces if classify_agent(t)=='vision-only')}")
    lines.append(f"4. **Interaction effect:** {tg-vg:.1f}pp (text gradient {tg:.1f}pp vs vision {vg:.1f}pp)")
    lines.append(f"5. **Non-low gap:** text {tr:.1f}% vs vision {vr:.1f}% = {tr-vr:.1f}pp advantage")
    lines.append("")
    return '\n'.join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading traces...", file=sys.stderr)
    traces = load_all_traces()
    print(f"Loaded {len(traces)} traces", file=sys.stderr)
    if not traces:
        print(f"ERROR: No traces found! Searched: {TRACE_GLOB}", file=sys.stderr)
        sys.exit(1)

    parts = []
    parts.append("# Pilot 4 Full Analysis (240/240 Cases)\n")
    parts.append(f"**Run ID:** f4929214-3d48-443b-a859-dd013a737d50")
    parts.append(f"**Total traces:** {len(traces)}")
    parts.append(f"**Design:** 6 tasks × 4 variants × 2 agents × 5 reps = 240")
    parts.append(f"**Variant injection:** Plan D (context.route + deferred patch + MutationObserver)")
    parts.append(f"**Date:** 2026-04-07\n---\n")

    parts.append(section_inventory(traces))

    print("Text-only analysis...", file=sys.stderr)
    text_section, text_rates = section_text_only(traces)
    parts.append(text_section)

    print("Vision-only analysis...", file=sys.stderr)
    vision_section, vision_rates = section_vision_only(traces)
    parts.append(vision_section)

    print("Comparison...", file=sys.stderr)
    parts.append(section_comparison(traces, text_rates, vision_rates))

    print("Tokens...", file=sys.stderr)
    parts.append(section_tokens(traces))

    print("Failures...", file=sys.stderr)
    parts.append(section_failures(traces))

    print("Plan D verification...", file=sys.stderr)
    parts.append(section_plan_d_verification(traces))

    print("Interpretation...", file=sys.stderr)
    parts.append(section_deep_interpretation(traces, text_rates, vision_rates))

    output = '\n'.join(parts)
    out_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot4-full-analysis.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\nAnalysis written to {out_path}", file=sys.stderr)

if __name__ == '__main__':
    main()
