#!/bin/bash
# ============================================================================
# deploy-new-account.sh — One-command deployment to a new AWS burner account
#
# Usage:
#   1. Get new burner account from https://iad.merlon.amazon.dev/burner-accounts
#   2. Configure credentials:
#      ada credentials update --account=<ACCOUNT_ID> --provider=conduit \
#          --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot
#   3. Enable Bedrock model access in console (Claude Sonnet 4, Haiku 3.5, etc.)
#   4. Run: bash scripts/deploy-new-account.sh
#
# What this script does:
#   - terraform init + apply (creates VPC, EC2s, IAM, S3, VPC endpoints)
#   - Waits for both EC2 instances to pass SSM health checks
#   - Prints connection commands and verification steps
#
# Fixed IPs (no config changes needed between accounts):
#   WebArena: 10.0.1.50 (Magento, Postmill, GitLab)
#   Platform: 10.0.1.51 (experiment runner)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"

echo "============================================"
echo " AI Agent Accessibility Platform — Deploy"
echo "============================================"
echo ""

# ── Step 0: Verify AWS credentials ──
echo "[0/5] Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --profile a11y-pilot --query Account --output text 2>/dev/null) || {
    echo "ERROR: AWS credentials not configured. Run:"
    echo "  ada credentials update --account=<ACCOUNT_ID> --provider=conduit \\"
    echo "      --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot"
    exit 1
}
echo "  Account: $ACCOUNT_ID"
echo "  Profile: a11y-pilot"
echo ""

# ── Step 1: Terraform init ──
echo "[1/5] Terraform init..."
cd "$INFRA_DIR"
terraform init -input=false -no-color 2>&1 | tail -3
echo ""

# ── Step 2: Terraform apply ──
echo "[2/5] Terraform apply (this takes 3-5 minutes)..."
terraform apply -auto-approve -input=false -no-color 2>&1 | tail -20
echo ""

# ── Step 3: Capture outputs ──
echo "[3/5] Capturing deployment outputs..."
PLATFORM_ID=$(terraform output -raw instance_id)
WEBARENA_ID=$(terraform output -raw webarena_instance_id)
WEBARENA_IP=$(terraform output -raw webarena_private_ip)
S3_BUCKET=$(terraform output -raw s3_bucket_name)
REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-2")

echo "  Platform EC2:  $PLATFORM_ID"
echo "  WebArena EC2:  $WEBARENA_ID"
echo "  WebArena IP:   $WEBARENA_IP (should be 10.0.1.50)"
echo "  S3 Bucket:     $S3_BUCKET"
echo "  Region:        $REGION"
echo ""

# Verify fixed IP
if [ "$WEBARENA_IP" != "10.0.1.50" ]; then
    echo "WARNING: WebArena IP is $WEBARENA_IP, expected 10.0.1.50"
    echo "Config YAML files may need updating: sed -i 's/10.0.1.50/$WEBARENA_IP/g' config*.yaml"
fi

# ── Step 4: Wait for SSM ──
echo "[4/5] Waiting for EC2 instances to register with SSM..."
echo "  (WebArena takes 2-3 min for Docker containers to start)"
for INSTANCE in "$PLATFORM_ID" "$WEBARENA_ID"; do
    echo -n "  Waiting for $INSTANCE..."
    for i in $(seq 1 30); do
        STATUS=$(aws ssm describe-instance-information \
            --filters "Key=InstanceIds,Values=$INSTANCE" \
            --query "InstanceInformationList[0].PingStatus" \
            --output text --profile a11y-pilot --region "$REGION" 2>/dev/null || echo "None")
        if [ "$STATUS" = "Online" ]; then
            echo " Online!"
            break
        fi
        echo -n "."
        sleep 10
    done
    if [ "$STATUS" != "Online" ]; then
        echo " TIMEOUT (may need a few more minutes)"
    fi
done
echo ""

# ── Step 5: Print next steps ──
echo "[5/5] Deployment complete!"
echo ""
echo "============================================"
echo " Connection Commands"
echo "============================================"
echo ""
echo "  # Connect to Platform EC2:"
echo "  aws ssm start-session --target $PLATFORM_ID --region $REGION --profile a11y-pilot"
echo ""
echo "  # Connect to WebArena EC2:"
echo "  aws ssm start-session --target $WEBARENA_ID --region $REGION --profile a11y-pilot"
echo ""
echo "============================================"
echo " Post-Deploy Verification (on Platform EC2)"
echo "============================================"
echo ""
echo "  sudo su - ec2-user"
echo "  export NVM_DIR=\"\$HOME/.nvm\" && . \"\$NVM_DIR/nvm.sh\""
echo "  cd ~/platform"
echo ""
echo "  # Verify WebArena connectivity:"
echo "  curl -s http://10.0.1.50:7770 | head -5   # Shopping"
echo "  curl -s http://10.0.1.50:7780 | head -5   # Admin"
echo "  curl -s http://10.0.1.50:9999 | head -5   # Reddit"
echo ""
echo "  # Start LiteLLM:"
echo "  ~/.local/bin/litellm --config litellm_config.yaml --port 4000 &"
echo ""
echo "  # Run smoke test:"
echo "  npx tsx scripts/run-pilot3.ts --config config-reinject-smoke.yaml"
echo ""
echo "============================================"
echo " Sync data before account expires (day 6):"
echo "  bash scripts/sync-to-s3.sh"
echo "  aws s3 sync s3://$S3_BUCKET ./data-backup/ --profile a11y-pilot"
echo "============================================"
