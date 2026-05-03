#!/bin/bash
# Launch Pilot 4 CUA experiment (nohup wrapper for SSM sessions)
# 6 tasks × 4 variants × 1 agent (CUA) × 5 reps = 120 cases
# Estimated: ~3-4 hours, ~16M tokens via Bedrock

set -e
cd "$(dirname "$0")/.."

LOG="data/pilot4-cua.log"
mkdir -p data

echo "=== Pilot 4 CUA Launch ==="
echo "Config: configs/archive/config-pilot4-cua.yaml"
echo "Cases: 120 (6 tasks × 4 variants × 5 reps)"
echo "Log: $LOG"
echo ""

# Source nvm for node
source ~/.nvm/nvm.sh

nohup npx tsx scripts/runners/run-pilot3.ts --config configs/archive/config-pilot4-cua.yaml > "$LOG" 2>&1 &
PID=$!
echo "Started PID: $PID"
echo "$PID" > data/pilot4-cua.pid
echo "Monitor: tail -f $LOG"
echo "Kill: kill $PID"
