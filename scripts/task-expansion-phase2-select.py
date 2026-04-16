#!/usr/bin/env python3
"""Phase 2 task expansion: identify templates and select 7 diverse tasks."""

import json
from collections import defaultdict

with open('test.raw.json') as f:
    tasks = json.load(f)

with open('task-site-mapping.json') as f:
    site_map = json.load(f)

existing_ids = {4, 41, 94, 198, 23, 24, 26, 188, 29, 67, 132, 293, 308}
existing_templates = {222, 279, 285, 274, 366, 159, 214, 33, 17, 322, 329, 323}

# Build task lookup
task_by_id = {t['task_id']: t for t in tasks}

# Group candidates by intent pattern (template proxy)
def normalize_intent(intent):
    """Extract the structural pattern from an intent."""
    import re
    # Remove specific names, numbers, dates
    s = intent.lower()
    # Remove quoted strings
    s = re.sub(r'"[^"]*"', '"X"', s)
    # Remove specific product names, dates, numbers
    s = re.sub(r'\d+/\d+/\d+', 'DATE', s)
    s = re.sub(r'\d{4}', 'YEAR', s)
    s = re.sub(r'\b\d+\b', 'N', s)
    return s[:80]

# Analyze specific candidate groups
print("=" * 80)
print("TEMPLATE ANALYSIS — Grouping similar tasks")
print("=" * 80)

# Group by normalized intent
groups = defaultdict(list)
for t in tasks:
    tid = t['task_id']
    site = site_map.get(str(tid), '')
    if site not in ('shopping', 'shopping_admin', 'reddit', 'gitlab'):
        continue
    if tid in existing_ids:
        continue
    eval_types = t.get('eval', {}).get('eval_types', [])
    if 'string_match' not in eval_types or 'llm_eval' in eval_types:
        continue
    
    norm = normalize_intent(t['intent'])
    groups[norm].append(t)

# Print groups sorted by size
for norm, group_tasks in sorted(groups.items(), key=lambda x: -len(x[1])):
    if len(group_tasks) >= 2:
        ids = [t['task_id'] for t in group_tasks]
        site = site_map.get(str(ids[0]), '')
        print(f"\nTemplate ({len(group_tasks)} tasks, {site}): {norm}")
        for t in group_tasks[:3]:
            print(f"  ID={t['task_id']}: {t['intent'][:100]}")
        if len(group_tasks) > 3:
            print(f"  ... and {len(group_tasks)-3} more")

# Now analyze specific candidates for selection
print("\n" + "=" * 80)
print("CANDIDATE ANALYSIS FOR SELECTION")
print("=" * 80)

# Category 1: GitLab issue/MR tasks
print("\n--- GitLab Issue Tasks (173-182) ---")
for tid in [173, 174, 175, 176, 177, 178, 179, 180, 181, 182]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {ref}")

# Category 2: GitLab settings/profile
print("\n--- GitLab Settings/Profile ---")
for tid in [259, 349, 350]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {ref}")

# Category 3: Reddit content reading
print("\n--- Reddit Content Reading ---")
for tid in [66, 68, 69]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {ref}")

# Category 4: Shopping search/price range
print("\n--- Shopping Search/Price Range ---")
for tid in [124, 125, 126, 226, 227, 228, 229, 230, 279, 280, 281, 282]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        site = site_map.get(str(tid), '')
        print(f"  ID={tid} ({site}): {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {str(ref)[:100]}")

# Category 5: Admin customer lookup
print("\n--- Admin Customer Lookup ---")
for tid in [62, 63, 64, 65, 208, 209, 210, 211, 212]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {ref}")

# Category 6: Admin inventory/catalog
print("\n--- Admin Inventory/Catalog ---")
for tid in [77, 78, 183, 184, 185, 186, 187]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {ref}")

# Category 7: Shopping order details
print("\n--- Shopping Order Details ---")
for tid in [96, 117, 146, 148, 149, 150, 189, 190, 231, 232, 233, 334, 335, 358]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {str(ref)[:100]}")

# Category 8: Admin review analysis
print("\n--- Admin Review/Sentiment ---")
for tid in [112, 113, 114, 119, 120, 121]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {str(ref)[:100]}")

# Category 9: Shopping product criticism
print("\n--- Shopping Product Criticism ---")
for tid in [163, 164, 165, 166, 167]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {str(ref)[:100]}")

# Category 10: GitLab contributor email/details
print("\n--- GitLab Contributor Details ---")
for tid in [784, 785, 786, 787, 788]:
    t = task_by_id.get(tid)
    if t:
        ref = t.get('eval', {}).get('reference_answers', {})
        print(f"  ID={tid}: {t['intent'][:100]}")
        print(f"    start_url: {t['start_url']}")
        print(f"    eval: {t['eval']['eval_types']}, ref: {str(ref)[:100]}")
