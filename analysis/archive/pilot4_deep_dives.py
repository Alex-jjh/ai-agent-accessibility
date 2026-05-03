#!/usr/bin/env python3
"""Pilot 4 Deep Dive Analysis — 6 targeted investigations.

Reads specific trace files, analyzes failure modes, and outputs a markdown report.

Investigations:
  1. reddit:67 anomaly (base/high 20%)
  2. ecom:24 low success (1/5)
  3. admin:4 high failure (4/5)
  4. Vision phantom label classification
  5. reddit:29 high failures (3/5 = 60%)
  6. Token inflation controlled comparison (ecom:24 high vs base)

Output: data/pilot4-deep-dives.md
"""

import json, glob, os, sys
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data' / 'pilot4-full'
TRACE_DIR = DATA_DIR / 'track-a' / 'runs'
OUTPUT = DATA_DIR.parent / 'pilot4-deep-dives.md'

def find_traces(site_pattern, variant=None, task_id=None, config_idx=None):
    """Find traces matching criteria. Returns list of (case_name, trace_dict)."""
    results = []
    for fp in sorted(TRACE_DIR.glob('*/cases/*/trace-attempt-*.json')):
        case = fp.parent.name
        parsed = parse_case(case)
        if not parsed:
            continue
        if site_pattern and site_pattern not in parsed['site']:
            continue
        if variant is not None and parsed['variant'] != variant:
            continue
        if task_id is not None and parsed['taskId'] != task_id:
            continue
        if config_idx is not None and parsed['configIndex'] != config_idx:
            continue
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['_case'] = case
            data['_parsed'] = parsed
            results.append(data)
        except Exception as e:
            print(f"  ERR {fp}: {e}", file=sys.stderr)
    return results

def parse_case(name):
    for v in ['medium-low', 'base', 'low', 'high']:
        m = f'_{v}_'
        idx = name.find(m)
        if idx >= 0:
            site = name[:idx]
            rest = name[idx+len(m):].split('_')
            if len(rest) >= 3:
                return {'site': site, 'variant': v, 'taskId': rest[0],
                        'configIndex': int(rest[1]), 'rep': int(rest[2])}
    return None

def avg(lst): return sum(lst)/len(lst) if lst else 0
def med(lst):
    if not lst: return 0
    s = sorted(lst); n = len(s)
    return (s[n//2-1]+s[n//2])/2 if n%2==0 else s[n//2]

def get_final_answer(t):
    """Extract the agent's final send_msg_to_user answer."""
    for s in reversed(t.get('steps', [])):
        a = s.get('action', '')
        if 'send_msg_to_user' in a:
            # Extract message content
            start = a.find('("')
            end = a.rfind('")')
            if start >= 0 and end > start:
                return a[start+2:end][:200]
            return a[18:200]  # fallback
    return None

def get_last_reasoning(t):
    """Get reasoning from the last step."""
    steps = t.get('steps', [])
    if steps:
        return steps[-1].get('reasoning', '')[:300]
    return ''

def count_skip_links(t):
    """Count 'Skip to' or 'skip-link' mentions in observations."""
    count = 0
    for s in t.get('steps', []):
        obs = s.get('observation', '')
        count += obs.lower().count('skip to') + obs.lower().count('skip-link')
    return count

def has_keyword_in_obs(t, kw):
    for s in t.get('steps', []):
        if kw in s.get('observation', ''):
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# Investigation 1: reddit:67 anomaly
# ══════════════════════════════════════════════════════════════════════════════

def investigate_reddit67():
    lines = ["## 1. reddit:67 Anomaly — Why base/high = 20%\n"]
    traces = find_traces('reddit', task_id='67', config_idx=0)  # text-only
    lines.append(f"**Loaded:** {len(traces)} text-only traces for reddit:67\n")

    # Per-variant breakdown
    by_var = defaultdict(list)
    for t in traces:
        by_var[t['_parsed']['variant']].append(t)

    lines.append("### Per-Variant Results\n")
    lines.append("| Variant | Success | Total | Rate | Avg Tokens | Avg Steps |")
    lines.append("|---------|---------|-------|------|-----------|-----------|")
    for v in ['low', 'medium-low', 'base', 'high']:
        ts = by_var[v]
        succ = sum(1 for t in ts if t.get('success'))
        tok = avg([t.get('totalTokens',0) for t in ts])
        stp = avg([t.get('totalSteps',0) for t in ts])
        lines.append(f"| {v} | {succ} | {len(ts)} | {succ/len(ts)*100:.0f}% | {tok:,.0f} | {stp:.1f} |")
    lines.append("")

    # Analyze each base trace
    lines.append("### Base Variant Trace-by-Trace\n")
    for t in by_var.get('base', []):
        cn = t['_case']
        ans = get_final_answer(t)
        reason = get_last_reasoning(t)
        lines.append(f"**{cn}:** {t.get('outcome','?')}, steps={t.get('totalSteps',0)}, tokens={t.get('totalTokens',0):,}")
        if ans: lines.append(f"  Answer: `{ans}`")
        lines.append(f"  Last reasoning: {reason[:200]}")
        # Check what actions were taken
        actions = [(s.get('stepNum'), s.get('action','')[:100]) for s in t.get('steps',[])]
        lines.append(f"  Actions: {actions[:8]}")
        lines.append("")

    # Analyze high variant
    lines.append("### High Variant Trace-by-Trace\n")
    for t in by_var.get('high', []):
        cn = t['_case']
        ans = get_final_answer(t)
        lines.append(f"**{cn}:** {t.get('outcome','?')}, steps={t.get('totalSteps',0)}, tokens={t.get('totalTokens',0):,}")
        if ans: lines.append(f"  Answer: `{ans}`")
        lines.append("")

    # Compare with medium-low (100% success)
    lines.append("### Medium-Low (100% success) — What's Different?\n")
    for t in by_var.get('medium-low', [])[:2]:
        cn = t['_case']
        ans = get_final_answer(t)
        lines.append(f"**{cn}:** {t.get('outcome','?')}, steps={t.get('totalSteps',0)}")
        if ans: lines.append(f"  Answer: `{ans}`")
        lines.append("")

    # Diagnosis
    lines.append("### Diagnosis\n")
    base_answers = [get_final_answer(t) for t in by_var.get('base', []) if get_final_answer(t)]
    ml_answers = [get_final_answer(t) for t in by_var.get('medium-low', []) if get_final_answer(t)]
    lines.append(f"Base answers: {base_answers}")
    lines.append(f"ML answers: {ml_answers}")
    lines.append("")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Investigation 2: ecom:24 low success (1/5)
# ══════════════════════════════════════════════════════════════════════════════

def investigate_ecom24_low():
    lines = ["## 2. ecom:24 Low — The 1/5 Success Case\n"]
    traces = find_traces('ecommerce', variant='low', task_id='24', config_idx=0)
    lines.append(f"**Loaded:** {len(traces)} traces\n")

    lines.append("### All 5 Traces\n")
    for t in traces:
        cn = t['_case']
        succ = t.get('success', False)
        ans = get_final_answer(t)
        steps = t.get('totalSteps', 0)
        tokens = t.get('totalTokens', 0)
        marker = "✅" if succ else "❌"
        lines.append(f"{marker} **{cn}:** steps={steps}, tokens={tokens:,}, outcome={t.get('outcome','?')}")
        if ans: lines.append(f"  Answer: `{ans}`")
        # Check for tablist/tabpanel
        has_tab = has_keyword_in_obs(t, 'tablist')
        has_panel = has_keyword_in_obs(t, 'tabpanel')
        lines.append(f"  tablist={has_tab}, tabpanel={has_panel}")
        # Show action sequence
        actions = [s.get('action','')[:80] for s in t.get('steps',[])]
        lines.append(f"  Actions: {actions}")
        lines.append("")

    # The success case — detailed analysis
    success_traces = [t for t in traces if t.get('success')]
    if success_traces:
        t = success_traces[0]
        lines.append("### Success Case Deep Dive\n")
        for s in t.get('steps', []):
            lines.append(f"Step {s.get('stepNum')}: action=`{s.get('action','')[:100]}`")
            lines.append(f"  result={s.get('result')}, reasoning={s.get('reasoning','')[:150]}")
            lines.append("")
    lines.append("")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Investigation 3: admin:4 high failure (4/5)
# ══════════════════════════════════════════════════════════════════════════════

def investigate_admin4_high():
    lines = ["## 3. admin:4 High — The 1 Failure Case\n"]
    traces = find_traces('ecommerce_admin', variant='high', task_id='4', config_idx=0)
    lines.append(f"**Loaded:** {len(traces)} traces\n")

    lines.append("### All 5 Traces\n")
    for t in traces:
        cn = t['_case']
        succ = t.get('success', False)
        marker = "✅" if succ else "❌"
        tokens = t.get('totalTokens', 0)
        steps = t.get('totalSteps', 0)
        skip_count = count_skip_links(t)
        ans = get_final_answer(t)
        lines.append(f"{marker} **{cn}:** steps={steps}, tokens={tokens:,}, skip-link mentions={skip_count}")
        if ans: lines.append(f"  Answer: `{ans}`")
        lines.append("")

    # Compare tokens: high vs base
    base_traces = find_traces('ecommerce_admin', variant='base', task_id='4', config_idx=0)
    high_tokens = [t.get('totalTokens',0) for t in traces]
    base_tokens = [t.get('totalTokens',0) for t in base_traces]
    lines.append("### Token Comparison: High vs Base\n")
    lines.append(f"- High: avg={avg(high_tokens):,.0f}, med={med(high_tokens):,.0f}, values={high_tokens}")
    lines.append(f"- Base: avg={avg(base_tokens):,.0f}, med={med(base_tokens):,.0f}, values={base_tokens}")
    lines.append(f"- Δ: {avg(high_tokens)-avg(base_tokens):+,.0f} ({(avg(high_tokens)/max(avg(base_tokens),1)-1)*100:+.1f}%)")
    lines.append("")

    # The failure case
    fail_traces = [t for t in traces if not t.get('success')]
    if fail_traces:
        t = fail_traces[0]
        lines.append("### Failure Case Deep Dive\n")
        lines.append(f"Case: {t['_case']}, outcome={t.get('outcome')}, steps={t.get('totalSteps')}, tokens={t.get('totalTokens'):,}")
        for s in t.get('steps', []):
            lines.append(f"  Step {s.get('stepNum')}: `{s.get('action','')[:100]}` → {s.get('result')}")
        lines.append("")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Investigation 4: Vision phantom label classification
# ══════════════════════════════════════════════════════════════════════════════

def investigate_vision_phantoms():
    lines = ["## 4. Vision Phantom Label Classification\n"]
    lines.append("Sampling 2-3 vision-only failure traces per site to classify phantom label modes.\n")

    mode_a = 0  # element exists but not visible
    mode_b = 0  # element doesn't exist
    other = 0
    details = []

    for site in ['ecommerce', 'ecommerce_admin', 'reddit']:
        # Get vision-only failures (config_idx=1)
        traces = find_traces(site, config_idx=1)
        failures = [t for t in traces if not t.get('success')][:3]

        for t in failures:
            cn = t['_case']
            error_types = Counter()
            for s in t.get('steps', []):
                detail = s.get('resultDetail', '') or ''
                if 'not visible' in detail.lower() or 'not interactable' in detail.lower():
                    error_types['not_visible'] += 1
                elif 'could not find' in detail.lower() or 'valueerror' in detail.lower():
                    error_types['not_found'] += 1
                elif s.get('result') in ('failure', 'error') and detail:
                    error_types['other'] += 1

            dominant = error_types.most_common(1)[0] if error_types else ('none', 0)
            if dominant[0] == 'not_visible':
                mode_a += 1
                mode = 'A (exists, not visible)'
            elif dominant[0] == 'not_found':
                mode_b += 1
                mode = 'B (element missing)'
            else:
                other += 1
                mode = f'Other ({dominant[0]})'

            details.append(f"- `{cn}`: {mode} — errors: {dict(error_types)}")

    lines.append("### Classification Results\n")
    lines.append(f"- **Mode A** (element exists, not visible): {mode_a} traces")
    lines.append(f"- **Mode B** (element doesn't exist): {mode_b} traces")
    lines.append(f"- **Other**: {other} traces\n")
    lines.append("### Trace Details\n")
    lines.extend(details)
    lines.append("")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Investigation 5: reddit:29 high failures (3/5 = 60%)
# ══════════════════════════════════════════════════════════════════════════════

def investigate_reddit29_high():
    lines = ["## 5. reddit:29 High — 3 Failures (60%)\n"]
    traces = find_traces('reddit', variant='high', task_id='29', config_idx=0)
    lines.append(f"**Loaded:** {len(traces)} traces\n")

    lines.append("### All 5 Traces\n")
    for t in traces:
        cn = t['_case']
        succ = t.get('success', False)
        marker = "✅" if succ else "❌"
        tokens = t.get('totalTokens', 0)
        steps = t.get('totalSteps', 0)
        skip_count = count_skip_links(t)
        ans = get_final_answer(t)
        lines.append(f"{marker} **{cn}:** steps={steps}, tokens={tokens:,}, skip-links={skip_count}")
        if ans: lines.append(f"  Answer: `{ans}`")
        lines.append("")

    # Compare with base (100% success)
    base_traces = find_traces('reddit', variant='base', task_id='29', config_idx=0)
    lines.append("### Comparison: High vs Base\n")
    h_tok = [t.get('totalTokens',0) for t in traces]
    b_tok = [t.get('totalTokens',0) for t in base_traces]
    lines.append(f"- High tokens: avg={avg(h_tok):,.0f}, values={h_tok}")
    lines.append(f"- Base tokens: avg={avg(b_tok):,.0f}, values={b_tok}")
    lines.append(f"- High success: {sum(1 for t in traces if t.get('success'))}/5")
    lines.append(f"- Base success: {sum(1 for t in base_traces if t.get('success'))}/5")
    lines.append("")

    # Failure traces detail
    fail_traces = [t for t in traces if not t.get('success')]
    lines.append(f"### {len(fail_traces)} Failure Traces\n")
    for t in fail_traces:
        cn = t['_case']
        lines.append(f"**{cn}:** outcome={t.get('outcome')}, steps={t.get('totalSteps')}, tokens={t.get('totalTokens'):,}")
        ans = get_final_answer(t)
        if ans: lines.append(f"  Answer: `{ans}`")
        reason = get_last_reasoning(t)
        lines.append(f"  Last reasoning: {reason[:250]}")
        # Action sequence
        actions = [(s.get('stepNum'), s.get('action','')[:80]) for s in t.get('steps',[])]
        lines.append(f"  Actions: {actions[:10]}")
        lines.append("")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Investigation 6: Token inflation controlled comparison
# ══════════════════════════════════════════════════════════════════════════════

def investigate_token_inflation():
    lines = ["## 6. Token Inflation — Controlled Comparison\n"]
    lines.append("Compare high vs base tokens on tasks where BOTH have 100% success,\n")
    lines.append("eliminating failure-driven token inflation as a confound.\n")

    # ecom:24 text-only: both high and base are 100%
    lines.append("### ecom:24 (text-only, both 100% success)\n")
    high_24 = find_traces('ecommerce', variant='high', task_id='24', config_idx=0)
    base_24 = find_traces('ecommerce', variant='base', task_id='24', config_idx=0)
    h_tok = [t.get('totalTokens',0) for t in high_24]
    b_tok = [t.get('totalTokens',0) for t in base_24]
    lines.append(f"- High: {h_tok} → avg={avg(h_tok):,.0f}")
    lines.append(f"- Base: {b_tok} → avg={avg(b_tok):,.0f}")
    delta = avg(h_tok) - avg(b_tok)
    pct = (delta / max(avg(b_tok), 1)) * 100
    lines.append(f"- **Δ = {delta:+,.0f} ({pct:+.1f}%)**")
    lines.append("")

    # ecom:23 text-only: both high and base are 100%
    lines.append("### ecom:23 (text-only, both 100% success)\n")
    high_23 = find_traces('ecommerce', variant='high', task_id='23', config_idx=0)
    base_23 = find_traces('ecommerce', variant='base', task_id='23', config_idx=0)
    h_tok2 = [t.get('totalTokens',0) for t in high_23]
    b_tok2 = [t.get('totalTokens',0) for t in base_23]
    lines.append(f"- High: {h_tok2} → avg={avg(h_tok2):,.0f}")
    lines.append(f"- Base: {b_tok2} → avg={avg(b_tok2):,.0f}")
    delta2 = avg(h_tok2) - avg(b_tok2)
    pct2 = (delta2 / max(avg(b_tok2), 1)) * 100
    lines.append(f"- **Δ = {delta2:+,.0f} ({pct2:+.1f}%)**")
    lines.append("")

    # ecom:26 text-only: both 100%
    lines.append("### ecom:26 (text-only, both 100% success)\n")
    high_26 = find_traces('ecommerce', variant='high', task_id='26', config_idx=0)
    base_26 = find_traces('ecommerce', variant='base', task_id='26', config_idx=0)
    h_tok3 = [t.get('totalTokens',0) for t in high_26]
    b_tok3 = [t.get('totalTokens',0) for t in base_26]
    lines.append(f"- High: {h_tok3} → avg={avg(h_tok3):,.0f}")
    lines.append(f"- Base: {b_tok3} → avg={avg(b_tok3):,.0f}")
    delta3 = avg(h_tok3) - avg(b_tok3)
    pct3 = (delta3 / max(avg(b_tok3), 1)) * 100
    lines.append(f"- **Δ = {delta3:+,.0f} ({pct3:+.1f}%)**")
    lines.append("")

    # admin:4 text-only: high=80%, base=100% — include for reference
    lines.append("### admin:4 (text-only, high=80% base=100%)\n")
    high_a4 = find_traces('ecommerce_admin', variant='high', task_id='4', config_idx=0)
    base_a4 = find_traces('ecommerce_admin', variant='base', task_id='4', config_idx=0)
    h_tok4 = [t.get('totalTokens',0) for t in high_a4]
    b_tok4 = [t.get('totalTokens',0) for t in base_a4]
    lines.append(f"- High: {h_tok4} → avg={avg(h_tok4):,.0f}")
    lines.append(f"- Base: {b_tok4} → avg={avg(b_tok4):,.0f}")
    delta4 = avg(h_tok4) - avg(b_tok4)
    pct4 = (delta4 / max(avg(b_tok4), 1)) * 100
    lines.append(f"- **Δ = {delta4:+,.0f} ({pct4:+.1f}%)**")
    lines.append("")

    # Summary
    lines.append("### ISSUE-BR-4 Verdict\n")
    all_deltas = [delta, delta2, delta3]
    avg_delta = avg(all_deltas)
    lines.append(f"Average high-base token delta (100% success tasks): {avg_delta:+,.0f}")
    if avg_delta > 5000:
        lines.append("⚠️ **CONFIRMED:** High variant has significant token inflation vs base.")
        lines.append("MutationObserver sentinel bug (ISSUE-BR-4) likely causing skip-link accumulation.")
    elif avg_delta > 1000:
        lines.append("🟡 **MODERATE:** Some token inflation detected. May be legitimate ARIA additions.")
    else:
        lines.append("✅ **NOT CONFIRMED:** Token difference is within expected range for ARIA enhancements.")
    lines.append("")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parts = []
    parts.append("# Pilot 4 Deep Dive Analysis\n")
    parts.append("**Date:** 2026-04-08")
    parts.append("**Data:** 240/240 traces, Run ID f4929214\n---\n")

    print("Investigation 1: reddit:67...", file=sys.stderr)
    parts.append(investigate_reddit67())

    print("Investigation 2: ecom:24 low...", file=sys.stderr)
    parts.append(investigate_ecom24_low())

    print("Investigation 3: admin:4 high...", file=sys.stderr)
    parts.append(investigate_admin4_high())

    print("Investigation 4: vision phantoms...", file=sys.stderr)
    parts.append(investigate_vision_phantoms())

    print("Investigation 5: reddit:29 high...", file=sys.stderr)
    parts.append(investigate_reddit29_high())

    print("Investigation 6: token inflation...", file=sys.stderr)
    parts.append(investigate_token_inflation())

    output = '\n'.join(parts)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\nReport written to {OUTPUT}", file=sys.stderr)

if __name__ == '__main__':
    main()
