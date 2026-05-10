#!/bin/bash
# =============================================================================
# Stage 4b — Trace-URL SSIM replay on Burner B
# Replays the 336 replayable URLs the agents actually visited, across
# base + base2 + 26 AMT operators × 1 rep = 28 variants × 336 = 9,408 captures.
# Expected wall time: ~12-14 hours at ~5 s/capture.
# Expected cost: $0 (Playwright only, no LLM).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_DIR="$PROJECT_DIR/data/stage4b-ssim-replay"
LOG_FILE="$DATA_DIR/replay.log"
PID_FILE="$DATA_DIR/replay.pid"
UPLOAD_NAME="stage4b-ssim-replay"

cd "$PROJECT_DIR"
mkdir -p "$DATA_DIR"

# Refuse to relaunch if already running
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stage 4b already running (PID $OLD_PID)" >&2
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

echo "Launching Stage 4b SSIM replay (9,408 captures, ~12-14h)..."

nohup setsid bash -c "
  cd \"$PROJECT_DIR\"
  echo '=== Stage 4b replay started at '\$(date -u '+%Y-%m-%d %H:%M:%S UTC')' ==='
  python3.11 scripts/stage3/replay-stage3-urls.py \\
      --urls-csv results/stage3/visual-equiv/stage3-urls-dedup.csv \\
      --min-visits 1 \\
      --webarena-ip 10.0.1.50 \\
      --output $DATA_DIR
  EXIT_CODE=\$?
  echo '=== Stage 4b replay finished at '\$(date -u '+%Y-%m-%d %H:%M:%S UTC')' (exit '\$EXIT_CODE') ==='
  rm -f '$PID_FILE'
  if [ \"\$EXIT_CODE\" = \"0\" ]; then
    bash scripts/data-pipeline/experiment-upload.sh $UPLOAD_NAME $DATA_DIR || echo 'S3 upload failed (non-fatal)'
  fi
" </dev/null > "$LOG_FILE" 2>&1 &
disown

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"
echo "Stage 4b launched (PID $NOHUP_PID)"
echo "Monitor: tail -f $LOG_FILE"
