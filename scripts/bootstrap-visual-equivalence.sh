#!/bin/bash
# =============================================================================
# Minimal Bootstrap for URL-Replay Visual Equivalence Experiment
#
# Installs ONLY what's needed for:
#   scripts/extract_agent_urls.py         (python stdlib only)
#   scripts/replay-url-screenshots.py     (playwright + Pillow)
#   scripts/replay-url-patch-ablation.py  (same)
#
# Does NOT install:
#   - LiteLLM / BrowserGym / gymnasium (not needed — direct Playwright only)
#   - Node.js / npm (not needed — TypeScript bridge not invoked)
#   - TypeScript toolchain
#
# Usage via SSM:
#   aws ssm send-command --instance-ids <platform-id> \\
#     --document-name AWS-RunShellScript \\
#     --parameters file://scripts/ssm-bootstrap-visual-equivalence.json
# =============================================================================
set -eo pipefail

# SSM non-login shells don't set $HOME or some other env vars
if [ -z "${HOME:-}" ]; then
  if [ "$(id -u)" = "0" ]; then
    export HOME=/root
  else
    export HOME=$(getent passwd "$(id -un)" | cut -d: -f6 || echo /tmp)
  fi
fi

echo "[bootstrap] HOME=$HOME USER=$(id -un) PWD=$(pwd)"
echo "[bootstrap] Starting minimal install for URL-replay..."

# 1. Python 3.11 (for modern type hints)
if ! python3.11 --version &>/dev/null; then
  echo "[1/4] Installing Python 3.11..."
  sudo yum install -y python3.11 python3.11-pip >/dev/null
fi
sudo ln -sf /usr/bin/python3.11 /usr/bin/python3 2>/dev/null || true
sudo ln -sf /usr/bin/python3.11 /usr/bin/python 2>/dev/null || true
echo "  $(python3 --version)"

# 2. System deps for chromium (Amazon Linux 2023 — yum not apt)
echo "[2/4] Installing chromium system deps..."
sudo yum install -y \
  nss atk at-spi2-atk cups-libs libdrm libXcomposite \
  libXdamage libXrandr mesa-libgbm pango alsa-lib libxkbcommon \
  >/dev/null 2>&1 || echo "  (some packages may already be present, continuing)"

# 3. Python packages: playwright + Pillow + scikit-image + ImageHash
echo "[3/4] Installing Python packages..."
python3 -m pip install --user --quiet \
  playwright Pillow numpy scikit-image ImageHash

# 4. Playwright chromium
echo "[4/4] Installing Playwright chromium..."
python3 -m playwright install chromium >/dev/null 2>&1 || {
  # Retry — sometimes the first install fails on resource-constrained fresh instances
  sleep 5
  python3 -m playwright install chromium
}

echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "Verify:"
echo "  python3 -c 'from playwright.sync_api import sync_playwright; print(\"playwright ok\")'"
echo "  python3 -c 'import PIL, numpy, skimage, imagehash; print(\"deps ok\")'"
echo ""
echo "Then run:"
echo "  cd ~/platform  # or wherever repo is cloned"
echo "  bash scripts/run-visual-equivalence.sh"
