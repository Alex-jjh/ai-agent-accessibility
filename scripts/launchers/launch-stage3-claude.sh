#!/bin/bash
# =============================================================================
# Stage 3 — Claude Sonnet 4 × all 48 info-retrieval tasks
# Runs on burner A.
#
# 48 tasks × 26 operators × 3 reps × 1 agent = 3,744 cases
# Expected wall time: ~3.8 days
# Expected cost: ~$225
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/stage3-claude"
LOG_FILE="$LOG_DIR/stage3.log"
PID_FILE="$LOG_DIR/stage3.pid"
CONFIG="./config-stage3-claude.yaml"
UPLOAD_NAME="stage3-claude"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

cd "$PROJECT_DIR"

if ! command -v node &>/dev/null; then
  echo "ERROR: node not found."
  exit 1
fi
echo "Node: $(node --version)"
echo "Config: $CONFIG"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stage 3 Claude already running (PID $OLD_PID)"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

if ! curl -s http://localhost:4000/health >/dev/null 2>&1; then
  echo "ERROR: LiteLLM proxy not reachable at localhost:4000."
  exit 1
fi

echo "Launching Stage 3 Claude (3,744 cases, ~3.8 days)..."

nohup setsid bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Stage 3 Claude started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  npx tsx scripts/runners/run-pilot3.ts --config $CONFIG
  EXIT_CODE=\$?
  echo \"=== Stage 3 Claude finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
  if [ \"\$EXIT_CODE\" = \"0\" ]; then
    bash scripts/data-pipeline/experiment-upload.sh $UPLOAD_NAME ./data/$UPLOAD_NAME || echo 'S3 upload failed (non-fatal)'
  fi
" </dev/null > "$LOG_FILE" 2>&1 &
disown

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"
echo "Stage 3 Claude launched (PID $NOHUP_PID)"
echo "Monitor: tail -f $LOG_FILE"
