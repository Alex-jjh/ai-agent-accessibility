#!/usr/bin/env bash
# Thin wrapper. See ../audit/README.md and ../../docs/by-stage/phase3-c2.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec "${PYTHON:-python3.11}" -m analysis.stages.phase3_c2 "$@"
