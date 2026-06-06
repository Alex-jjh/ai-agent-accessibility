#!/usr/bin/env bash
# check-archival-state.sh — quick health check for the post-2026-05-14 archival state.
# Reports disk size of key dirs, presence of caches that should be absent in
# an archived tree, and whether the stage4b SHA-256 manifest has the same
# *line count* as the number of files on disk. NOTE: this is a cheap count
# check (wc -l vs find | wc -l), not a content verification — it never runs
# `shasum -c`, so it catches added/removed files but not modified ones.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

echo "=== disk usage (top-level) ==="
du -sh data results figures docs src scripts analysis infra scan-a11y-audit 2>/dev/null | sort -h

echo
echo "=== regenerable caches (expected ABSENT in an archived tree) ==="
echo "    (a live dev checkout legitimately has these — analysis/.venv is"
echo "     required by verify-all — so PRESENT only matters when archiving)"
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
