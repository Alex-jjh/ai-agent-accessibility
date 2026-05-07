#!/bin/bash
# =============================================================================
# Stage 3 Shard A — Claude Sonnet 4 × ecommerce + ecommerce_admin (34 tasks)
#
# 34 tasks × 26 operators × 3 reps × 1 agent = 2,652 cases
# Expected wall time: ~2.7 days
# Expected cost: ~$160
#
# Usage:
#   bash scripts/launchers/launch-stage3-claude-shard-a.sh
#
# Monitor:
#   tail -f data/stage3-claude-shard-a/stage3.log
#   find data/stage3-claude-shard-a/*/cases/ -name '*.json' 2>/dev/null | wc -l
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/stage3-claude-shard-a"
LOG_FILE="$LOG_DIR/stage3.log"
PID_FILE="$LOG_DIR/stage3.pid"
CONFIG="./config-stage3-claude-shard-a.yaml"
UPLOAD_NAME="stage3-claude-shard-a"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

cd "$PROJECT_DIR"

if ! command -v node &>/dev/null; then
  echo "ERROR: node not found. Run scripts/infra/bootstrap-platform.sh first."
  exit 1
fi
echo "Node: $(node --version)"
echo "Config: $CONFIG"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stage 3 Claude Shard A already running (PID $OLD_PID)"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

if ! curl -s http://localhost:4000/health >/dev/null 2>&1; then
  echo "ERROR: LiteLLM proxy not reachable at localhost:4000. Aborting."
  exit 1
fi

echo ""
echo "Launching Stage 3 Claude Shard A (2,652 cases, ~2.7 days)..."
echo "  Log: tail -f $LOG_FILE"
echo ""

nohup setsid bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Stage 3 Claude Shard A started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  echo \"Config: $CONFIG\"
  echo \"\"
  npx tsx scripts/runners/run-pilot3.ts --config $CONFIG
  EXIT_CODE=\$?
  echo \"\"
  echo \"=== Stage 3 Claude Shard A finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
  if [ \"\$EXIT_CODE\" = \"0\" ]; then
    bash scripts/data-pipeline/experiment-upload.sh $UPLOAD_NAME ./data/$UPLOAD_NAME || echo 'S3 upload failed (non-fatal)'
  fi
" </dev/null > "$LOG_FILE" 2>&1 &
disown

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"

echo "Stage 3 Claude Shard A launched (PID $NOHUP_PID)"
echo ""
echo "Monitor:"
echo "  tail -f $LOG_FILE"
echo "  find data/stage3-claude-shard-a/*/cases/ -name '*.json' 2>/dev/null | wc -l  # out of 2,652"
