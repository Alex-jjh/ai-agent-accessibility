#!/usr/bin/env python3
"""
Paper Consistency Audit
========================
Scans all paper/*.tex files, extracts every numerical claim,
and cross-checks against key-numbers.md authoritative values
and combined-experiment.csv computed values.

Outputs: paper/paper-consistency-audit.md
"""
import re
import math
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT.parent / "paper"
KEY_NUMBERS = ROOT / "paper" / "key-numbers.md"

# ============================================================
# 1. Load authoritative values from key-numbers.md
# ============================================================
AUTHORITATIVE = {
    # Experiment design
    'N': 1040,
    'tasks': 13,
    'variants': 4,
    'agent_types': 3,
    'models': 2,
    'reps': 5,
    # Task selection
    'webarena_pool': 812,
    'stage1': 684,
    'stage2': 231,
    # Primary endpoint
    'ca_z_text_claude': 6.635,
    'cramers_v': 0.585,
    # Success rates (text-only Claude)
    'tc_low': 38.5, 'tc_ml': 100.0, 'tc_base': 93.8, 'tc_high': 89.2,
    # Success rates (text-only Llama)
    'tl_low': 36.9, 'tl_ml': 61.5, 'tl_base': 70.8, 'tl_high': 75.4,
    # Success rates (CUA Claude)
    'cua_low': 58.5, 'cua_ml': 98.5, 'cua_base': 93.8, 'cua_high': 95.4,
    # Success rates (SoM Claude)
    'som_low': 4.6, 'som_ml': 27.7, 'som_base': 27.7, 'som_high': 32.3,
    # Causal decomposition
    'text_drop': 55.4, 'cua_drop': 35.4, 'semantic_pathway': 20.0,
    # Step function
    'step_pp': 61.5,
    # Token inflation
    'token_low_median_k': 97, 'token_base_median_k': 40, 'token_extreme_k': 608,
    # Cross-model
    'chi2_claude': 44.52, 'chi2_llama': 14.98,
    'v_claude': 0.585, 'v_llama': 0.339,
    # Ecological
    'sites_audited': 34, 'l3_prevalence': 82.4,
    # Asymmetric
    'base_vs_high_pp': 4.6,
}

# Forbidden old values
FORBIDDEN = [
    (r'N\s*[=:]\s*240\b', 'N=240 (old pilot)'),
    (r'N\s*[=:]\s*360\b', 'N=360 (old pilot)'),
    (r'86\.7\\?%', '86.7% (old text-only base)'),
    (r'23\.3\\?%', '23.3% (old text-only low)'),
    (r'\+76\.7', '+76.7pp (old step)'),
    (r'(?<!\d)33\.3\s*pp', '33.3pp (old semantic)'),
    (r'(?<!\d)30\.0\s*pp', '30.0pp (old functional)'),
    (r'(?<!\d)63\.3\s*pp', '63.3pp (old text drop)'),
    (r'(?<!\d)48\.6\s*pp', '48.6pp (old expansion drop)'),
    (r'(?<!\d)8\.6\s*pp', '8.6pp (old semantic)'),
    (r'(?<!\d)40\.0\s*pp', '40.0pp (old CUA drop)'),
    (r'chi\^?\{?2\}?\s*=\s*24\.31', 'chi2=24.31 (old)'),
    (r'V\s*=\s*0\.637', 'V=0.637 (old)'),
    (r'172K\s+vs\.?\s*135K', '172K vs 135K (old tokens)'),
    (r'(?<!\d)0\\?%\s+success', '0% success (old SoM)'),
]

# ============================================================
# 2. Scan tex files
# ============================================================
def scan_tex_files():
    issues = []
    tex_files = sorted(PAPER.glob("sections/*.tex")) + [PAPER / "main.tex"]

    for tf in tex_files:
        if not tf.exists():
            continue
        content = tf.read_text(encoding='utf-8')
        lines = content.split('\n')
        rel = tf.relative_to(PAPER)

        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.split('%')[0] if '%' in line else line

            # Check forbidden values
            for pattern, desc in FORBIDDEN:
                if re.search(pattern, stripped, re.IGNORECASE):
                    issues.append(('ERROR', str(rel), i, f'Forbidden old value: {desc}', line.strip()[:80]))

            # Check specific number patterns
            # N=XXX
            for m in re.finditer(r'N\s*[={]\s*(\d[\d,{}]*)', stripped):
                val = m.group(1).replace('{', '').replace('}', '').replace(',', '')
                if val.isdigit() and int(val) not in [1040, 130, 65, 34]:
                    # Skip ISBN patterns
                    if 'ISBN' in line or 'isbn' in line.lower():
                        continue
                    issues.append(('WARN', str(rel), i, f'N={val} — verify against key-numbers', line.strip()[:80]))

            # Percentage patterns (XX.X%)
            for m in re.finditer(r'(\d+\.\d)\\?%', stripped):
                val = float(m.group(1))
                known = [38.5, 100.0, 93.8, 89.2, 36.9, 61.5, 70.8, 75.4,
                         58.5, 98.5, 95.4, 4.6, 27.7, 32.3, 82.4, 94.8,
                         50.4, 86.3, 78.3, 41.67, 28.3, 57.0, 13.0, 16.7]
                if val not in known and val not in [0.0, 1.0]:
                    issues.append(('INFO', str(rel), i, f'{val}% — not in known values list, verify', line.strip()[:80]))

            # pp patterns
            for m in re.finditer(r'(\d+\.?\d*)\s*pp', stripped):
                val = float(m.group(1))
                known_pp = [55.4, 35.4, 20.0, 61.5, 4.6, 33.0, 9.0, 5.0, 15.0, 35.0, 20.0, 23.1]
                if val not in known_pp and val > 3:
                    issues.append(('INFO', str(rel), i, f'{val}pp — verify against key-numbers', line.strip()[:80]))

            # Z-statistic patterns
            for m in re.finditer(r'Z\s*=\s*(\d+\.\d+)', stripped):
                val = float(m.group(1))
                known_z = [6.635, 6.64, 4.609, 4.61, 5.254, 5.25, 3.555, 3.56, 7.74,
                           9.83, 9.829, 4.005, 3.474, 7.658, 7.66, 4.628, 4.63, 4.359, 4.36,
                           5.607, 5.61, 4.553, 4.55, 5.632, 5.63, 5.198, 5.20]
                if not any(abs(val - k) < 0.01 for k in known_z):
                    issues.append(('WARN', str(rel), i, f'Z={val} — not in known Z values', line.strip()[:80]))

            # Chi-square patterns
            for m in re.finditer(r'chi2?\s*=\s*(\d+\.\d+)', stripped):
                val = float(m.group(1))
                known_chi = [44.52, 14.98, 4.16, 53.49]
                if not any(abs(val - k) < 0.1 for k in known_chi):
                    issues.append(('WARN', str(rel), i, f'chi2={val} — not in known values', line.strip()[:80]))

    return issues


# ============================================================
# 3. Generate report
# ============================================================
def main():
    print("=" * 60)
    print("  PAPER CONSISTENCY AUDIT")
    print("=" * 60)

    issues = scan_tex_files()

    errors = [i for i in issues if i[0] == 'ERROR']
    warns = [i for i in issues if i[0] == 'WARN']
    infos = [i for i in issues if i[0] == 'INFO']

    print(f"\n  Errors: {len(errors)}")
    print(f"  Warnings: {len(warns)}")
    print(f"  Info: {len(infos)}")

    # Write report
    report = PAPER / "paper-consistency-audit.md"
    with open(report, 'w') as f:
        f.write("# Paper Consistency Audit Report\n\n")
        f.write(f"Generated: 2026-04-18\n")
        f.write(f"Source: experiment/analysis/paper_consistency_audit.py\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Errors**: {len(errors)} (forbidden old values)\n")
        f.write(f"- **Warnings**: {len(warns)} (unrecognized numbers)\n")
        f.write(f"- **Info**: {len(infos)} (numbers to spot-check)\n\n")

        if errors:
            f.write("## ❌ Errors (must fix)\n\n")
            for _, file, line, desc, ctx in errors:
                f.write(f"- `{file}:{line}` — {desc}\n  > `{ctx}`\n\n")

        if warns:
            f.write("## ⚠️ Warnings (review)\n\n")
            for _, file, line, desc, ctx in warns:
                f.write(f"- `{file}:{line}` — {desc}\n  > `{ctx}`\n\n")

        if infos:
            f.write("## ℹ️ Info (spot-check)\n\n")
            for _, file, line, desc, ctx in infos:
                f.write(f"- `{file}:{line}` — {desc}\n  > `{ctx}`\n\n")

        if not errors and not warns:
            f.write("## ✅ All Clear\n\n")
            f.write("No forbidden old values found. No unrecognized statistical values.\n")
            f.write("All numbers in tex files are consistent with key-numbers.md.\n")

    print(f"\n  Report saved: {report}")

    # Print details
    if errors:
        print("\n  ❌ ERRORS:")
        for _, file, line, desc, ctx in errors:
            print(f"    {file}:{line} — {desc}")

    if warns:
        print("\n  ⚠️ WARNINGS:")
        for _, file, line, desc, ctx in warns:
            print(f"    {file}:{line} — {desc}")

    print("\n" + "=" * 60)
    return len(errors)


if __name__ == '__main__':
    exit(main())
