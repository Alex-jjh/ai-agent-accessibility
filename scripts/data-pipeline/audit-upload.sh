#!/bin/bash
# ============================================================================
# audit-upload.sh — Package and upload an AMT DOM-signature audit run to S3
#
# Run on EC2 after an audit-operator.ts invocation completes.
# Parallel to scripts/data-pipeline/experiment-upload.sh but writes to s3://<bucket>/audits/
# instead of s3://<bucket>/experiments/, so audit runs and experiment runs
# stay organized separately.
#
# Artefact layout produced by audit-operator.ts:
#   data/amt-audit-runs/<run-id>/
#   ├── audit.json
#   ├── run.log
#   └── screenshots/*.png
#
# See docs/amt-audit-artifacts.md for the full spec.
#
# Usage:
#   bash scripts/data-pipeline/audit-upload.sh <run-id>
#
# Examples:
#   bash scripts/data-pipeline/audit-upload.sh amt-audit-1777362049706
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: bash scripts/data-pipeline/audit-upload.sh <run-id>"
    echo ""
    echo "Example:  bash scripts/data-pipeline/audit-upload.sh amt-audit-1777362049706"
    exit 1
fi

RUN_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="$REPO_ROOT/data/amt-audit-runs/$RUN_ID"
REGION="${AWS_REGION:-us-east-2}"

if [ ! -d "$RUN_DIR" ]; then
    echo "ERROR: Run directory not found: $RUN_DIR"
    exit 1
fi

# Sanity check: the run-dir should have audit.json + screenshots/
if [ ! -f "$RUN_DIR/audit.json" ]; then
    echo "ERROR: $RUN_DIR has no audit.json — is this a valid audit run?"
    exit 1
fi

# ── Find S3 bucket ──
if [ -z "${S3_BUCKET:-}" ]; then
    S3_BUCKET=$(aws s3 ls --region "$REGION" 2>/dev/null \
        | grep -o 'a11y-platform-data-[^ ]*' | head -1 || true)
    if [ -z "$S3_BUCKET" ]; then
        echo "ERROR: Cannot find S3 bucket. Set S3_BUCKET env var."
        exit 1
    fi
fi

echo "============================================"
echo " AMT Audit Upload: $RUN_ID"
echo "============================================"
echo "  Source: $RUN_DIR"
echo "  Bucket: s3://$S3_BUCKET/audits"
echo ""

FILE_COUNT=$(find "$RUN_DIR" -type f | wc -l)
DIR_SIZE=$(du -sh "$RUN_DIR" | cut -f1)
echo "  Files:  $FILE_COUNT"
echo "  Size:   $DIR_SIZE"
echo ""

# ── Manifest ──
MANIFEST="/tmp/${RUN_ID}-manifest.txt"
{
  echo "# AMT DOM-signature audit run"
  echo "# Run ID: $RUN_ID"
  echo "# Uploaded: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# Source: $RUN_DIR"
  echo "# Files: $FILE_COUNT"
  echo "# Size: $DIR_SIZE"
  echo "#"
  # Include the audit.json 'fixture' block for quick at-a-glance review
  # without downloading the whole archive.
  if command -v python3.11 >/dev/null 2>&1; then PY=python3.11
  elif command -v python3 >/dev/null 2>&1; then PY=python3
  else PY=""
  fi
  if [ -n "$PY" ]; then
    echo "# fixture:"
    "$PY" -c "import json, sys; d=json.load(open('$RUN_DIR/audit.json')); print('\n'.join('#   '+l for l in json.dumps(d.get('fixture',{}), indent=2).splitlines()))" 2>/dev/null || true
    echo "#"
  fi
  find "$RUN_DIR" -type f -printf '%s\t%p\n' | sort -k2
} > "$MANIFEST"

# ── Package ──
ARCHIVE="/tmp/${RUN_ID}.tar.gz"
echo "[1/3] Packaging..."
# Archive the run-dir itself (so extraction creates data/amt-audit-runs/<run-id>/).
tar -czf "$ARCHIVE" -C "$REPO_ROOT/data/amt-audit-runs" "$RUN_ID"
echo "  Archive: $ARCHIVE ($(du -sh "$ARCHIVE" | cut -f1))"

# ── Upload ──
S3_PREFIX="s3://$S3_BUCKET/audits"

echo "[2/3] Uploading archive..."
aws s3 cp "$ARCHIVE" "$S3_PREFIX/${RUN_ID}.tar.gz" --region "$REGION"

echo "[3/3] Uploading manifest..."
aws s3 cp "$MANIFEST" "$S3_PREFIX/${RUN_ID}-manifest.txt" --region "$REGION"

rm -f "$ARCHIVE" "$MANIFEST"

echo ""
echo "============================================"
echo " Upload complete!"
echo "============================================"
echo ""
echo "  Archive:  $S3_PREFIX/${RUN_ID}.tar.gz"
echo "  Manifest: $S3_PREFIX/${RUN_ID}-manifest.txt"
echo ""
echo "  Download locally with:"
echo "    bash scripts/data-pipeline/audit-download.sh ${RUN_ID}"
echo ""
