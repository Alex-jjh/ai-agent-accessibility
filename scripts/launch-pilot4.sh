#!/bin/bash
# =============================================================================
# Pilot 4 Launch Script — canonical run with Plan D variant injection
#
# 240 cases (6 tasks × 4 variants × 2 agents × 5 reps), ~12-15 hours
#
# Usage:
#   bash scripts/launch-pilot4.sh
#   bash scripts/launch-pilot4.sh --resume <runId>
#   bash scripts/launch-pilot4.sh --dry-run
#
# Monitor:
#   tail -f data/pilot4/pilot4.log
#   # Progress check from another session:
#   find data/pilot4/track-a/runs/*/cases/ -name "trace-attempt-*.json" 2>/dev/null | wc -l
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/pilot4"
LOG_FILE="$LOG_DIR/pilot4.log"
PID_FILE="$LOG_DIR/pilot4.pid"
CONFIG="./config-pilot4.yaml"

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

if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Pilot 4 is already running (PID $OLD_PID)"
    echo "  Log: tail -f $LOG_FILE"
    echo "  Stop: kill $OLD_PID"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

ARGS="$*"

if echo "$ARGS" | grep -q -- '--dry-run'; then
  echo ""
  exec npx tsx scripts/run-pilot3.ts --config "$CONFIG" $ARGS
fi

# Pre-flight: check LiteLLM
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

# Pre-flight: verify claude-sonnet-vision model
if curl -s http://localhost:4000/model/info 2>/dev/null | grep -q "claude-sonnet-vision"; then
  echo "✓ claude-sonnet-vision model available"
else
  echo "WARNING: claude-sonnet-vision not found in LiteLLM. Vision-only cases may fail."
  echo "Restart LiteLLM: pkill -f litellm && ~/.local/bin/litellm --config litellm_config.yaml --port 4000 &"
fi

echo ""
echo "Launching Pilot 4 in background (240 cases, ~12-15 hours)..."
echo "  Log:    tail -f $LOG_FILE"
echo ""

nohup bash -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"
  cd \"$PROJECT_DIR\"
  echo \"=== Pilot 4 started at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') ===\"
  echo \"Config: $CONFIG\"
  echo \"Variant injection: Plan D (context.route + deferred patch + MutationObserver)\"
  echo \"Args: $ARGS\"
  echo \"\"
  npx tsx scripts/run-pilot3.ts --config $CONFIG $ARGS
  EXIT_CODE=\$?
  echo \"\"
  echo \"=== Pilot 4 finished at \$(date -u '+%Y-%m-%d %H:%M:%S UTC') (exit \$EXIT_CODE) ===\"
  rm -f \"$PID_FILE\"
" > "$LOG_FILE" 2>&1 &

NOHUP_PID=$!
echo "$NOHUP_PID" > "$PID_FILE"

echo "Pilot 4 launched (PID $NOHUP_PID)"
echo ""
echo "Commands:"
echo "  tail -f $LOG_FILE"
echo "  kill $NOHUP_PID"
echo "  find data/pilot4/track-a/runs/*/cases/ -name 'trace-attempt-*.json' 2>/dev/null | wc -l  # progress"
