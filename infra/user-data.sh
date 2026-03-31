#!/bin/bash
# EC2 User Data — bootstraps the platform instance on first boot.
# Runs as root. Logs to /var/log/cloud-init-output.log.
set -euo pipefail

export HOME=/home/ec2-user
export GITHUB_REPO="${github_repo}"
export S3_BUCKET="${s3_bucket}"
export AWS_REGION="${aws_region}"

# --- System packages ---
yum install -y git docker python3 python3-pip
systemctl enable docker && systemctl start docker
usermod -aG docker ec2-user

# Docker Compose plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# --- Node.js 20 via nvm ---
su - ec2-user -c '
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm install 20
  echo "export NVM_DIR=\"\$HOME/.nvm\"" >> ~/.bashrc
  echo "[ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"" >> ~/.bashrc
'

# --- Clone repo + install deps ---
su - ec2-user -c "
  export NVM_DIR=\"\$HOME/.nvm\"
  [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\"

  git clone $GITHUB_REPO ~/platform
  cd ~/platform
  npm install
  npx playwright install --with-deps chromium

  # Python analysis env
  cd analysis
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  pip install browsergym-webarena gymnasium Pillow numpy
  deactivate

  # LiteLLM
  pip install --user litellm
"

# --- WebArena Docker Compose ---
su - ec2-user -c '
  mkdir -p ~/webarena
  cat > ~/webarena/docker-compose.yml << COMPOSE
version: "3.8"
services:
  reddit:
    image: ghcr.io/web-arena-x/webarena-reddit:latest
    ports: ["9999:80"]
    restart: unless-stopped
  gitlab:
    image: ghcr.io/web-arena-x/webarena-gitlab:latest
    ports: ["8023:8023"]
    restart: unless-stopped
    shm_size: "256m"
  cms:
    image: ghcr.io/web-arena-x/webarena-cms:latest
    ports: ["7770:80"]
    restart: unless-stopped
  ecommerce:
    image: ghcr.io/web-arena-x/webarena-shopping:latest
    ports: ["7780:80"]
    restart: unless-stopped
COMPOSE
'

# --- S3 sync helper script ---
su - ec2-user -c "
  cat > ~/sync-to-s3.sh << 'SYNC'
#!/bin/bash
aws s3 sync ~/platform/data/ s3://$S3_BUCKET/data/ --region $AWS_REGION
echo \"Synced to s3://$S3_BUCKET/data/\"
SYNC
  chmod +x ~/sync-to-s3.sh
"

# --- Startup instructions ---
cat > /home/ec2-user/README-quickstart.txt << 'EOF'
=== AI Agent Accessibility Platform — Quick Start ===

1. Start WebArena containers:
   cd ~/webarena && docker compose up -d
   # Wait ~2 min for GitLab to initialize

2. Start LiteLLM proxy:
   litellm --config ~/platform/litellm_config.yaml --port 4000 &

3. Verify services:
   curl -s http://localhost:9999 | head -5
   curl -s http://localhost:7780 | head -5

4. Run pilot experiment:
   cd ~/platform
   npm run build
   node dist/verify-scanner.js        # Scanner smoke test
   # node scripts/run-pilot.js        # Full pilot (needs tsc build)

5. Sync results to S3:
   ~/sync-to-s3.sh

WebArena URLs:
  Reddit:     http://localhost:9999
  GitLab:     http://localhost:8023
  CMS:        http://localhost:7770
  E-commerce: http://localhost:7780
EOF

chown ec2-user:ec2-user /home/ec2-user/README-quickstart.txt

echo "=== User data setup complete ==="
