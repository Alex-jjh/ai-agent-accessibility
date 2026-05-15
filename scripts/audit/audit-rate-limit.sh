#!/usr/bin/env bash
# Bedrock 429 rate-limit confound check (Stage 3).
# Pass --data-dir <data/stage3-claude|llama> to choose model.
# See: ../audit/README.md, ../amt/audit-rate-limit-confound.py
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec "${PYTHON:-python3.11}" scripts/amt/audit-rate-limit-confound.py "$@"
