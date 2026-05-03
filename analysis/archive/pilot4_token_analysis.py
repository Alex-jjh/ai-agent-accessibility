#!/usr/bin/env python3
"""ISSUE-BR-4 Token Inflation Analysis — Pilot 4 (240 traces).

Investigates whether the MutationObserver sentinel in Plan D variant injection
causes continuous re-application of high-variant patches, leading to:
  1. Duplicate skip-links accumulating in the DOM
  2. Inflated a11y tree token counts for the high variant

Expected: high variant adds ~100-500 extra tokens (ARIA labels, skip-link, scopes).
If we see 10K+ extra tokens, that confirms the MutationObserver bug.

Outputs: data/pilot4-token-analysis.md
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

CASES_DIR = Path(__file__).parent.parent / 'data' / 'pilot4-full' / 'track-a' / 'runs' / \
    'f4929214-3d48-443b-a859-dd013a737d50' / 'cases'
OUTPUT_PATH = Path(__file__).parent.parent / 'data' / 'pilot4-token-analysis.md'

VARIANTS = ['low', 'medium-low', 'base', 'high']

# ── Helpers ───────────────────────────────────────────────────────────────────

def avg(lst):
    return sum(lst) / len(lst) if lst else 0

def median(lst):
    if not lst:
        return 0
    s = sorted(lst)
    n = len(s)
    return (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]

def parse_case_name(name):
    """Parse case directory name: {site}_{variant}_{taskId}_{configIndex}_{rep}.
    Sites can contain underscores (e.g. ecommerce_admin)."""
    for v in ['medium-low', 'base', 'low', 'high']:  # medium-low first to avoid partial match
        marker = '_' + v + '_'
        idx = name.find(marker)
        if idx >= 0:
            site = name[:idx]
            rest = name[idx + len(marker):]
            parts = rest.split('_')
            if len(parts) >= 3:
                return {
                    'site': site,
                    'variant': v,
                    'taskId': parts[0],
                    'configIndex': int(parts[1]),
                    'rep': int(parts[2]),
                }
    return None

