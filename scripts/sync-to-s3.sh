#!/bin/bash
# Sync pilot results to S3 bucket.
# Usage: bash scripts/sync-to-s3.sh
#
# The bucket name is auto-detected from the EC2 instance's IAM role.
# Requires: EC2 instance with a11y-platform-ec2-role attached.
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
DATA_DIR="${1:-./data}"

# Auto-detect bucket name
BUCKET=$(aws s3 ls --region "$REGION" 2>/dev/null | grep -o 'a11y-platform-data-[^ ]*' | head -1)

if [ -z "$BUCKET" ]; then
  echo "ERROR: Could not find a11y-platform-data-* bucket. Check IAM permissions."
  exit 1
fi

echo "Syncing $DATA_DIR → s3://$BUCKET/data/"
aws s3 sync "$DATA_DIR" "s3://$BUCKET/data/" --region "$REGION"
echo "Done. Synced to s3://$BUCKET/data/"
