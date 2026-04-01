# Deployment Guide

## Infrastructure Overview

Two EC2 instances across two AWS regions:

| Instance | Region | Type | Purpose | SSH User |
|----------|--------|------|---------|----------|
| Platform | us-east-1 | r6i.2xlarge (8 vCPU, 64GB) | Platform code, LiteLLM proxy, Playwright | ec2-user |
| WebArena | us-east-2 | t3a.xlarge (4 vCPU, 16GB) | 4 WebArena Docker apps (pre-installed AMI) | ubuntu |

Supporting resources: VPC + subnet + IGW (us-east-1), S3 bucket (experiment data), IAM role (Bedrock + S3).

## Prerequisites

- AWS burner account (get one at https://iad.merlon.amazon.dev/burner-accounts)
- Terraform >= 1.5
- SSH key pair (RSA format, EC2 doesn't accept ECDSA)
- ADA CLI for AWS credential management

## Step 1: Get AWS Credentials

```bash
# Authenticate with Midway
mwinit -o

# Get credentials (SDO org — use conduit)
ada credentials update --account=<ACCOUNT_ID> --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot

# Set profile
# PowerShell:
$env:AWS_PROFILE = "a11y-pilot"
# Bash:
export AWS_PROFILE=a11y-pilot

# Verify
aws sts get-caller-identity
```

Note: Burner account credentials expire frequently. Re-run the `ada` command if you get 403 errors.

## Step 2: Generate SSH Key

```bash
# PowerShell (press Enter twice for empty passphrase):
ssh-keygen -t rsa -b 4096 -f C:\Users\<username>\.ssh\a11y-pilot

# Linux/Mac:
ssh-keygen -t rsa -b 4096 -f ~/.ssh/a11y-pilot -N ""
```

## Step 3: Deploy Infrastructure

```bash
cd infra
terraform init
terraform apply -var="ssh_public_key_path=C:/Users/<username>/.ssh/a11y-pilot.pub"
```

This creates all resources in both regions. First apply may hit `PendingVerification` for new accounts — wait 5-15 minutes and retry.

Outputs:
- `instance_public_ip` — Platform EC2 IP
- `webarena_public_ip` — WebArena EC2 IP
- `s3_bucket_name` — Data bucket
- `webarena_urls` — All WebArena app URLs

## Step 4: Verify Platform Instance

```bash
# SSH in (use private key, not .pub)
ssh -i ~/.ssh/a11y-pilot ec2-user@<platform_ip>

# Check bootstrap completed
tail -5 /var/log/cloud-init-output.log
# Should show: "=== User data setup complete ==="

# Install Playwright browsers (Amazon Linux needs manual deps)
sudo yum install -y nss atk at-spi2-atk cups-libs libdrm libXcomposite libXdamage libXrandr mesa-libgbm pango alsa-lib libxkbcommon
source ~/.nvm/nvm.sh
cd ~/platform
npx playwright install chromium

# Build and verify Scanner
npm run build
node dist/verify-scanner.js
```

## Step 5: Verify WebArena

```bash
# From local machine (use curl.exe on Windows to avoid PowerShell alias):
curl.exe http://<webarena_ip>:9999 -o NUL -w "Reddit: %{http_code}\n"
curl.exe http://<webarena_ip>:7770 -o NUL -w "Shopping: %{http_code}\n"
curl.exe http://<webarena_ip>:8023 -o NUL -w "GitLab: %{http_code}\n"

# Expected: Reddit 200, Shopping 302, GitLab 200 (may take 3-5 min to start)
```

If GitLab shows 502:
```bash
ssh -i ~/.ssh/a11y-pilot ubuntu@<webarena_ip>
sudo docker exec gitlab gitlab-ctl status
# If PostgreSQL issues:
sudo docker exec gitlab rm -f /var/opt/gitlab/postgresql/data/postmaster.pid
sudo docker exec -u gitlab-psql gitlab /opt/gitlab/embedded/bin/pg_resetwal -f /var/opt/gitlab/postgresql/data
sudo docker exec gitlab gitlab-ctl restart
```

## Step 6: Configure Platform to Use WebArena

On the platform instance, update config files with WebArena IP:

```bash
ssh -i ~/.ssh/a11y-pilot ec2-user@<platform_ip>
cd ~/platform

# Update configs
WEBARENA_IP=<webarena_ip>
sed -i "s/localhost:9999/$WEBARENA_IP:9999/g; s/localhost:8023/$WEBARENA_IP:8023/g; s/localhost:7770/$WEBARENA_IP:7770/g; s/localhost:7780/$WEBARENA_IP:7780/g" config.yaml config-pilot.yaml
```

## Step 7: Start LiteLLM and Run Pilot

```bash
# On platform instance
cd ~/platform

# Start LiteLLM proxy (background)
~/.local/bin/litellm --config litellm_config.yaml --port 4000 &

# Run pilot experiment
node dist/run-pilot.js

# Sync results to S3
~/sync-to-s3.sh
```

## Teardown

```bash
cd infra
terraform destroy -var="ssh_public_key_path=C:/Users/<username>/.ssh/a11y-pilot.pub"
```

Burner accounts auto-delete after 7 days regardless.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `PendingVerification` on EC2 create | New account validation, wait 5-15 min and retry `terraform apply` |
| S3 403 errors | ADA credentials expired, re-run `ada credentials update` |
| `apt-get: command not found` on Playwright install | Amazon Linux uses `yum`, install deps manually (see Step 4) |
| ECDSA key rejected by EC2 | Generate RSA key: `ssh-keygen -t rsa -b 4096` |
| WebArena Docker `manifest unknown` | ghcr.io images don't exist; use the AMI-based deployment instead |
| Bing/complex sites crash Tier 2 | Expected — graceful degradation returns 0 for affected metrics |
| `__name is not defined` in page.evaluate | Use `npm run build && node dist/...` instead of `npx tsx` |
| Lighthouse `wsEndpoint` error | Pass `--remote-debugging-port=9222` to chromium.launch() |
