#!/bin/bash
# ============================================================================
# experiment-run-and-upload.sh — Run experiment, then auto-upload to S3
#
# Wraps any experiment command. After it finishes (success or failure),
# automatically packages and uploads the data directory to S3.
#
# Usage:
#   bash scripts/data-pipeline/experiment-run-and-upload.sh <experiment-name> <data-dir> <command...>
#
# Examples:
#   bash scripts/data-pipeline/experiment-run-and-upload.sh pilot5 ./data/pilot5 \
#       npx tsx scripts/runners/run-pilot3.ts --config configs/archive/config-pilot4.yaml
#
#   bash scripts/data-pipeline/experiment-run-and-upload.sh pilot5-cua ./data/pilot5-cua \
#       npx tsx scripts/runners/run-pilot3.ts --config configs/archive/config-pilot4-cua.yaml
#
# The launch-*.sh scripts can call this instead of raw nohup.
# ============================================================================
set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: bash scripts/data-pipeline/experiment-run-and-upload.sh <name> <data-dir> <command...>"
    exit 1
fi

EXPERIMENT_NAME="$1"
DATA_DIR="$2"
shift 2
COMMAND="$@"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Experiment: $EXPERIMENT_NAME ==="
echo "=== Data dir:   $DATA_DIR ==="
echo "=== Command:    $COMMAND ==="
echo "=== Started:    $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo ""

# Run the experiment
EXIT_CODE=0
eval "$COMMAND" || EXIT_CODE=$?

echo ""
echo "=== Experiment finished at $(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit $EXIT_CODE) ==="
echo ""

# Auto-upload regardless of exit code (partial data is still valuable)
if [ -d "$DATA_DIR" ]; then
    echo "=== Auto-uploading to S3... ==="
    bash "$SCRIPT_DIR/experiment-upload.sh" "$EXPERIMENT_NAME" "$DATA_DIR" || {
        echo "WARNING: S3 upload failed (non-fatal). Data is still in $DATA_DIR"
    }
else
    echo "WARNING: Data directory $DATA_DIR not found, skipping upload"
fi

exit $EXIT_CODE
