#!/usr/bin/env python3
"""
Verify the regenerated signature-alignment quadrant counts (SIGALIGN-1).
==========================================================================
Standalone, read-only check added during the 2026-06 adversarial-audit
remediation. It asserts that the supplementary regenerated alignment file
reproduces the four-quadrant counts reported in paper section 5.2:

    aligned_active       = 2   (L1, L5)
    aligned_null         = 13
    agent_adaptation     = 9   (includes L11 on the Claude axis)
    structural_criticality = 2 (L10, L12)

and that L11 is classified as `agent_adaptation` (NOT `aligned_active`),
which is where the legacy categorical artifact
`results/amt/signature_alignment.csv` disagrees (it tags L11 on the Llama-4
axis). The frozen legacy file is never read here; we only validate the
NEW supplementary file. Exit non-zero on mismatch.

Run:
    analysis/.venv/bin/python scripts/audit/verify_signature_alignment_regenerated.py
"""

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REGEN = ROOT / "results" / "supplementary" / "signature_alignment_regenerated.csv"

EXPECTED = {
    "aligned_active": 2,
    "aligned_null": 13,
    "agent_adaptation": 9,
    "structural_criticality": 2,
}

def main() -> int:
    if not REGEN.exists():
        print(f"ERROR: missing {REGEN}")
        return 1

    df = pd.read_csv(REGEN)
    counts = Counter(df["quadrant"])
    failed = False

    for quad, exp in EXPECTED.items():
        got = counts.get(quad, 0)
        if got != exp:
            print(f"ERROR: quadrant '{quad}' has {got}, expected {exp}")
            failed = True
        else:
            print(f"OK: quadrant '{quad}' = {got}")

    total = len(df)
    if total != 26:
        print(f"ERROR: total operators {total}, expected 26")
        failed = True
    else:
        print("OK: 26 operators total")

    l11 = df.loc[df["operator"] == "L11", "quadrant"]
    if l11.empty or l11.iloc[0] != "agent_adaptation":
        print(f"ERROR: L11 quadrant = {None if l11.empty else l11.iloc[0]}, "
              "expected agent_adaptation")
        failed = True
    else:
        print("OK: L11 = agent_adaptation (Claude axis)")

    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
