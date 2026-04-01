# Deployment Guide

## Quick Start (New EC2)

```bash
# 1. Clone and bootstrap
git clone https://github.com/Alex-jjh/ai-agent-accessibility.git ~/platform
cd ~/platform
bash scripts/bootstrap-platform.sh

# 2. Set WebArena env vars
export WA_SHOPPING="http://<WEBARENA_IP>:7770"
export WA_SHOPPING_ADMIN="http://<WEBARENA_IP>:7780"
export WA_REDDIT="http://<WEBARENA_IP>:9999"
export WA_GITLAB="http://<WEBARENA_IP>:8023"
export WA_WIKIPEDIA="http://<WEBARENA_IP>:8888"
export WA_MAP="http://<WEBARENA_IP>:3000"
export WA_HOMEPAGE=""

# 3. Update config with WebArena IP
WEBARENA_IP=<your_ip>
sed -i "s/localhost:7770/$WEBARENA_IP:7770/g" config-pilot.yaml

# 4. Start LiteLLM
~/.local/bin/litellm --config litellm_config.yaml --port 4000 &

# 5. Run
npx tsx scripts/run-pilot.ts
```

## Infrastructure Overview

Two EC2 instances across two AWS regions:

| Instance | Region | Type | AMI | SSH User |
|----------|--------|------|-----|----------|
| Platform | us-east-1 | r6i.2xlarge | Amazon Linux 2023 | ec2-user |
| WebArena | us-east-2 | t3a.xlarge | WebArena AMI `ami-08a862bf98e3bd7aa` | ubuntu |

Supporting: S3 bucket (experiment data), IAM role (Bedrock + S3).

## Terraform Deployment

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit: set ssh_public_key_path to your RSA key

terraform init
terraform apply -var="ssh_public_key_path=<path_to_rsa_pub_key>"
```

Note: EC2 key pairs require RSA format. ECDSA keys are rejected.

## Known Issues & Solutions

### Python Version
BrowserGym requires Python 3.10+ (`match/case` syntax). Amazon Linux 2023 ships with 3.9.

**Fix:** `sudo yum install -y python3.11 python3.11-pip && sudo ln -sf /usr/bin/python3.11 /usr/bin/python`

### Playwright on Amazon Linux
`npx playwright install --with-deps` fails because it tries `apt-get` (Debian only).

**Fix:** Install system deps manually with yum:
```bash
sudo yum install -y nss atk at-spi2-atk cups-libs libdrm libXcomposite \
  libXdamage libXrandr mesa-libgbm pango alsa-lib libxkbcommon
npx playwright install chromium
```

### LiteLLM Missing Proxy Dependencies
`pip install litellm` doesn't include proxy server deps (websockets, uvicorn).

**Fix:** `pip install --user 'litellm[proxy]'`

### LiteLLM Guardrail Errors on Python 3.9
LiteLLM shows `TypeError: unsupported operand type(s) for |` errors on startup. These are Python 3.10+ syntax in optional guardrail modules.

**Impact:** None — proxy works fine, guardrails are optional.

### Bedrock IAM: inference-profile ARN
Bedrock geo inference IDs (`us.anthropic.*`) use `inference-profile` ARN, not `foundation-model`. The IAM policy must include both:
```
arn:aws:bedrock:us-east-1::foundation-model/*
arn:aws:bedrock:us-east-1:<account_id>:inference-profile/*
```

### WebArena Docker Images
The `ghcr.io/web-arena-x/webarena-*` images don't exist. Use the official WebArena AMI instead (`ami-08a862bf98e3bd7aa` in us-east-2).

### WebArena Environment Variables
BrowserGym requires these env vars to connect to WebArena:
```bash
WA_SHOPPING, WA_SHOPPING_ADMIN, WA_REDDIT, WA_GITLAB, WA_WIKIPEDIA, WA_MAP, WA_HOMEPAGE
```

### Magento Base URL Configuration
After deploying WebArena, Magento redirects to the AMI's original hostname. Must reconfigure:
```bash
ssh ubuntu@<WEBARENA_IP>
sudo docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<WEBARENA_IP>:7770/"
sudo docker exec shopping mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://<WEBARENA_IP>:7770/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping /var/www/magento2/bin/magento cache:flush

sudo docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<WEBARENA_IP>:7780/"
sudo docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://<WEBARENA_IP>:7780/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping_admin /var/www/magento2/bin/magento cache:flush
```

### GitLab 502 on First Boot
GitLab takes 3-5 minutes to initialize. If persistent 502:
```bash
sudo docker exec gitlab rm -f /var/opt/gitlab/postgresql/data/postmaster.pid
sudo docker exec -u gitlab-psql gitlab /opt/gitlab/embedded/bin/pg_resetwal -f /var/opt/gitlab/postgresql/data
sudo docker exec gitlab gitlab-ctl restart
```

### WebArena Connectivity Timeout
Magento cold-start after cache flush takes >10s. Platform uses 30s timeout for verification.

### crypto.subtle on HTTP
`crypto.subtle.digest()` requires HTTPS. WebArena runs on HTTP. DOM hashing uses djb2 instead.

### tsx vs tsc for page.evaluate
`tsx` (esbuild) injects `__name` helper into all function declarations, which breaks `page.evaluate()` in browser context. Use `npm run build && node dist/...` for Scanner verification. `npx tsx` works for pilot runner since it doesn't use `page.evaluate` directly.

### Lighthouse CDP Port
Lighthouse needs `--remote-debugging-port=9222` passed to `chromium.launch()`. The verify-scanner script handles this. In the pilot pipeline, Lighthouse failures are logged but don't block (axe-core still works).

### Shadow DOM Stack Overflow
Sites with deep Web Components (Bing, etc.) can overflow the call stack in `querySelectorAll('*')`. All Tier 2 metrics have `safe()` wrappers that return 0 on error. `MAX_SHADOW_DEPTH=10` limits recursion.

## WebArena Task IDs
Tasks are numeric: `browsergym/webarena.{0-811}`. The bridge resolves task IDs:
- Pure number → `browsergym/webarena.{N}`
- Already prefixed → used as-is

Default task mapping in `buildTasksPerApp`:
- Shopping: 0, 1, 2
- Reddit: 100, 101, 102
- GitLab: 200, 201, 202
- CMS: 300, 301, 302

## Bedrock Model IDs
Verified against AWS docs (April 2026):

| Alias | Bedrock Geo Inference ID |
|-------|-------------------------|
| claude-opus | `us.anthropic.claude-opus-4-1-20250805-v1:0` |
| claude-sonnet | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| claude-haiku | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| nova-pro | `us.amazon.nova-pro-v1:0` |
| llama4 | `us.meta.llama4-maverick-17b-instruct-v1:0` |

## Cost Estimate

| Resource | Hourly | Daily |
|----------|--------|-------|
| r6i.2xlarge (platform) | ~$0.50 | ~$12 |
| t3a.xlarge (WebArena) | ~$0.15 | ~$3.60 |
| Bedrock LLM (pilot) | — | ~$10 |
| **Total** | | **~$25/day** |

Burner accounts auto-delete after 7 days.

## Teardown

```bash
cd infra
terraform destroy -var="ssh_public_key_path=<path>"
```
