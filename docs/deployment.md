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

### Magento 302 Redirect → Chromium Connection Refused (CRITICAL)
Magento redirects to its configured `base_url`. The WebArena AMI's user-data script tries to auto-configure this using `curl metadata`, but on private subnets the metadata may return a public hostname (e.g., `ec2-3-131-244-37.us-east-2.compute.amazonaws.com`). Chromium follows the redirect to the public hostname, which is unreachable from the private subnet → `ERR_CONNECTION_REFUSED`. `curl` appears to work because `-o /dev/null` ignores the redirect body.

**Fix:** After every deploy, SSM into WebArena and manually set base URLs to the private IP:
```bash
PRIVATE_IP=<webarena_private_ip_from_terraform_output>
sudo docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://$PRIVATE_IP:7770/"
sudo docker exec shopping mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://$PRIVATE_IP:7770/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping /var/www/magento2/bin/magento cache:flush
sudo docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://$PRIVATE_IP:7780/"
sudo docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://$PRIVATE_IP:7780/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping_admin /var/www/magento2/bin/magento cache:flush
```
**Verify:** `curl -v http://<IP>:7770 2>&1 | grep Location` should show NO Location header (200, not 302).

### Python Playwright Needs Separate Browser Install
Node's `npx playwright install chromium` and Python's `python -m playwright install chromium` are independent. BrowserGym uses the Python version. You must run both:
```bash
npx playwright install chromium
python -m playwright install chromium
```

### SSM Session Doesn't Load nvm
SSM sessions use `sh` not `bash`, and don't source `.bashrc`. Node/npm/npx won't be found.
**Fix:** Bootstrap script now writes nvm loader to `.bashrc`. For existing sessions:
```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

### GitLab Takes 10-15 Minutes to Start
GitLab container shows `(unhealthy)` for up to 15 minutes on `t3a.xlarge`. Wait or `sudo docker restart gitlab`. Check with `sudo docker ps --format "table {{.Names}}\t{{.Status}}" | grep gitlab`.

### WA_MAP and WA_SHOPPING_ADMIN Env Vars
BrowserGym tries to login to ALL `WA_*` services on reset. If a service isn't running, it fails. Only set env vars for services that are actually up:
```bash
unset WA_MAP            # No map service in WebArena AMI
unset WA_SHOPPING_ADMIN # Only set if 7780 is confirmed working
```

### Bedrock Region Must Match VPC Endpoint
LiteLLM config must use the same region as the VPC endpoint (us-east-2). Using us-east-1 causes 403 because the IAM policy and VPC endpoint are in us-east-2. All `aws_region_name` in `litellm_config.yaml` must be `us-east-2`.

### Terraform Inline vs Standalone SG Rules Conflict
Never mix inline `ingress {}` blocks in `aws_security_group` with standalone `aws_security_group_rule` resources. Terraform will silently drop one set. All ingress rules are now inline in `main.tf`.

### IAM Roles Persist After State Loss
If you `terraform state rm` or lose state, IAM roles remain in AWS (they're global). Next `terraform apply` fails with `EntityAlreadyExists`. Fix: `terraform import aws_iam_role.<name> <role-name>`.

### Lighthouse CDP Port: "Could not determine browser CDP port"
Lighthouse needs a raw CDP debugging port. `chromium.launch()` doesn't expose one by default. `run-pilot.ts` now passes `--remote-debugging-port=9222` in launch args. If you still see this error, ensure no other Chromium process is using port 9222.

### BrowserGym Requires ALL 7 WA_* Env Vars
BrowserGym's `WebArenaInstance.__init__` asserts all 7 env vars exist: `WA_SHOPPING`, `WA_SHOPPING_ADMIN`, `WA_REDDIT`, `WA_GITLAB`, `WA_WIKIPEDIA`, `WA_MAP`, `WA_HOMEPAGE`. You must export ALL of them even if the service isn't running — BrowserGym checks at init time, not at use time. Set unavailable services to the IP anyway; they'll fail gracefully at task level.

### Pilot Results Location
Results are written to the `output.dataDir` path in config (default: `./data/pilot/`). Contains JSON records, CSV exports, and a manifest file. Sync to S3 with `~/sync-to-s3.sh` if configured.

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
