#!/usr/bin/env python3
"""Audit smoker shard B passing tasks for Stage 3 go/no-go gate.

One-off audit script; not part of the standard analysis pipeline.
"""
import csv, json, os, re, glob, random, statistics
from collections import defaultdict, Counter

CASES_DIR = 'data/smoker-shard-b/dac27420-a4ae-4899-b9e0-daeed23b5c52/cases'
FILTER_CSV = 'results/smoker/filter-summary.csv'
PASSING_JSON = 'results/smoker/passing-tasks.json'

with open(PASSING_JSON) as f:
    passing = json.load(f)
pass_gitlab = set(passing['gitlab'])
pass_reddit = set(passing['reddit'])
passing_pairs = [('gitlab', t) for t in pass_gitlab] + [('reddit', t) for t in pass_reddit]
print(f"[INIT] {len(passing_pairs)} passing tasks ({len(pass_gitlab)} gitlab + {len(pass_reddit)} reddit)")

with open('test.raw.json') as f:
    raw = json.load(f)
INTENT = {str(t['task_id']): t['intent'] for t in raw}

STEP_ROWS = {}
with open(FILTER_CSV) as f:
    for row in csv.DictReader(f):
        STEP_ROWS[(row['app'], row['task_id'])] = row

def case_files(app, task_id):
    return sorted(glob.glob(f'{CASES_DIR}/{app}_base_{task_id}_0_*.json'))

def load_case(p):
    with open(p) as f:
        return json.load(f)

def final_send_msg(trace):
    for s in reversed(trace.get('steps', [])):
        a = s.get('action', '')
        if isinstance(a, str) and a.startswith('send_msg_to_user'):
            return a
    return None

def extract_msg_arg(action_str):
    if not action_str:
        return None
    m = re.match(r'^send_msg_to_user\((.*)\)\s*$', action_str, re.DOTALL)
    if not m:
        return action_str
    inner = m.group(1).strip()
    if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in ('"', "'"):
        if inner[0] == '"':
            try:
                return json.loads(inner)
            except Exception:
                pass
        return inner[1:-1]
    return inner

def norm_answer(s):
    if s is None:
        return ''
    s = s.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s.strip('.,!?"\'')

# ---------------------------------------------------------------
# FOCUS 1: Answer drift
# ---------------------------------------------------------------
print("\n" + "="*70)
print("FOCUS 1: Answer drift across 3 reps in passing tasks")
print("="*70)

all_answers = {}
for app, tid in passing_pairs:
    files = case_files(app, tid)
    answers = [extract_msg_arg(final_send_msg(load_case(fp)['trace'])) for fp in files]
    all_answers[(app, tid)] = answers

drift = []
for (app, tid), ans in all_answers.items():
    normed = set(norm_answer(a) for a in ans)
    if len(normed) > 1:
        drift.append((app, tid, ans))

print(f"Tasks with >1 distinct normalized answer across 3 reps: {len(drift)}")
for app, tid, ans in drift:
    print(f"\n  {app}:{tid}  intent: {INTENT.get(tid,'?')[:110]}")
    for i, a in enumerate(ans, 1):
        print(f"    rep{i}: {(a or '<NONE>')[:160]!r}")

# ---------------------------------------------------------------
# FOCUS 2: Hidden bridge errors
# ---------------------------------------------------------------
print("\n" + "="*70)
print("FOCUS 2: Hidden bridge errors in passing tasks")
print("="*70)

ERR_PATTERNS = [
    ('context_window',   re.compile(r'context.{0,25}(window|length|exceed)', re.I)),
    ('traceback',        re.compile(r'Traceback \(most recent call last', re.I)),
    ('err_prefix',       re.compile(r'\bERR_')),
    ('Error:',           re.compile(r'(?<!\w)Error:\s', re.I)),
    ('Exception',        re.compile(r'(?<!\w)Exception:', re.I)),
    ('TimeoutError',     re.compile(r'TimeoutError', re.I)),
    ('login_failed',     re.compile(r'login\s+(failed|timeout|error)', re.I)),
    ('playwright_err',   re.compile(r'Playwright[^\n]{0,80}(Error|closed|crashed|fail)', re.I)),
    ('bridge_fail',      re.compile(r'\[bridge\].{0,60}(fail|error|crash)', re.I)),
]

hits_per_task = defaultdict(lambda: defaultdict(list))
total_cases = 0
for app, tid in passing_pairs:
    for fp in case_files(app, tid):
        total_cases += 1
        c = load_case(fp)
        bl = c['trace'].get('bridgeLog', '')
        if not isinstance(bl, str):
            continue
        for name, pat in ERR_PATTERNS:
            for m in pat.finditer(bl):
                start = max(0, m.start() - 40)
                end = min(len(bl), m.end() + 100)
                hits_per_task[(app, tid)][name].append((os.path.basename(fp), bl[start:end]))
                break

print(f"Scanned {total_cases} cases across {len(passing_pairs)} passing tasks")
for name, _ in ERR_PATTERNS:
    tasks_hit = [k for k, v in hits_per_task.items() if name in v]
    print(f"  pattern {name!r}: {len(tasks_hit)} passing tasks affected")
    # show up to 3 examples
    shown = 0
    for k in tasks_hit:
        if shown >= 3: break
        for fn, snip in hits_per_task[k][name][:1]:
            print(f"    {k[0]}:{k[1]} [{fn}] …{snip!r}…")
            shown += 1

# ---------------------------------------------------------------
# FOCUS 3: Answer quality vs intent — 10 random
# ---------------------------------------------------------------
print("\n" + "="*70)
print("FOCUS 3: Answer quality (intent vs final answer) — 10 random passing tasks")
print("="*70)
random.seed(7)
for app, tid in random.sample(passing_pairs, 10):
    intent = INTENT.get(tid, '?')
    ans = all_answers[(app, tid)]
    ms = STEP_ROWS.get((app, tid), {}).get('median_steps', '?')
    print(f"\n  {app}:{tid}  median_steps={ms}")
    print(f"    intent : {intent[:200]}")
    for i, a in enumerate(ans, 1):
        print(f"    rep{i}  : {(a or '<NONE>')[:200]!r}")

# ---------------------------------------------------------------
# FOCUS 4: Step boundaries
# ---------------------------------------------------------------
print("\n" + "="*70)
print("FOCUS 4: Step distribution — passing tasks near [3,25] boundaries")
print("="*70)

low_bnd, high_bnd, all_med = [], [], []
for app, tid in passing_pairs:
    ms_str = STEP_ROWS.get((app, tid), {}).get('median_steps')
    if not ms_str:
        continue
    ms = float(ms_str)
    all_med.append(ms)
    if ms <= 4:
        low_bnd.append((app, tid, ms))
    if ms >= 23:
        high_bnd.append((app, tid, ms))

print(f"  min={min(all_med)} p25={statistics.quantiles(all_med,n=4)[0]:.1f} med={statistics.median(all_med)} p75={statistics.quantiles(all_med,n=4)[2]:.1f} max={max(all_med)}")
print(f"  Histogram: " + ", ".join(f"{v}:{c}" for v,c in sorted(Counter(int(m) for m in all_med).items())))
print(f"  Tasks with median_steps in [3,4] (low-boundary risk): {len(low_bnd)}")
for app, tid, ms in sorted(low_bnd, key=lambda x:(x[2], x[0], x[1])):
    print(f"    {app}:{tid} median={ms}")
print(f"  Tasks with median_steps in [23,25] (high-boundary risk): {len(high_bnd)}")
for app, tid, ms in sorted(high_bnd, key=lambda x:(x[2], x[0], x[1])):
    print(f"    {app}:{tid} median={ms}")

# ---------------------------------------------------------------
# FOCUS 5: Suspicious patterns
# ---------------------------------------------------------------
print("\n" + "="*70)
print("FOCUS 5: Suspicious patterns")
print("="*70)
short_dur, empty_final = [], []
task_common = {}
for app, tid in passing_pairs:
    for fp in case_files(app, tid):
        c = load_case(fp)
        tr = c['trace']
        succ, dur = tr.get('success'), tr.get('durationMs', 0)
        msg = extract_msg_arg(final_send_msg(tr))
        if succ and dur is not None and dur < 15000:
            short_dur.append((app, tid, os.path.basename(fp), dur, (msg or '')[:80]))
        if succ and (msg is None or norm_answer(msg) == ''):
            empty_final.append((app, tid, os.path.basename(fp), msg))
    ans = [norm_answer(a or '') for a in all_answers[(app, tid)]]
    if ans:
        task_common[(app, tid)] = Counter(ans).most_common(1)[0][0]

print(f"  Successful cases with duration <15s: {len(short_dur)}")
for e in short_dur[:25]:
    print(f"    {e[0]}:{e[1]} [{e[2]}] dur={e[3]}ms  ans={e[4]!r}")
if len(short_dur) > 25:
    print(f"    ... and {len(short_dur)-25} more")

print(f"\n  Successful cases with empty/null final answer: {len(empty_final)}")
for e in empty_final[:20]:
    print(f"    {e[0]}:{e[1]} [{e[2]}]: ans={e[3]!r}")

ans_to_tasks = defaultdict(list)
for (app, tid), common in task_common.items():
    ans_to_tasks[common].append(f"{app}:{tid}")
print(f"\n  Normalized dominant answers shared by ≥3 distinct tasks:")
rows = [(a, ts) for a, ts in ans_to_tasks.items() if len(ts) >= 3 and len(a) < 40]
for a, ts in sorted(rows, key=lambda x: -len(x[1]))[:20]:
    print(f"    {a!r:40s}  used by {len(ts)} tasks: {ts[:8]}{'...' if len(ts)>8 else ''}")

# ---------------------------------------------------------------
# FOCUS 6: App imbalance — reddit vs gitlab drop reasons
# ---------------------------------------------------------------
print("\n" + "="*70)
print("FOCUS 6: Reddit drop-reason inspection")
print("="*70)
code_by_app = defaultdict(Counter)
tasks_by_app = defaultdict(int)
with open(FILTER_CSV) as f:
    for row in csv.DictReader(f):
        if row['app'] not in ('gitlab', 'reddit'):
            continue
        code_by_app[row['app']][row['drop_code']] += 1
        tasks_by_app[row['app']] += 1
for app in ('gitlab', 'reddit'):
    print(f"\n  {app}: total {tasks_by_app[app]} tasks")
    for code, n in sorted(code_by_app[app].items(), key=lambda x: -x[1]):
        pct = n / tasks_by_app[app] * 100
        print(f"    {code:32s}  {n:4d}  ({pct:5.1f}%)")
