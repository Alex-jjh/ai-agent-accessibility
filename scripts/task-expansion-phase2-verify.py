#!/usr/bin/env python3
"""Verify specific candidate tasks for Phase 2 expansion."""

import json

with open('test.raw.json') as f:
    tasks = json.load(f)

task_by_id = {t['task_id']: t for t in tasks}

# Final candidate list to verify
candidates = [
    # GitLab issue task
    180,  # "Open my latest created issue that has dependency in its title to check if it is closed" → "No"
    173,  # "Open my latest updated issue that has keyword 'better' in its title to check if it is closed"
    
    # Reddit content reading
    68,   # "Among the top 10 post in 'books' forum, show me the author name and the book name"
    69,   # "Among the top 10 post in 'books' forum, is there any post talks about supporting local book stores?"
    
    # Shopping search/category browsing
    125,  # "What is the price range of teeth grinding mouth guard in the One Stop Market?"
    229,  # "What is the price range for products from ugreen?"
    
    # Admin customer section
    208,  # "Find the customer name and email with phone number +1 2058812302"
    209,  # "Find the customer name and email with phone number 2137418080"
    
    # Admin catalog/inventory
    184,  # "Give me the name of the products that have 0 units left"
    77,   # "What is the total count of Pending reviews amongst all the reviews?"
    
    # Shopping order detail (different from 188)
    358,  # "Show me the shipping method for order number 187."
    146,  # "What is the size configuration of the picture frame I bought Sep 2022"
    
    # GitLab profile/settings
    259,  # "Get me my RSS feed token"
    349,  # "Who else have access to my repo gimmiethat.space"
    
    # Shopping product criticism (different page type)
    163,  # "What are the main criticisms of this product?"
    
    # Admin review count
    77,   # "What is the total count of Pending reviews"
    
    # GitLab repo stars
    169,  # "Tell me the full names of the repositories where I made contributions and they got the most stars?"
]

# Remove duplicates while preserving order
seen = set()
unique_candidates = []
for c in candidates:
    if c not in seen:
        seen.add(c)
        unique_candidates.append(c)

print("DETAILED VERIFICATION OF CANDIDATES")
print("=" * 80)

for tid in unique_candidates:
    t = task_by_id.get(tid)
    if not t:
        print(f"\nID={tid}: NOT FOUND!")
        continue
    
    eval_info = t.get('eval', {})
    eval_types = eval_info.get('eval_types', [])
    ref = eval_info.get('reference_answers', {})
    ref_url = eval_info.get('reference_url', '')
    program_html = eval_info.get('program_html', '')
    sites = t.get('sites', [])
    
    print(f"\nID={tid}")
    print(f"  sites: {sites}")
    print(f"  intent: {t['intent']}")
    print(f"  start_url: {t['start_url']}")
    print(f"  eval_types: {eval_types}")
    print(f"  reference_answers: {ref}")
    if ref_url:
        print(f"  reference_url: {ref_url}")
    if program_html:
        print(f"  program_html: {str(program_html)[:200]}")
    
    # Check for potential issues
    issues = []
    if 'llm_eval' in eval_types:
        issues.append("REJECT: contains llm_eval")
    if 'program_html' in eval_types:
        issues.append("WARNING: contains program_html (fragile DOM check)")
    if 'url_match' in eval_types:
        issues.append("NOTE: contains url_match (need to verify URL stability)")
    if 'fuzzy_match' in ref and ref['fuzzy_match'] == 'N/A':
        issues.append("NOTE: fuzzy_match N/A (negative answer expected)")
    if 'map' in str(sites) or 'wikipedia' in str(sites):
        issues.append("REJECT: uses map or wikipedia")
    
    # Check answer stability
    if 'must_include' in ref:
        if len(ref['must_include']) > 5:
            issues.append("WARNING: many must_include items (harder to get all)")
    
    if issues:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print(f"  ✅ No issues detected")
