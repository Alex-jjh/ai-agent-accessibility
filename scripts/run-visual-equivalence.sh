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
/usr/bin/python3.11 --version
/usr/bin/python3.11 -c "from playwright.sync_api import sync_playwright; import PIL; print('playwright + PIL OK')" || {
  echo "ERROR: missing deps. Install:"
  echo "  /usr/bin/python3.11 -m pip install --user playwright Pillow requests scipy lpips torch"
  echo "  /usr/bin/python3.11 -m playwright install chromium"
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

# Phase B: aggregate URL replay (now with base2 baseline — P0-2)
echo
echo "=============================================="
echo "  Phase B: URL replay (base, base2, low — P0-2 baseline included)"
echo "=============================================="
P_B_LOG="$LOG_DIR/phase-b-replay.log"
P_B_START=$(date +%s)
PHASE_B_ARGS=(
  --urls-csv "$URLS_CSV"
  --webarena-ip "$WEBARENA_IP"
  --min-visits "$MIN_VISITS"
  --variants base base2 low
  --relogin-every 50
  --output "$DATA_DIR/replay"
)
[ "$LIMIT" -gt 0 ] && PHASE_B_ARGS+=(--limit "$LIMIT")
/usr/bin/python3.11 "$REPO_ROOT/scripts/replay-url-screenshots.py" "${PHASE_B_ARGS[@]}" \
  2>&1 | tee "$P_B_LOG"
P_B_ELAPSED=$(( $(date +%s) - P_B_START ))
echo "Phase B elapsed: ${P_B_ELAPSED}s"

# Phase C: per-patch ablation (now 15 URLs × 14 captures — P0-1)
echo
echo "=============================================="
echo "  Phase C: Per-patch ablation (15 URLs × 14 captures — P0-1)"
echo "=============================================="
P_C_LOG="$LOG_DIR/phase-c-ablation.log"
P_C_START=$(date +%s)
/usr/bin/python3.11 "$REPO_ROOT/scripts/replay-url-patch-ablation.py" \
  --webarena-ip "$WEBARENA_IP" \
  --output "$DATA_DIR/ablation-replay" \
  2>&1 | tee "$P_C_LOG"
P_C_ELAPSED=$(( $(date +%s) - P_C_START ))
echo "Phase C elapsed: ${P_C_ELAPSED}s"

# Phase D: click-probe (P1-3)
echo
echo "=============================================="
echo "  Phase D: Click-probe for Group C (P1-3)"
echo "=============================================="
P_D_LOG="$LOG_DIR/phase-d-click-probe.log"
P_D_START=$(date +%s)
/usr/bin/python3.11 "$REPO_ROOT/scripts/replay-url-click-probe.py" \
  --webarena-ip "$WEBARENA_IP" \
  --output "$DATA_DIR/click-probe" \
  2>&1 | tee "$P_D_LOG"
P_D_ELAPSED=$(( $(date +%s) - P_D_START ))
echo "Phase D elapsed: ${P_D_ELAPSED}s"

# Summary
echo
echo "=============================================="
echo "  Summary"
echo "=============================================="
PHASE_B_OK=$(/usr/bin/python3.11 -c "
import json
m = json.load(open('$DATA_DIR/replay/manifest.json'))
ok = sum(1 for r in m['records'] if r['success'])
print(f\"{ok}/{len(m['records'])}\")
" 2>/dev/null || echo "?")
PHASE_C_OK=$(/usr/bin/python3.11 -c "
import json
m = json.load(open('$DATA_DIR/ablation-replay/manifest.json'))
ok = sum(1 for r in m['records'] if r['success'])
print(f\"{ok}/{len(m['records'])}\")
" 2>/dev/null || echo "?")
PHASE_D_OK=$(/usr/bin/python3.11 -c "
import json
m = json.load(open('$DATA_DIR/click-probe/manifest.json'))
print(f\"{m.get('n_patch11_inert','?')}/{m.get('n_base_ok','?')} inert\")
" 2>/dev/null || echo "?")
PNG_TOTAL=$(find "$DATA_DIR" -name '*.png' | wc -l)
echo "Phase B:   $PHASE_B_OK"
echo "Phase C:   $PHASE_C_OK"
echo "Phase D:   $PHASE_D_OK"
echo "Total PNG: $PNG_TOTAL"
echo "Elapsed:   $((P_B_ELAPSED + P_C_ELAPSED + P_D_ELAPSED))s"

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
