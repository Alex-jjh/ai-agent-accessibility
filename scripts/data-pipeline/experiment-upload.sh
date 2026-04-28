#!/bin/bash
# ============================================================================
# experiment-upload.sh — Package and upload experiment data to S3
#
# Run on EC2 after an experiment completes.
#
# Usage:
#   bash scripts/data-pipeline/experiment-upload.sh <experiment-name> [data-dir]
#
# Examples:
#   bash scripts/data-pipeline/experiment-upload.sh pilot5
#   bash scripts/data-pipeline/experiment-upload.sh pilot5-cua ./data/pilot5-cua
#   bash scripts/data-pipeline/experiment-upload.sh psl-smoke ./data/psl-expanded-smoke
#
# Creates: s3://<bucket>/experiments/pilot5-20260411-143022.tar.gz
# Also uploads an uncompressed manifest for quick listing without download.
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: bash scripts/data-pipeline/experiment-upload.sh <experiment-name> [data-dir]"
    echo ""
    echo "Examples:"
    echo "  bash scripts/data-pipeline/experiment-upload.sh pilot5"
    echo "  bash scripts/data-pipeline/experiment-upload.sh pilot5-cua ./data/pilot5-cua"
    exit 1
fi

EXPERIMENT_NAME="$1"
DATA_DIR="${2:-./data}"
REGION="${AWS_REGION:-us-east-2}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE_NAME="${EXPERIMENT_NAME}-${TIMESTAMP}"

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
echo " Experiment Upload: $ARCHIVE_NAME"
echo "============================================"
echo "  Source:  $DATA_DIR"
echo "  Bucket:  s3://$S3_BUCKET"
echo ""

# ── Check data exists ──
if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: Data directory not found: $DATA_DIR"
    exit 1
fi

# ── Count files ──
FILE_COUNT=$(find "$DATA_DIR" -type f | wc -l)
DIR_SIZE=$(du -sh "$DATA_DIR" | cut -f1)
echo "  Files:   $FILE_COUNT"
echo "  Size:    $DIR_SIZE"
echo ""

# ── Create manifest (file listing with sizes) ──
MANIFEST="/tmp/${ARCHIVE_NAME}-manifest.txt"
echo "# Experiment: $EXPERIMENT_NAME" > "$MANIFEST"
echo "# Timestamp: $TIMESTAMP" >> "$MANIFEST"
echo "# Source: $DATA_DIR" >> "$MANIFEST"
echo "# Files: $FILE_COUNT" >> "$MANIFEST"
echo "# Size: $DIR_SIZE" >> "$MANIFEST"
echo "#" >> "$MANIFEST"
find "$DATA_DIR" -type f -printf '%s\t%p\n' | sort -k2 >> "$MANIFEST"

# ── Package ──
echo "[1/3] Packaging..."
ARCHIVE="/tmp/${ARCHIVE_NAME}.tar.gz"
tar -czf "$ARCHIVE" -C "$(dirname "$DATA_DIR")" "$(basename "$DATA_DIR")"
ARCHIVE_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo "  Archive: $ARCHIVE ($ARCHIVE_SIZE)"

# ── Upload ──
S3_PREFIX="s3://$S3_BUCKET/experiments"

echo "[2/3] Uploading archive..."
aws s3 cp "$ARCHIVE" "$S3_PREFIX/${ARCHIVE_NAME}.tar.gz" --region "$REGION"

echo "[3/3] Uploading manifest..."
aws s3 cp "$MANIFEST" "$S3_PREFIX/${ARCHIVE_NAME}-manifest.txt" --region "$REGION"

# ── Cleanup ──
rm -f "$ARCHIVE" "$MANIFEST"

echo ""
echo "============================================"
echo " Upload complete!"
echo "============================================"
echo ""
echo "  Archive:  $S3_PREFIX/${ARCHIVE_NAME}.tar.gz"
echo "  Manifest: $S3_PREFIX/${ARCHIVE_NAME}-manifest.txt"
echo ""
echo "  Download locally:"
echo "    bash scripts/data-pipeline/experiment-download.sh ${ARCHIVE_NAME}"
echo ""
echo "  List all experiments:"
echo "    bash scripts/data-pipeline/experiment-download.sh --list"
echo ""
