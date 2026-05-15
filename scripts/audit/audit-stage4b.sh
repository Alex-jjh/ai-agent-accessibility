#!/usr/bin/env bash
# Thin wrapper. See ../audit/README.md and ../../docs/by-stage/phase6-stage4b.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec "${PYTHON:-python3.11}" -m analysis.stages.phase6_stage4b "$@"
