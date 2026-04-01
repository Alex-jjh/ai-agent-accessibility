#!/bin/bash
# Sync pilot results to S3 bucket.
# Usage: bash scripts/sync-to-s3.sh
#   or:  S3_BUCKET=my-bucket bash scripts/sync-to-s3.sh
#
# Bucket name is resolved in order:
#   1. S3_BUCKET env var (set by user-data or manually)
#   2. Auto-detect via `aws s3 ls` (needs s3:ListAllMyBuckets)
#   3. Fail with instructions
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
DATA_DIR="${1:-./data}"

if [ -z "${S3_BUCKET:-}" ]; then
  # Try auto-detect
  BUCKET=$(aws s3 ls --region "$REGION" 2>/dev/null | grep -o 'a11y-platform-data-[^ ]*' | head -1 || true)
  if [ -z "$BUCKET" ]; then
    echo "ERROR: Could not auto-detect bucket. Set S3_BUCKET manually:"
    echo "  export S3_BUCKET=a11y-platform-data-<timestamp>"
    echo "  bash scripts/sync-to-s3.sh"
    echo ""
    echo "Find your bucket name from terraform output:"
    echo "  cd infra && terraform output s3_bucket_name"
    exit 1
  fi
else
  BUCKET="$S3_BUCKET"
fi

echo "Syncing $DATA_DIR → s3://$BUCKET/data/"
aws s3 sync "$DATA_DIR" "s3://$BUCKET/data/" --region "$REGION"
echo "Done. Synced to s3://$BUCKET/data/"
