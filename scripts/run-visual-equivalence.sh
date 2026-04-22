#!/bin/bash
# One-shot visual equivalence experiment driver — runs both capture phases
# inside an existing Platform EC2 with WebArena running, auto-uploads to S3.
#
# Prerequisites on EC2:
#   - Repo checked out at /home/ssm-user/ai-agent-accessibility
#   - WebArena running at 10.0.1.50 (shopping 7770, admin 7780, reddit 9999, gitlab 8023)
#   - LiteLLM proxy running on localhost:4000 (used only for eval key)
#   - Python venv with browsergym, playwright, gymnasium, numpy, Pillow installed
#
# Run from EC2 via SSM:
#   aws ssm start-session --target <platform-instance-id>
#   cd ~/ai-agent-accessibility
#   git pull
#   bash scripts/run-visual-equivalence.sh
#
# Output: ~/ai-agent-accessibility/data/visual-equivalence/ gets uploaded to S3
# under s3://<bucket>/experiments/visual-equivalence-<timestamp>.tar.gz.
#
# Runtime estimate: ~45 min total
#   Part 1 (aggregate, 13 tasks × 2 variants × 3 reps = 78 captures): ~25 min
#   Part 2 (ablation, 4 tasks × 14 captures = 56 captures): ~15 min
#   Upload: ~2 min
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$REPO_ROOT/data/visual-equivalence"
LOG_DIR="$REPO_ROOT/data/visual-equivalence/logs"
BASE_URL="${WEBARENA_BASE_URL:-http://10.0.1.50:7770}"
REPS="${REPS:-3}"

mkdir -p "$DATA_DIR" "$LOG_DIR"

echo "=============================================="
echo "  Visual Equivalence Experiment"
echo "=============================================="
echo "Repo root:    $REPO_ROOT"
echo "Data dir:     $DATA_DIR"
echo "Base URL:     $BASE_URL"
echo "Reps/cell:    $REPS"
echo "Start time:   $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo

# Check python environment
echo "--- Environment check ---"
python3 --version || { echo "ERROR: python3 not found"; exit 1; }
python3 -c "import browsergym.webarena, gymnasium, PIL" 2>&1 || {
  echo "ERROR: missing dependencies. Install with:"
  echo "  pip install browsergym-webarena gymnasium 'browsergym[webarena]' Pillow"
  exit 1
}
echo "Python deps OK"

# Check WebArena reachability
echo
echo "--- WebArena health check ---"
for port in 7770 7780 9999 8023; do
  if curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://10.0.1.50:$port" | grep -qE "^(200|301|302|403)$"; then
    echo "  port $port: OK"
  else
    echo "  port $port: UNREACHABLE — aborting"
    exit 1
  fi
done

# Phase 1: 13-task base-vs-low aggregate
echo
echo "=============================================="
echo "  Phase 1: Aggregate capture (13 tasks × 2 variants × $REPS reps)"
echo "=============================================="
PHASE1_LOG="$LOG_DIR/phase1-aggregate.log"
PHASE1_START=$(date +%s)
python3 "$REPO_ROOT/scripts/smoke-visual-equivalence.py" \
  --base-url "$BASE_URL" \
  --variants base low \
  --reps "$REPS" \
  --output "$DATA_DIR" \
  2>&1 | tee "$PHASE1_LOG"
PHASE1_ELAPSED=$(( $(date +%s) - PHASE1_START ))
echo "Phase 1 elapsed: ${PHASE1_ELAPSED}s"

# Phase 2: per-patch ablation on 4 representative tasks
echo
echo "=============================================="
echo "  Phase 2: Per-patch ablation (4 tasks × 14 captures)"
echo "=============================================="
PHASE2_LOG="$LOG_DIR/phase2-ablation.log"
PHASE2_START=$(date +%s)
python3 "$REPO_ROOT/scripts/patch-ablation-screenshots.py" \
  --base-url "$BASE_URL" \
  --tasks 23 4 29 132 \
  --output "$DATA_DIR/ablation" \
  2>&1 | tee "$PHASE2_LOG"
PHASE2_ELAPSED=$(( $(date +%s) - PHASE2_START ))
echo "Phase 2 elapsed: ${PHASE2_ELAPSED}s"

# Summary
echo
echo "=============================================="
echo "  Summary"
echo "=============================================="
PHASE1_OK=$(python3 -c "import json; m=json.load(open('$DATA_DIR/manifest.json')); print(m['summary'].get('success', 0), '/', m['summary'].get('total', 0))" 2>/dev/null || echo "?")
PHASE2_OK=$(python3 -c "import json; m=json.load(open('$DATA_DIR/ablation/manifest.json')); print(sum(1 for r in m['records'] if r.get('success')), '/', len(m['records']))" 2>/dev/null || echo "?")
TOTAL_PNG=$(find "$DATA_DIR" -name "*.png" | wc -l)
echo "Phase 1 captures: $PHASE1_OK"
echo "Phase 2 captures: $PHASE2_OK"
echo "Total PNG files:  $TOTAL_PNG"
echo "Total elapsed:    $((PHASE1_ELAPSED + PHASE2_ELAPSED))s"

# Auto-upload to S3
echo
echo "=============================================="
echo "  Uploading to S3"
echo "=============================================="
bash "$REPO_ROOT/scripts/experiment-upload.sh" visual-equivalence "$DATA_DIR" || {
  echo "WARNING: upload failed — data is still at $DATA_DIR, upload manually:"
  echo "  bash scripts/experiment-upload.sh visual-equivalence $DATA_DIR"
  exit 1
}

echo
echo "Done. Download locally with:"
echo "  bash scripts/experiment-download.sh --latest visual-equivalence"
