#!/usr/bin/env bash
# Thin wrapper. See ../audit/README.md and ../../docs/by-stage/phase1-composite.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec "${PYTHON:-python3.11}" -m analysis.stages.phase1_composite "$@"
