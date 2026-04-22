#!/bin/bash
# =============================================================================
# run-visual-equivalence.sh — One-shot URL-replay visual equivalence driver
#
# Runs on Platform EC2 with WebArena docker up at 10.0.1.50. Produces
# pixel-level base-vs-low comparison data to close paper §6 Limitations item 7.
#
# Prerequisites:
#   - Python 3.11 with playwright + Pillow (bootstrap-platform.sh installs these)
#   - `playwright install chromium` (done by bootstrap)
#   - WebArena up at 10.0.1.50 (shopping 7770, admin 7780, reddit 9999, gitlab 8023)
#   - Repo cloned at ~/platform with current git HEAD
#
# Usage:
#   bash scripts/run-visual-equivalence.sh
#
# Output (auto-uploaded to S3):
#   ./data/visual-equivalence/replay/{slug}/base.png + low.png  (Part B, ~137 URLs × 2)
#   ./data/visual-equivalence/ablation-replay/{slug}/{base,patch_NN}.png  (Part C, 4 URLs × 14)
#   ./data/visual-equivalence/logs/
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$REPO_ROOT/data/visual-equivalence"
LOG_DIR="$DATA_DIR/logs"
WEBARENA_IP="${WEBARENA_IP:-10.0.1.50}"
URLS_CSV="${URLS_CSV:-$REPO_ROOT/results/visual-equivalence/agent-urls-dedup.csv}"
MIN_VISITS="${MIN_VISITS:-5}"   # Skip long-tail URLs that only one agent hit
LIMIT="${LIMIT:-0}"             # 0 = all

mkdir -p "$DATA_DIR/replay" "$DATA_DIR/ablation-replay" "$LOG_DIR"

echo "=============================================="
echo "  Visual Equivalence — URL Replay Experiment"
echo "=============================================="
echo "Repo root:     $REPO_ROOT"
echo "Data dir:      $DATA_DIR"
echo "WebArena IP:   $WEBARENA_IP"
echo "URLs CSV:      $URLS_CSV"
echo "Min visits:    $MIN_VISITS"
echo "Start time:    $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo

# Environment check
echo "--- Environment ---"
python3 --version
python3 -c "import playwright, PIL; print('playwright:', playwright.__version__)" || {
  echo "ERROR: missing deps. Install:"
  echo "  python3 -m pip install --user playwright Pillow"
  echo "  python3 -m playwright install chromium"
  exit 1
}

# WebArena health
echo
echo "--- WebArena health ---"
for port in 7770 7780 9999 8023; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "http://$WEBARENA_IP:$port")
  if [[ "$code" =~ ^(200|301|302|401|403)$ ]]; then
    echo "  port $port: OK ($code)"
  else
    echo "  port $port: BAD ($code) — aborting"
    exit 1
  fi
done

# URLs CSV check
if [ ! -f "$URLS_CSV" ]; then
  echo
  echo "URLs CSV not found. Extracting from traces..."
  python3 "$REPO_ROOT/scripts/extract_agent_urls.py" \
    --traces "$REPO_ROOT/data/expansion-cua" \
             "$REPO_ROOT/data/pilot4-cua" \
             "$REPO_ROOT/data/pilot4-full" \
             "$REPO_ROOT/data/expansion-claude" \
             "$REPO_ROOT/data/expansion-llama4" \
             "$REPO_ROOT/data/expansion-som" \
    --output "$REPO_ROOT/results/visual-equivalence"
fi

# Phase B: aggregate URL replay
echo
echo "=============================================="
echo "  Phase B: URL replay (base vs low)"
echo "=============================================="
P_B_LOG="$LOG_DIR/phase-b-replay.log"
P_B_START=$(date +%s)
PHASE_B_ARGS=(
  --urls-csv "$URLS_CSV"
  --webarena-ip "$WEBARENA_IP"
  --min-visits "$MIN_VISITS"
  --output "$DATA_DIR/replay"
)
[ "$LIMIT" -gt 0 ] && PHASE_B_ARGS+=(--limit "$LIMIT")
python3 "$REPO_ROOT/scripts/replay-url-screenshots.py" "${PHASE_B_ARGS[@]}" \
  2>&1 | tee "$P_B_LOG"
P_B_ELAPSED=$(( $(date +%s) - P_B_START ))
echo "Phase B elapsed: ${P_B_ELAPSED}s"

# Phase C: per-patch ablation
echo
echo "=============================================="
echo "  Phase C: Per-patch ablation (4 URLs × 14 captures)"
echo "=============================================="
P_C_LOG="$LOG_DIR/phase-c-ablation.log"
P_C_START=$(date +%s)
python3 "$REPO_ROOT/scripts/replay-url-patch-ablation.py" \
  --webarena-ip "$WEBARENA_IP" \
  --output "$DATA_DIR/ablation-replay" \
  2>&1 | tee "$P_C_LOG"
P_C_ELAPSED=$(( $(date +%s) - P_C_START ))
echo "Phase C elapsed: ${P_C_ELAPSED}s"

# Summary
echo
echo "=============================================="
echo "  Summary"
echo "=============================================="
PHASE_B_OK=$(python3 -c "
import json
m = json.load(open('$DATA_DIR/replay/manifest.json'))
ok = sum(1 for r in m['records'] if r['success'])
print(f\"{ok}/{len(m['records'])}\")
" 2>/dev/null || echo "?")
PHASE_C_OK=$(python3 -c "
import json
m = json.load(open('$DATA_DIR/ablation-replay/manifest.json'))
ok = sum(1 for r in m['records'] if r['success'])
print(f\"{ok}/{len(m['records'])}\")
" 2>/dev/null || echo "?")
PNG_TOTAL=$(find "$DATA_DIR" -name '*.png' | wc -l)
echo "Phase B:   $PHASE_B_OK"
echo "Phase C:   $PHASE_C_OK"
echo "Total PNG: $PNG_TOTAL"
echo "Elapsed:   $((P_B_ELAPSED + P_C_ELAPSED))s"

# Upload to S3
echo
echo "=============================================="
echo "  Uploading to S3"
echo "=============================================="
bash "$REPO_ROOT/scripts/experiment-upload.sh" visual-equivalence "$DATA_DIR" || {
  echo "WARNING: upload failed — data still at $DATA_DIR"
  exit 1
}

echo
echo "Done. Download locally with:"
echo "  bash scripts/experiment-download.sh --latest visual-equivalence"
