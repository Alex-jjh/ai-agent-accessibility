# Deployment Guide

## CRITICAL: Burner Account Security Rules

Burner accounts will be **automatically closed** if EC2 instances have public access. You MUST:

- **NEVER** assign public IPs to EC2 instances
- **NEVER** create security groups with `0.0.0.0/0` inbound rules
- **ALWAYS** use SSM Session Manager instead of SSH
- **ALWAYS** use private subnets with NAT gateway for outbound internet

Our Terraform handles all of this automatically. Do NOT manually create EC2 instances through the AWS console — the default "Review and Launch" creates a public security group that triggers account closure.

## ⚠️ CRITICAL: AWS Profile — VERIFY BEFORE EVERY COMMAND ⚠️

**Terraform will deploy to your PERSONAL AWS account if you forget to set the profile.**
This has happened multiple times and costs real money. The provider is now locked to
`profile = "a11y-pilot"` in `main.tf`, but you MUST still configure the profile credentials.

**Before EVERY terminal session:**
```bash
# 1. Set the profile
# PowerShell:
$env:AWS_PROFILE = "a11y-pilot"
# Bash:
export AWS_PROFILE=a11y-pilot

# 2. VERIFY — do this EVERY TIME before terraform or aws commands
aws sts get-caller-identity
# ✅ Confirm the Account number is your BURNER account
# ❌ If you see 730883237142 or any personal account — STOP, fix credentials first
```

**If credentials expired:**
```bash
mwinit -o
ada credentials update --account=<BURNER_ACCOUNT_ID> --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot
```

**Rule: `aws sts get-caller-identity` before every `terraform apply/destroy` and `aws ssm`. No exceptions.**

## Quick Start (New Deployment)

```bash
# 1. Get burner account
#    Go to https://iad.merlon.amazon.dev/burner-accounts
#    Name: <username>-a11y-pilot

# 2. Get credentials
mwinit -o
ada credentials update --account=<ACCOUNT_ID> --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot

# PowerShell:
$env:AWS_PROFILE = "a11y-pilot"
# Bash:
export AWS_PROFILE=a11y-pilot

# 3. Deploy infrastructure
cd infra
terraform init
terraform apply

# 4. Connect via SSM (NOT SSH)
aws ssm start-session --target <instance-id> --region us-east-1

# 5. Bootstrap platform (on EC2)
cd ~/platform
bash scripts/bootstrap-platform.sh

# 6. Set WebArena env vars + start LiteLLM + run pilot
# (see sections below)
```

## Architecture (Private Subnet)

```
┌─────────────────────────────────────────────────┐
│ VPC 10.0.0.0/16                                 │
│                                                 │
│  ┌──────────────┐    ┌───────────────────────┐  │
│  │ Public Subnet │    │ Private Subnet        │  │
│  │ 10.0.0.0/24  │    │ 10.0.1.0/24           │  │
│  │              │    │                       │  │
│  │  NAT Gateway ├────┤  EC2 (no public IP)   │  │
│  │              │    │  ├─ Platform code      │  │
│  └──────┬───────┘    │  ├─ LiteLLM proxy     │  │
│         │            │  └─ Playwright         │  │
│  ┌──────┴───────┐    │                       │  │
│  │ IGW          │    │  VPC Endpoints:        │  │
│  └──────────────┘    │  ├─ SSM (Session Mgr)  │  │
│                      │  ├─ Bedrock Runtime    │  │
│                      │  └─ S3 Gateway         │  │
│                      └───────────────────────┘  │
└─────────────────────────────────────────────────┘
```

- EC2 in private subnet — no public IP, no SSH
- NAT gateway for outbound internet (yum, git, pip)
- VPC Endpoints for SSM, Bedrock, S3 (traffic stays on AWS backbone)
- Access via `aws ssm start-session`

## Connecting to EC2

```bash
# Shell access (replaces SSH)
aws ssm start-session --target <instance-id> --region us-east-1

# Port forwarding (access LiteLLM from local machine)
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters portNumber=4000,localPortNumber=4000 \
  --region us-east-1
```

Requires: AWS CLI v2 + Session Manager plugin installed locally.
Install plugin: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

## Platform Bootstrap (on EC2)

After SSM connect:

```bash
cd ~/platform
bash scripts/bootstrap-platform.sh
```

This script handles all known gotchas (see Known Issues below).

## WebArena Setup

WebArena runs on a separate EC2 in us-east-2 using the official AMI.

```bash
# After WebArena EC2 is up, configure Magento URLs:
ssh ubuntu@<WEBARENA_IP>  # WebArena AMI uses ubuntu user
sudo docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<WEBARENA_IP>:7770/"
sudo docker exec shopping mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://<WEBARENA_IP>:7770/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping /var/www/magento2/bin/magento cache:flush

sudo docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<WEBARENA_IP>:7780/"
sudo docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://<WEBARENA_IP>:7780/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping_admin /var/www/magento2/bin/magento cache:flush
```

Set env vars on platform EC2:
```bash
export WA_SHOPPING="http://<WEBARENA_IP>:7770"
export WA_SHOPPING_ADMIN="http://<WEBARENA_IP>:7780"
export WA_REDDIT="http://<WEBARENA_IP>:9999"
export WA_GITLAB="http://<WEBARENA_IP>:8023"
export WA_WIKIPEDIA="http://<WEBARENA_IP>:8888"
export WA_MAP="http://<WEBARENA_IP>:3000"
export WA_HOMEPAGE="http://<WEBARENA_IP>:7770"
```

## Running Experiments

```bash
# Start LiteLLM
~/.local/bin/litellm --config litellm_config.yaml --port 4000 &

# Scanner verification
node dist/verify-scanner.js

# Pilot experiment
npx tsx scripts/run-pilot.ts

# Sync results to S3
~/sync-to-s3.sh
```

## Known Issues & Solutions

### ⚠️ Wrong AWS Account = Money Burned
If you forget `$env:AWS_PROFILE = "a11y-pilot"`, Terraform deploys to your PERSONAL account. r6i.2xlarge + t3a.xlarge + NAT + VPC endpoints = ~$0.75/hr. Always run `aws sts get-caller-identity` before any AWS command. The Terraform provider is now locked to `profile = "a11y-pilot"` but you still need the credentials configured.

### Burner Account S3 403 Errors
Burner account SCPs block `GetBucketVersioning`, `GetBucketEncryption`, `GetPublicAccessBlock`. The S3 bucket versioning/encryption/public-access-block resources have been removed from Terraform. The bucket itself works fine for data storage.

### Burner Account: Public Access = Account Closure
Security groups with `0.0.0.0/0` inbound rules trigger automatic account closure. Our Terraform uses private subnets + SSM. NEVER manually create public security groups.

### Python 3.11 Required
BrowserGym uses `match/case` (Python 3.10+). Amazon Linux 2023 ships 3.9.
**Fix:** `sudo yum install -y python3.11 python3.11-pip && sudo ln -sf /usr/bin/python3.11 /usr/bin/python`

### Playwright on Amazon Linux
`--with-deps` fails (tries apt-get). Install deps manually:
```bash
sudo yum install -y nss atk at-spi2-atk cups-libs libdrm libXcomposite \
  libXdamage libXrandr mesa-libgbm pango alsa-lib libxkbcommon
npx playwright install chromium
```

### LiteLLM Proxy Dependencies
`pip install litellm` misses proxy deps. Use: `pip install --user 'litellm[proxy]'`

### Bedrock IAM: inference-profile ARN
Geo inference IDs (`us.anthropic.*`) need `inference-profile/*` in IAM, not just `foundation-model/*`.

### WebArena Docker Images Don't Exist on ghcr.io
Use the official AMI (`ami-08a862bf98e3bd7aa` in us-east-2) instead.

### WA_HOMEPAGE Required
BrowserGym asserts all WA_* env vars are set. Set `WA_HOMEPAGE` to shopping URL as fallback (no dedicated homepage service).

### Magento 302 Redirect
Magento redirects to configured base URL. Must set base URL to the actual IP after deployment. Also causes `fetch` timeout — platform uses `redirect: 'manual'` and 30s timeout.

### crypto.subtle on HTTP
WebArena runs HTTP (not HTTPS). `crypto.subtle` unavailable. DOM hashing uses djb2 instead.

### Shadow DOM Stack Overflow
Sites with deep Web Components crash `querySelectorAll('*')`. All Tier 2 metrics wrapped in `safe()` — returns 0 on error. `MAX_SHADOW_DEPTH=10`.

### tsx __name Injection
esbuild injects `__name` helper into `page.evaluate()` callbacks. Use `npm run build && node dist/...` for Scanner. `npx tsx` works for pilot runner.

### WebArena Task IDs
Numeric only: `browsergym/webarena.{0-811}`. Default mapping: shopping 0-2, reddit 100-102, gitlab 200-202, cms 300-302.

## Bedrock Model IDs

| Alias | Bedrock Geo Inference ID |
|-------|-------------------------|
| claude-opus | `us.anthropic.claude-opus-4-1-20250805-v1:0` |
| claude-sonnet | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| claude-haiku | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| nova-pro | `us.amazon.nova-pro-v1:0` |
| llama4 | `us.meta.llama4-maverick-17b-instruct-v1:0` |

## ADA Credential Refresh

Credentials expire frequently. Re-run when you get 403:
```bash
ada credentials update --account=<ACCOUNT_ID> --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot
```

## Teardown

```bash
cd infra
terraform destroy
```

Burner accounts auto-delete after 7 days regardless.
