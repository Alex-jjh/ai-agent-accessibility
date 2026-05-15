#!/usr/bin/env bash
# Scan paper *.tex for known forbidden / authoritative numbers.
# See: ../audit/README.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec "${PYTHON:-python3.11}" analysis/paper_consistency_audit.py "$@"
