#!/bin/bash
# =============================================================================
# Platform EC2 Bootstrap Script (Amazon Linux 2023)
#
# Run this on a fresh EC2 instance after git clone.
# Handles ALL the gotchas we discovered during deployment.
#
# Usage:
#   git clone https://github.com/Alex-jjh/ai-agent-accessibility.git ~/platform
#   cd ~/platform
#   bash scripts/bootstrap-platform.sh
# =============================================================================
set -euo pipefail

echo "=== Platform Bootstrap ==="

# --- 1. Python 3.11 (BrowserGym requires 3.10+ for match/case syntax) ---
echo "[1/6] Installing Python 3.11..."
if ! python3.11 --version &>/dev/null; then
  sudo yum install -y python3.11 python3.11-pip
fi
# Make 'python' point to 3.11 (BrowserGym bridge uses 'python')
sudo ln -sf /usr/bin/python3.11 /usr/bin/python
echo "  Python: $(python --version)"

# --- 2. Node.js 20 via nvm ---
echo "[2/6] Installing Node.js 20..."
if ! command -v node &>/dev/null; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm install 20
fi
# Ensure nvm is loaded (SSM sessions don't source .bashrc)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Write nvm loader to .bashrc so future SSM sessions have node
if ! grep -q 'NVM_DIR' ~/.bashrc 2>/dev/null; then
  cat >> ~/.bashrc << 'EOF'
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
EOF
fi
echo "  Node: $(node --version)"

# --- 3. Playwright + system deps ---
echo "[3/6] Installing Playwright and system dependencies..."
# Amazon Linux uses yum, not apt — Playwright's --with-deps won't work
sudo yum install -y nss atk at-spi2-atk cups-libs libdrm libXcomposite \
  libXdamage libXrandr mesa-libgbm pango alsa-lib libxkbcommon 2>/dev/null || true

npm install
npx playwright install chromium

# --- 4. Python packages ---
echo "[4/6] Installing Python packages..."
# LiteLLM proxy (needs [proxy] extras for websockets/uvicorn)
python -m pip install --user 'litellm[proxy]'

# BrowserGym + WebArena
python -m pip install --user gymnasium browsergym-webarena Pillow numpy

# Python Playwright browsers (separate from Node's npx playwright install)
python -m playwright install chromium

# --- 5. Build TypeScript ---
echo "[5/6] Building TypeScript..."
npm run build

# --- 6. Verify ---
echo "[6/6] Verifying installation..."
echo "  Node: $(node --version)"
echo "  Python: $(python --version)"
echo "  npm test..."
npx vitest --run --reporter=dot 2>&1 | tail -3

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Next steps:"
echo "  1. Set ALL WebArena env vars (BrowserGym requires all 7, even if service is down):"
echo "     IP=<WEBARENA_PRIVATE_IP>  # from terraform output"
echo "     export WA_SHOPPING=\"http://\$IP:7770\""
echo "     export WA_SHOPPING_ADMIN=\"http://\$IP:7780\""
echo "     export WA_REDDIT=\"http://\$IP:9999\""
echo "     export WA_GITLAB=\"http://\$IP:8023\""
echo "     export WA_WIKIPEDIA=\"http://\$IP:8888\""
echo "     export WA_MAP=\"http://\$IP:3000\""
echo "     export WA_HOMEPAGE=\"http://\$IP:7770\""
echo ""
echo "  2. Start LiteLLM:"
echo "     ~/.local/bin/litellm --config litellm_config.yaml --port 4000 &"
echo ""
echo "  3. Run Scanner verification:"
echo "     node dist/verify-scanner.js"
echo ""
echo "  4. Run pilot:"
echo "     npx tsx scripts/run-pilot.ts"
