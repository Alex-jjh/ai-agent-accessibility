#!/bin/bash
# EC2 Setup Script for AI Agent Accessibility Platform
# Target: Amazon Linux 2023 or Ubuntu 22.04, r6i.2xlarge (8 vCPU, 64GB RAM)
# Region: us-east-1 (for Bedrock access)
#
# Prerequisites:
#   - EC2 instance with IAM role that has Bedrock InvokeModel permission
#   - Security group allowing outbound HTTPS (443)
#   - At least 80GB EBS storage
#
# Usage: bash scripts/ec2-setup.sh

set -euo pipefail

echo "=== AI Agent Accessibility Platform — EC2 Setup ==="

# --- 1. System packages ---
echo "[1/7] Installing system packages..."
if command -v apt-get &>/dev/null; then
  sudo apt-get update -y
  sudo apt-get install -y curl git docker.io docker-compose-plugin python3 python3-pip python3-venv
  sudo systemctl enable docker && sudo systemctl start docker
  sudo usermod -aG docker "$USER"
elif command -v yum &>/dev/null; then
  sudo yum install -y git docker python3 python3-pip
  sudo systemctl enable docker && sudo systemctl start docker
  sudo usermod -aG docker "$USER"
  # docker compose plugin
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# --- 2. Node.js ---
echo "[2/7] Installing Node.js 20..."
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null || true
  sudo apt-get install -y nodejs 2>/dev/null || sudo yum install -y nodejs 2>/dev/null || {
    # Fallback: nvm
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm install 20
  }
fi
echo "  Node: $(node --version)"

# --- 3. Clone repo ---
echo "[3/7] Cloning repository..."
REPO_DIR="$HOME/ai-agent-accessibility"
if [ -d "$REPO_DIR" ]; then
  cd "$REPO_DIR" && git pull
else
  git clone https://github.com/Alex-jjh/ai-agent-accessibility.git "$REPO_DIR"
  cd "$REPO_DIR"
fi

# --- 4. Install TypeScript dependencies ---
echo "[4/7] Installing npm dependencies + Playwright..."
npm install
npx playwright install --with-deps chromium

# --- 5. Python environment ---
echo "[5/7] Setting up Python analysis environment..."
cd analysis
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# BrowserGym dependencies
pip install browsergym-webarena gymnasium Pillow numpy
deactivate
cd ..

# --- 6. LiteLLM ---
echo "[6/7] Installing LiteLLM..."
pip install --user litellm

# --- 7. WebArena Docker ---
echo "[7/7] Setting up WebArena Docker containers..."
WEBARENA_DIR="$HOME/webarena-docker"
if [ ! -d "$WEBARENA_DIR" ]; then
  mkdir -p "$WEBARENA_DIR"
  cat > "$WEBARENA_DIR/docker-compose.yml" << 'COMPOSE'
version: "3.8"
services:
  reddit:
    image: ghcr.io/web-arena-x/webarena-reddit:latest
    ports:
      - "9999:80"
    restart: unless-stopped

  gitlab:
    image: ghcr.io/web-arena-x/webarena-gitlab:latest
    ports:
      - "8023:8023"
    restart: unless-stopped
    shm_size: "256m"

  cms:
    image: ghcr.io/web-arena-x/webarena-cms:latest
    ports:
      - "7770:80"
    restart: unless-stopped

  ecommerce:
    image: ghcr.io/web-arena-x/webarena-shopping:latest
    ports:
      - "7780:80"
    restart: unless-stopped
COMPOSE
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Start WebArena:    cd $WEBARENA_DIR && docker compose up -d"
echo "  2. Wait ~2 min for GitLab to initialize"
echo "  3. Start LiteLLM:     litellm --config $REPO_DIR/litellm_config.yaml --port 4000 &"
echo "  4. Verify services:   curl -s http://localhost:9999 | head -5"
echo "  5. Run pilot:         cd $REPO_DIR && npx tsx scripts/run-pilot.ts"
echo ""
echo "WebArena URLs:"
echo "  Reddit:     http://localhost:9999"
echo "  GitLab:     http://localhost:8023"
echo "  CMS:        http://localhost:7770"
echo "  E-commerce: http://localhost:7780"
