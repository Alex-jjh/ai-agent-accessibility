#!/usr/bin/env bash
# check-archival-state.sh — quick health check for the post-2026-05-14 archival state.
# Reports disk size of key dirs, presence of caches that should be absent,
# and whether the SHA-256 manifest for stage4b matches the current files.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

echo "=== disk usage (top-level) ==="
du -sh data results figures docs src scripts analysis infra scan-a11y-audit 2>/dev/null | sort -h

echo
echo "=== caches that should NOT exist (regenerable) ==="
for path in node_modules scan-a11y-audit/node_modules analysis/.venv infra/.terraform; do
  if [ -e "$path" ]; then
    echo "  PRESENT  $path  ($(du -sh "$path" | awk '{print $1}'))"
  else
    echo "  absent   $path"
  fi
done

echo
echo "=== backup state ==="
if [ -e data.zip ]; then
  echo "  data.zip present ($(du -sh data.zip | awk '{print $1}')) — user-verified full backup"
else
  echo "  WARNING  data.zip missing — user said it was the verified backup"
fi

echo
echo "=== Stage 4b SSIM manifest ==="
manifest="data/stage4b-ssim-replay.sha256"
if [ -f "$manifest" ]; then
  expected=$(wc -l < "$manifest" | tr -d ' ')
  actual=$(find data/stage4b-ssim-replay -type f 2>/dev/null | wc -l | tr -d ' ')
  echo "  manifest lines: $expected   filesystem: $actual"
  if [ "$expected" != "$actual" ]; then
    echo "  WARNING  count mismatch — re-run shasum if files changed intentionally"
  fi
else
  echo "  WARNING  $manifest absent"
fi

echo
echo "=== git rollback anchor ==="
if git rev-parse --verify --quiet refs/tags/pre-archival-2026-05-14 >/dev/null; then
  echo "  tag pre-archival-2026-05-14 present at $(git rev-parse --short refs/tags/pre-archival-2026-05-14)"
else
  echo "  WARNING  tag pre-archival-2026-05-14 missing"
fi
