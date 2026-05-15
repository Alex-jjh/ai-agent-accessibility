#!/usr/bin/env bash
# Repo archival-state health check (disk size + cache absence + tag presence).
# See: ../audit/README.md, ../maintenance/check-archival-state.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec bash scripts/maintenance/check-archival-state.sh "$@"
