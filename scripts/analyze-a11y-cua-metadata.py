#!/usr/bin/env python3.11
"""Analyze A11y-CUA metadata files for B.2 task mapping."""
import json, glob
from collections import defaultdict

data = []
for f in sorted(glob.glob('data/a11y-cua/**/metadata_*.json', recursive=True)):
    with open(f) as fh:
        m = json.load(fh)
    if '/SU/' in f:
        group, condition = 'SU', 'default'
    elif '/BLVU/' in f:
        group, condition = 'BLVU', 'screen_reader'
    elif 'Claude' in f:
        group = 'Claude'
        condition = 'default' if '/Default/' in f else ('screen_reader' if '/Screen' in f else 'magnifier')
    elif 'Qwen' in f:
        group = 'Qwen'
        condition = 'default' if '/Default/' in f else ('screen_reader' if '/Screen' in f else 'magnifier')
    else:
        continue
    task = m.get('task', {})
    session = m.get('session', {})
    dur = session.get('ended_at', 0) - session.get('started_at', 0)
    data.append(dict(
        group=group, condition=condition,
        task_id=task.get('task_id'),
        task_group=task.get('task_group'),
        success=task.get('success'),
        duration=round(dur, 1),
        title=task.get('task_title', ''),
        instruction=task.get('instruction', '')
    ))

# Success rates
print('=== Success rates by group x condition ===')
groups = defaultdict(lambda: defaultdict(list))
for d in data:
    groups[(d['group'], d['condition'])]['s'].append(d['success'])
    groups[(d['group'], d['condition'])]['d'].append(d['duration'])
for (g, c), v in sorted(groups.items()):
    n = len(v['s'])
    sr = sum(1 for s in v['s'] if s) / n * 100
    ad = sum(v['d']) / n
    print(f'  {g:8s} {c:15s}: {sr:5.1f}% success, {ad:6.1f}s avg (n={n})')

# Per-category success for Claude
print('\n=== Claude success by category x condition ===')
cat_stats = defaultdict(list)
for d in data:
    if d['group'] == 'Claude':
        cat_stats[(d['task_group'], d['condition'])].append(d['success'])
for (cat, cond), vals in sorted(cat_stats.items()):
    sr = sum(1 for s in vals if s) / len(vals) * 100
    print(f'  {cat:25s} {cond:15s}: {sr:5.1f}% (n={len(vals)})')

# Web & Browsing tasks detail
print('\n=== All 60 tasks (grouped by category) ===')
seen = {}
for d in sorted(data, key=lambda x: (x['task_group'] or '', x['task_id'] or 0)):
    tid = d['task_id']
    if tid not in seen:
        seen[tid] = d

cur_cat = None
for tid in sorted(seen, key=lambda t: (seen[t]['task_group'] or '', t)):
    d = seen[tid]
    if d['task_group'] != cur_cat:
        cur_cat = d['task_group']
        print(f'\n--- {cur_cat} ---')
    instr = d['instruction'][:120]
    print(f"  {tid:3d}: {d['title']}")
    print(f"       {instr}")

# Per-task success matrix (SU, BLVU, Claude-default, Claude-SR, Claude-Mag)
print('\n=== Per-task success: Web & Browsing ===')
print(f"{'ID':>3s} {'Title':40s} {'SU':>5s} {'BLVU':>5s} {'C-Def':>5s} {'C-SR':>5s} {'C-Mag':>5s}")
task_success = defaultdict(lambda: defaultdict(list))
for d in data:
    key = (d['group'], d['condition'])
    task_success[d['task_id']][key].append(d['success'])

for tid in sorted(task_success):
    d = seen.get(tid)
    if not d or d['task_group'] != 'Browsing and Web':
        continue
    def rate(key):
        vals = task_success[tid].get(key, [])
        if not vals: return '  -  '
        return f"{sum(1 for v in vals if v)/len(vals)*100:5.1f}"
    print(f"{tid:3d} {d['title'][:40]:40s} "
          f"{rate(('SU','default')):>5s} {rate(('BLVU','screen_reader')):>5s} "
          f"{rate(('Claude','default')):>5s} {rate(('Claude','screen_reader')):>5s} "
          f"{rate(('Claude','magnifier')):>5s}")
