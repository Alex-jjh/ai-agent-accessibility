#!/usr/bin/env python3.11
"""One-off check: do the 13 Mode A tasks pass the Stage 3 Gate 6+7?

Answers: which Mode A tasks would be excluded if we applied the same
state-mutation + trivial-ref filter retroactively.
"""
import json
from pathlib import Path

mode_a = [
    ('shopping_admin', '4'),
    ('shopping', '23'), ('shopping', '24'), ('shopping', '26'),
    ('reddit', '29'), ('reddit', '67'),
    ('gitlab', '132'), ('gitlab', '293'), ('gitlab', '308'),
    ('shopping_admin', '41'), ('shopping_admin', '94'), ('shopping_admin', '198'),
    ('shopping', '188'),
]

raw = json.loads(Path('test.raw.json').read_text())
meta = {str(t['task_id']): t for t in raw}

STATE_MUT = {'url_match', 'program_html'}
CANNED = {'n/a', 'none', 'null', 'done', 'yes', 'no', 'true', 'false'}


def assess(tid):
    t = meta.get(tid)
    e = t.get('eval', {}) or {}
    types = set(e.get('eval_types', []))
    ra = e.get('reference_answers', {}) or {}
    refs = []
    for k in ('must_include', 'must_exclude', 'fuzzy_match', 'exact_match'):
        v = ra.get(k)
        if isinstance(v, list):
            refs.extend(str(x) for x in v)
        elif v is not None:
            refs.append(str(v))
    state_mut = bool(types & STATE_MUT)
    trivial_ref = False
    if refs:
        trivial_ref = all(
            len(str(r).strip().lower()) <= 2 or str(r).strip().lower() in CANNED
            for r in refs
        )
    return types, refs, state_mut, trivial_ref


print(f"{'app':>16} {'task':>5} {'eval_types':20} {'refs':50}  state  trivial  verdict")
print('-' * 130)
pass_count = 0
fail_count = 0
for app, tid in mode_a:
    types, refs, sm, tr = assess(tid)
    flags = []
    if sm: flags.append('state_mutation')
    if tr: flags.append('trivial_ref')
    verdict = 'PASS' if not flags else 'FAIL: ' + ' + '.join(flags)
    if not flags:
        pass_count += 1
    else:
        fail_count += 1
    refs_str = str(refs)[:48]
    tstr = ','.join(sorted(types))
    print(f"{app:>16} {tid:>5} {tstr:20} {refs_str:50}  {sm!s:5} {tr!s:7}  {verdict}")

print()
print(f"Mode A tasks passing Gate 6+7: {pass_count}/13")
print(f"Mode A tasks failing Gate 6+7: {fail_count}/13")
