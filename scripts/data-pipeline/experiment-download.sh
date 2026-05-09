#!/bin/bash
# ============================================================================
# experiment-download.sh — Download experiment data from S3 to local machine
#
# Run on your LOCAL machine (not EC2).
#
# Usage:
#   bash scripts/data-pipeline/experiment-download.sh --list              # List available experiments
#   bash scripts/data-pipeline/experiment-download.sh <archive-name>      # Download + extract
#   bash scripts/data-pipeline/experiment-download.sh --latest             # Download most recent
#   bash scripts/data-pipeline/experiment-download.sh --latest <prefix>    # Download most recent matching prefix
#
# Examples:
#   bash scripts/data-pipeline/experiment-download.sh pilot5-20260411-143022
#   bash scripts/data-pipeline/experiment-download.sh --latest pilot5
#   bash scripts/data-pipeline/experiment-download.sh --latest
#
# Downloads to: data/<experiment-name>/  (auto-extracted)
# ============================================================================
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-a11y-pilot}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Script lives at scripts/data-pipeline/experiment-download.sh, so repo root is ../..
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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
S3_PREFIX="s3://$S3_BUCKET/experiments"

# ── List mode ──
if [ "${1:-}" = "--list" ]; then
    echo "Available experiments in $S3_PREFIX:"
    echo ""
    aws s3 ls "$S3_PREFIX/" --region "$REGION" --profile "$PROFILE" 2>/dev/null \
        | grep '\.tar\.gz$' \
        | awk '{printf "  %s  %s  %s\n", $1, $2, $4}' \
        | sed 's/\.tar\.gz$//'
    echo ""
    echo "Download with: bash scripts/data-pipeline/experiment-download.sh <name>"
    exit 0
fi

# ── Latest mode ──
if [ "${1:-}" = "--latest" ]; then
    PREFIX_FILTER="${2:-}"
    LATEST=$(aws s3 ls "$S3_PREFIX/" --region "$REGION" --profile "$PROFILE" 2>/dev/null \
        | grep '\.tar\.gz$' \
        | if [ -n "$PREFIX_FILTER" ]; then grep "$PREFIX_FILTER"; else cat; fi \
        | sort -k1,2 \
        | tail -1 \
        | awk '{print $4}' \
        | sed 's/\.tar\.gz$//')
    if [ -z "$LATEST" ]; then
        echo "ERROR: No experiments found${PREFIX_FILTER:+ matching '$PREFIX_FILTER'}"
        exit 1
    fi
    echo "Latest experiment: $LATEST"
    ARCHIVE_NAME="$LATEST"
else
    ARCHIVE_NAME="${1:-}"
fi

if [ -z "$ARCHIVE_NAME" ]; then
    echo "Usage: bash scripts/data-pipeline/experiment-download.sh <archive-name>"
    echo "       bash scripts/data-pipeline/experiment-download.sh --list"
    echo "       bash scripts/data-pipeline/experiment-download.sh --latest [prefix]"
    exit 1
fi

# Strip .tar.gz if user included it
ARCHIVE_NAME="${ARCHIVE_NAME%.tar.gz}"

echo "============================================"
echo " Experiment Download: $ARCHIVE_NAME"
echo "============================================"
echo "  Source: $S3_PREFIX/${ARCHIVE_NAME}.tar.gz"
echo ""

# ── Download ──
TMPFILE="/tmp/${ARCHIVE_NAME}.tar.gz"
echo "[1/3] Downloading..."
aws s3 cp "$S3_PREFIX/${ARCHIVE_NAME}.tar.gz" "$TMPFILE" \
    --region "$REGION" --profile "$PROFILE"

ARCHIVE_SIZE=$(du -sh "$TMPFILE" | cut -f1)
echo "  Downloaded: $ARCHIVE_SIZE"

# ── Extract ──
# Extract experiment name (strip timestamp suffix for directory name)
# pilot5-20260411-143022 -> pilot5
# pilot5-cua-20260411-143022 -> pilot5-cua
EXPERIMENT_DIR=$(echo "$ARCHIVE_NAME" | sed 's/-[0-9]\{8\}-[0-9]\{6\}$//')
TARGET_DIR="$REPO_ROOT/data/$EXPERIMENT_DIR"

echo "[2/3] Extracting to $TARGET_DIR..."
mkdir -p "$TARGET_DIR"

# tar archive contains "data/" at root, strip it
tar -xzf "$TMPFILE" -C "$TARGET_DIR" --strip-components=1

# ── Verify ──
FILE_COUNT=$(find "$TARGET_DIR" -type f | wc -l)
echo "[3/3] Extracted $FILE_COUNT files"

# ── Cleanup ──
rm -f "$TMPFILE"

echo ""
echo "============================================"
echo " Download complete!"
echo "============================================"
echo "  Location: $TARGET_DIR"
echo "  Files:    $FILE_COUNT"
echo ""
echo "  View manifest:"
echo "    aws s3 cp $S3_PREFIX/${ARCHIVE_NAME}-manifest.txt - --profile $PROFILE --region $REGION"
echo ""
