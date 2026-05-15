#!/usr/bin/env python3
"""
Paper Consistency Audit — delegates to the single-source-of-truth checker.

The original implementation (pre-2026-05-15) was a hardcoded Mode A-era
whitelist of "known values" that hung on 5+ minute runs. After Stage 3
landed, every new number (N=14,768, 2,184, 89.5%, etc.) was flagged as
suspect, generating thousands of false-positive INFO/WARN entries.

The actual paper-consistency check is `scripts/amt/audit-paper-numbers.py`:
zero external dependencies, deterministic, ~30s run, 28/28 PASS as of
2026-05-15. It re-derives every numerical paper claim from raw case JSON
files in `data/{mode-a-shard-{a,b}, mode-a-llama4-textonly, c2-composition-shard-{a,b}}/`
and compares against the inline expected values from §4-§5 of the paper.

This file is preserved as the path Makefile's `audit-paper` target invokes;
it now delegates. The legacy implementation is preserved in git history
(commit 416a59d). To revive it, `git show 416a59d:analysis/paper_consistency_audit.py`.

Usage:
    python analysis/paper_consistency_audit.py
    make audit-paper          # via Makefile
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "amt" / "audit-paper-numbers.py"


def main() -> int:
    if not CHECKER.exists():
        print(f"ERROR: paper-numbers checker not found at {CHECKER}", file=sys.stderr)
        return 2
    # Pass through any CLI args
    return subprocess.call([sys.executable, str(CHECKER)] + sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
