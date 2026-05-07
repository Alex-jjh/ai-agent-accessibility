#!/bin/bash
# =============================================================================
# Stage 3 Shard A — Llama 4 Maverick × ecommerce + ecommerce_admin (34 tasks)
#
# 34 tasks × 26 operators × 3 reps × 1 agent = 2,652 cases
# Expected wall time: ~2.7 days
# Expected cost: ~$110
#
# LAUNCH ONLY AFTER Claude shard A completes on the same burner
# (checks for existing claude shard A PID).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/stage3-llama-shard-a"
LOG_FILE="$LOG_DIR/stage3.log"
PID_FILE="$LOG_DIR/stage3.pid"
CLAUDE_PID_FILE="$PROJECT_DIR/data/stage3-claude-shard-a/stage3.pid"
CONFIG="./config-stage3-llama-shard-a.yaml"
UPLOAD_NAME="stage3-llama-shard-a"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

cd "$PROJECT_DIR"

# Safety check: don't launch Llama if Claude shard A still running
if [ -f "$CLAUDE_PID_FILE" ]; then
  CPID=$(cat "$CLAUDE_PID_FILE")
  if kill -0 "$CPID" 2>/dev/null; then
    echo "ERROR: Claude shard A still running (PID $CPID). Wait for completion or use --force."
    [ "${1:-}" = "--force" ] || exit 1
  fi
fi

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stage 3 Llama Shard A already running (PID $OLD_PID)"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

if ! curl -s http://localhost:4000/health >/dev/null 2>&1; then
  echo "ERROR: LiteLLM proxy not reachable at localhost:4000."
  exit 1
fi

echo "Launching Stage 3 Llama Shard A (2,652 cases, ~2.7 days)..."

nohup setsid bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Stage 3 Llama Shard A started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  npx tsx scripts/runners/run-pilot3.ts --config $CONFIG
  EXIT_CODE=\$?
  echo \"=== Stage 3 Llama Shard A finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
  if [ \"\$EXIT_CODE\" = \"0\" ]; then
    bash scripts/data-pipeline/experiment-upload.sh $UPLOAD_NAME ./data/$UPLOAD_NAME || echo 'S3 upload failed (non-fatal)'
  fi
" </dev/null > "$LOG_FILE" 2>&1 &
disown

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"
echo "Stage 3 Llama Shard A launched (PID $NOHUP_PID)"
