#!/usr/bin/env python3.11
"""Deep dive into Qwen metadata — check success field anomalies."""
import json, glob
from collections import defaultdict

# Parse Qwen metadata
qwen_data = []
for f in sorted(glob.glob('data/a11y-cua/Qwen3-VL-32B-Instruct/**/metadata_*.json', recursive=True)):
    with open(f) as fh:
        m = json.load(fh)
    if '/Default/' in f:
        condition = 'default'
    elif '/Screen' in f:
        condition = 'screen_reader'
    elif '/Magnifier/' in f:
        condition = 'magnifier'
    else:
        condition = 'unknown'
    task = m.get('task', {})
    session = m.get('session', {})
    dur = session.get('ended_at', 0) - session.get('started_at', 0)
    qwen_data.append(dict(
        condition=condition,
        task_id=task.get('task_id'),
        task_group=task.get('task_group'),
        success=task.get('success'),
        duration=round(dur, 1),
        title=task.get('task_title', ''),
        n_apps=len(session.get('applications', [])),
        total_events=sum(a.get('events', 0) for a in session.get('applications', [])),
    ))

# Per-condition success rates
print('=== Qwen success rates ===')
for cond in ['default', 'screen_reader', 'magnifier']:
    tasks = [d for d in qwen_data if d['condition'] == cond]
    n = len(tasks)
    succ = sum(1 for d in tasks if d['success'])
    print(f'  {cond:15s}: {succ}/{n} = {succ/n*100:.1f}%')

# Per-task success for each condition
print('\n=== Qwen per-task success (Web & Browsing) ===')
print(f'{"ID":>3s} {"Title":40s} {"Default":>7s} {"SR":>7s} {"Mag":>7s}')
task_map = defaultdict(dict)
for d in qwen_data:
    task_map[d['task_id']][d['condition']] = d

for tid in sorted(task_map):
    d = task_map[tid].get('default', {})
    if d.get('task_group') != 'Browsing and Web':
        continue
    def s(cond):
        v = task_map[tid].get(cond, {}).get('success')
        return 'True' if v else 'False' if v is not None else '?'
    print(f"{tid:3d} {d.get('title','')[:40]:40s} {s('default'):>7s} {s('screen_reader'):>7s} {s('magnifier'):>7s}")

# Check for anomalies: paper says Qwen SR=0%, Mag=0%
print('\n=== Qwen SR successes (paper says 0%) ===')
sr_succ = [d for d in qwen_data if d['condition'] == 'screen_reader' and d['success']]
for d in sr_succ:
    print(f"  Task {d['task_id']}: {d['title']}, events={d['total_events']}, dur={d['duration']}s, apps={d['n_apps']}")

print('\n=== Qwen Magnifier successes (paper says 0%) ===')
mag_succ = [d for d in qwen_data if d['condition'] == 'magnifier' and d['success']]
for d in mag_succ:
    print(f"  Task {d['task_id']}: {d['title']}, events={d['total_events']}, dur={d['duration']}s, apps={d['n_apps']}")
