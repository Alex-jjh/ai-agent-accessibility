#!/bin/bash
# =============================================================================
# Pilot 3b Launch Script — detached execution via nohup
#
# Same as launch-pilot3.sh but uses config-pilot3b.yaml (2 agents: text + vision)
# 240 cases, ~12 hours estimated.
#
# Usage:
#   bash scripts/launch-pilot3b.sh
#   bash scripts/launch-pilot3b.sh --resume <runId>
#   bash scripts/launch-pilot3b.sh --dry-run
#
# Monitor:
#   tail -f data/pilot3b/pilot3b.log
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/pilot3b"
LOG_FILE="$LOG_DIR/pilot3b.log"
PID_FILE="$LOG_DIR/pilot3b.pid"
CONFIG="./config-pilot3b.yaml"

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

cd "$PROJECT_DIR"

if ! command -v node &>/dev/null; then
  echo "ERROR: node not found. Run bootstrap-platform.sh first."
  exit 1
fi
echo "Node: $(node --version)"
echo "Project: $PROJECT_DIR"
echo "Config: $CONFIG"

mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Pilot 3b is already running (PID $OLD_PID)"
    echo "  Log: tail -f $LOG_FILE"
    echo "  Stop: kill $OLD_PID"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

ARGS="$*"

# Dry-run in foreground
if echo "$ARGS" | grep -q -- '--dry-run'; then
  echo ""
  exec npx tsx scripts/run-pilot3.ts --config "$CONFIG" $ARGS
fi

# Check LiteLLM
if ! curl -s http://localhost:4000/health >/dev/null 2>&1; then
  echo ""
  echo "WARNING: LiteLLM proxy not reachable at localhost:4000"
  echo "Start it first:  ~/.local/bin/litellm --config litellm_config.yaml --port 4000 &"
  echo ""
  read -p "Continue anyway? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo ""
echo "Launching Pilot 3b in background (240 cases, ~12 hours)..."
echo "  Log:    tail -f $LOG_FILE"
echo ""

nohup bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Pilot 3b started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  echo \"Config: $CONFIG\"
  echo \"Args: $ARGS\"
  echo \"\"
  npx tsx scripts/run-pilot3.ts --config $CONFIG $ARGS
  EXIT_CODE=\$?
  echo \"\"
  echo \"=== Pilot 3b finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
" > "$LOG_FILE" 2>&1 &

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"

echo "Pilot 3b launched (PID $NOHUP_PID)"
echo ""
echo "Commands:"
echo "  tail -f $LOG_FILE"
echo "  kill $NOHUP_PID"
