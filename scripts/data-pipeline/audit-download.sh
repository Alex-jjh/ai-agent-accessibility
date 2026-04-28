#!/bin/bash
# ============================================================================
# audit-download.sh — Download an AMT DOM-signature audit run from S3 to local
#
# Run on your LOCAL machine (not EC2).
# Parallel to scripts/experiment-download.sh but pulls from the
# s3://<bucket>/audits/ prefix (not experiments/).
#
# Usage:
#   bash scripts/data-pipeline/audit-download.sh --list            # List available runs
#   bash scripts/data-pipeline/audit-download.sh --latest          # Pull most recent
#   bash scripts/data-pipeline/audit-download.sh <run-id>          # Pull specific run
#
# Downloads to: data/amt-audit-runs/<run-id>/
# See docs/amt-audit-artifacts.md for the artefact layout.
# ============================================================================
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-a11y-pilot}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Find S3 bucket ──
find_bucket() {
    if [ -n "${S3_BUCKET:-}" ]; then
        echo "$S3_BUCKET"
        return
    fi
    local bucket
    bucket=$(aws s3 ls --region "$REGION" --profile "$PROFILE" 2>/dev/null \
        | grep -o 'a11y-platform-data-[^ ]*' | head -1 || true)
    if [ -z "$bucket" ]; then
        echo "ERROR: Cannot find S3 bucket. Set S3_BUCKET or check AWS credentials." >&2
        exit 1
    fi
    echo "$bucket"
}

S3_BUCKET=$(find_bucket)
S3_PREFIX="s3://$S3_BUCKET/audits"

# ── List mode ──
if [ "${1:-}" = "--list" ]; then
    echo "Available AMT audit runs in $S3_PREFIX:"
    echo ""
    aws s3 ls "$S3_PREFIX/" --region "$REGION" --profile "$PROFILE" 2>/dev/null \
        | grep '\.tar\.gz$' \
        | awk '{printf "  %s  %s  %s\n", $1, $2, $4}' \
        | sed 's/\.tar\.gz$//'
    echo ""
    echo "Download with: bash scripts/data-pipeline/audit-download.sh <run-id>"
    exit 0
fi

# ── Latest mode ──
if [ "${1:-}" = "--latest" ]; then
    LATEST=$(aws s3 ls "$S3_PREFIX/" --region "$REGION" --profile "$PROFILE" 2>/dev/null \
        | grep '\.tar\.gz$' \
        | sort -k1,2 \
        | tail -1 \
        | awk '{print $4}' \
        | sed 's/\.tar\.gz$//')
    if [ -z "$LATEST" ]; then
        echo "ERROR: No audit runs found in $S3_PREFIX"
        exit 1
    fi
    echo "Latest audit run: $LATEST"
    RUN_ID="$LATEST"
else
    RUN_ID="${1:-}"
fi

if [ -z "$RUN_ID" ]; then
    echo "Usage: bash scripts/data-pipeline/audit-download.sh <run-id>"
    echo "       bash scripts/data-pipeline/audit-download.sh --list"
    echo "       bash scripts/data-pipeline/audit-download.sh --latest"
    exit 1
fi

RUN_ID="${RUN_ID%.tar.gz}"

echo "============================================"
echo " AMT Audit Download: $RUN_ID"
echo "============================================"
echo "  Source: $S3_PREFIX/${RUN_ID}.tar.gz"
echo ""

TMPFILE="/tmp/${RUN_ID}.tar.gz"
echo "[1/3] Downloading..."
aws s3 cp "$S3_PREFIX/${RUN_ID}.tar.gz" "$TMPFILE" \
    --region "$REGION" --profile "$PROFILE"
echo "  Downloaded: $(du -sh "$TMPFILE" | cut -f1)"

TARGET_ROOT="$REPO_ROOT/data/amt-audit-runs"
TARGET_DIR="$TARGET_ROOT/$RUN_ID"
mkdir -p "$TARGET_ROOT"

echo "[2/3] Extracting to $TARGET_DIR..."
# Archive contains <run-id>/ at root, extract into TARGET_ROOT so that
# extraction recreates the expected data/amt-audit-runs/<run-id>/ layout.
tar -xzf "$TMPFILE" -C "$TARGET_ROOT"

FILE_COUNT=$(find "$TARGET_DIR" -type f | wc -l)
echo "[3/3] Extracted $FILE_COUNT files"

rm -f "$TMPFILE"

echo ""
echo "============================================"
echo " Download complete!"
echo "============================================"
echo "  Location: $TARGET_DIR"
echo "  Files:    $FILE_COUNT"
echo ""
echo "  View manifest:"
echo "    aws s3 cp $S3_PREFIX/${RUN_ID}-manifest.txt - --profile $PROFILE --region $REGION"
echo ""
