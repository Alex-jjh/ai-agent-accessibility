#!/bin/bash
# =============================================================================
# Smoker Shard A — shopping_admin + shopping base solvability gate
#
# 374 tasks × 1 base variant × 1 text-only agent × 3 reps = 1,122 cases
# Expected wall time: ~20-25 hours (info retrieval, single agent)
# Expected cost: ~$150
#
# PREREQUISITE: Run docker restart on WebArena EC2 first.
# See docs/smoker-docker-reset.md
#
# Usage:
#   bash scripts/launchers/launch-smoker-shard-a.sh
#   bash scripts/launchers/launch-smoker-shard-a.sh --resume <runId>
#   bash scripts/launchers/launch-smoker-shard-a.sh --dry-run
#
# Monitor:
#   tail -f data/smoker-shard-a/smoker.log
#   find data/smoker-shard-a/*/cases/ -name '*.json' 2>/dev/null | wc -l
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/smoker-shard-a"
LOG_FILE="$LOG_DIR/smoker.log"
PID_FILE="$LOG_DIR/smoker.pid"
CONFIG="./config-smoker-shard-a.yaml"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

cd "$PROJECT_DIR"

if ! command -v node &>/dev/null; then
  echo "ERROR: node not found. Run scripts/infra/bootstrap-platform.sh first."
  exit 1
fi
echo "Node: $(node --version)"
echo "Project: $PROJECT_DIR"
echo "Config: $CONFIG"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Smoker Shard A already running (PID $OLD_PID)"
    echo "  Log: tail -f $LOG_FILE"
    echo "  Stop: kill $OLD_PID"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

ARGS="$*"

if echo "$ARGS" | grep -q -- '--dry-run'; then
  exec npx tsx scripts/runners/run-pilot3.ts --config "$CONFIG" $ARGS
fi

# Pre-flight: LiteLLM check
if ! curl -s http://localhost:4000/health >/dev/null 2>&1; then
  echo "ERROR: LiteLLM proxy not reachable at localhost:4000. Aborting."
  echo "Start it first: nohup setsid ~/.local/bin/litellm --config litellm_config.yaml --port 4000 </dev/null > /tmp/litellm.log 2>&1 & disown"
  exit 1
fi

echo ""
echo "Launching Smoker Shard A (1,122 cases, ~20-25 hours)..."
echo "  Log: tail -f $LOG_FILE"
echo ""

nohup setsid bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Smoker Shard A started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  echo \"Config: $CONFIG\"
  echo \"Pre-run reset status: assumed done per docs/smoker-docker-reset.md\"
  echo \"\"
  npx tsx scripts/runners/run-pilot3.ts --config $CONFIG $ARGS
  EXIT_CODE=\$?
  echo \"\"
  echo \"=== Smoker Shard A finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
  # Auto-upload to S3 if run succeeded
  if [ \"\$EXIT_CODE\" = \"0\" ]; then
    bash scripts/data-pipeline/experiment-upload.sh smoker-shard-a ./data/smoker-shard-a || echo 'S3 upload failed (non-fatal)'
  fi
" </dev/null > "$LOG_FILE" 2>&1 &
disown

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"

echo "Smoker Shard A launched (PID $NOHUP_PID)"
echo ""
echo "Commands:"
echo "  tail -f $LOG_FILE"
echo "  kill $NOHUP_PID"
echo "  find data/smoker-shard-a/*/cases/ -name '*.json' 2>/dev/null | wc -l  # progress (out of 1122)"
