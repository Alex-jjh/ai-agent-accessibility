#!/bin/bash
# =============================================================================
# Pilot 3 Launch Script — detached execution via nohup
#
# Runs the experiment in the background so it survives SSH/SSM disconnection.
# Logs go to data/pilot3/pilot3.log (stdout+stderr combined).
#
# Usage:
#   bash scripts/launch-pilot3.sh              # fresh run
#   bash scripts/launch-pilot3.sh --resume <runId>  # resume interrupted run
#   bash scripts/launch-pilot3.sh --dry-run     # preview matrix only
#
# Monitor:
#   tail -f data/pilot3/pilot3.log
#
# Check if running:
#   ps aux | grep run-pilot3
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/pilot3"
LOG_FILE="$LOG_DIR/pilot3.log"
PID_FILE="$LOG_DIR/pilot3.pid"

# Load nvm (SSM sessions don't source .bashrc)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

cd "$PROJECT_DIR"

# Verify node is available
if ! command -v node &>/dev/null; then
  echo "ERROR: node not found. Run bootstrap-platform.sh first."
  exit 1
fi
echo "Node: $(node --version)"
echo "Project: $PROJECT_DIR"

# Create log directory
mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Pilot 3 is already running (PID $OLD_PID)"
    echo "  Log: tail -f $LOG_FILE"
    echo "  Stop: kill $OLD_PID"
    exit 1
  else
    echo "Stale PID file found (process $OLD_PID not running), removing."
    rm -f "$PID_FILE"
  fi
fi

# Pass through all arguments (--resume, --dry-run, etc.)
ARGS="$*"

# Dry-run mode runs in foreground (no nohup needed)
if echo "$ARGS" | grep -q -- '--dry-run'; then
  echo ""
  exec npx tsx scripts/run-pilot3.ts $ARGS
fi

# Ensure LiteLLM proxy is running (agent needs it for LLM calls)
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
echo "Launching Pilot 3 in background..."
echo "  Log:    tail -f $LOG_FILE"
echo "  PID:    $PID_FILE"
echo ""

# Launch with nohup — survives terminal disconnect
nohup bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Pilot 3 started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  echo \"Args: $ARGS\"
  echo \"\"
  npx tsx scripts/run-pilot3.ts $ARGS
  EXIT_CODE=\$?
  echo \"\"
  echo \"=== Pilot 3 finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
" > "$LOG_FILE" 2>&1 &

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"

echo "Pilot 3 launched (PID $NOHUP_PID)"
echo ""
echo "Commands:"
echo "  tail -f $LOG_FILE          # watch progress"
echo "  kill $NOHUP_PID                      # stop experiment"
echo "  ps aux | grep run-pilot3             # check if running"
