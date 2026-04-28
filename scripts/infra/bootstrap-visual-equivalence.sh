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

# 1. Python 3.11 (for modern type hints). DO NOT re-symlink /usr/bin/python3 —
# Amazon Linux 2023's dnf/yum are Python scripts shebang'd to /usr/bin/python3.
# Overwriting that symlink breaks dnf system-wide.
if ! python3.11 --version &>/dev/null; then
  echo "[1/4] Installing Python 3.11..."
  sudo dnf install -y python3.11 python3.11-pip >/dev/null
fi
echo "  $(python3.11 --version)"

# 2. System deps for chromium (Amazon Linux 2023 — dnf not apt)
# Key packages: nspr + nss for TLS/crypto (libnspr4.so),
# atk/at-spi2-atk for a11y bridge, cups-libs/libdrm/libX* for headless rendering
echo "[2/4] Installing chromium system deps..."
sudo dnf install -y \
  nspr nss nss-util \
  atk at-spi2-atk cups-libs libdrm \
  libXcomposite libXdamage libXrandr libXtst libXScrnSaver \
  mesa-libgbm pango alsa-lib libxkbcommon \
  >/dev/null 2>&1 || echo "  (some packages may already be present, continuing)"

# 3. Python packages: playwright + Pillow + scikit-image + ImageHash + requests
#    + scipy (Mann-Whitney U for P0-2) + lpips + torch (perceptual metric P1-1)
echo "[3/4] Installing Python packages..."
python3.11 -m pip install --user --quiet \
  playwright Pillow numpy scikit-image ImageHash requests scipy
# LPIPS + torch are large (~800MB). Install CPU-only torch to keep it small
# since we only use LPIPS for inference on screenshots, not training.
python3.11 -m pip install --user --quiet \
  "torch>=2.0" --index-url https://download.pytorch.org/whl/cpu || \
  python3.11 -m pip install --user --quiet torch
python3.11 -m pip install --user --quiet lpips

# 4. Playwright chromium — use python3.11 directly, NOT 'python3' (which stays at 3.9)
echo "[4/4] Installing Playwright chromium..."
python3.11 -m playwright install chromium >/dev/null 2>&1 || {
  sleep 5
  python3.11 -m playwright install chromium
}

echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "Verify:"
echo "  python3.11 -c 'from playwright.sync_api import sync_playwright; print(\"playwright ok\")'"
echo "  python3.11 -c 'import PIL, numpy, skimage, imagehash; print(\"deps ok\")'"
echo ""
echo "Then run:"
echo "  cd ~/platform  # or wherever repo is cloned"
echo "  PATH=/root/.local/bin:\$PATH python3.11 scripts/run-visual-equivalence.sh"
