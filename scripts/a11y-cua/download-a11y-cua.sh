#!/usr/bin/env bash
# Download the Reduced-A11y-CUA dataset from HuggingFace
# Target: data/a11y-cua/ (~3.89 GB)
#
# Usage: bash scripts/a11y-cua/download-a11y-cua.sh
#
# To download only metadata JSONs (much smaller, ~3 MB):
#   bash scripts/a11y-cua/download-a11y-cua.sh --metadata-only

set -e

DEST="data/a11y-cua"
REPO="berkeley-hci/Reduced-A11y-CUA"

# Ensure huggingface_hub is installed
python3.11 -c "import huggingface_hub" 2>/dev/null || {
    echo "Installing huggingface_hub..."
    python3.11 -m pip install --quiet huggingface_hub
}

if [ "$1" = "--metadata-only" ]; then
    echo "Downloading metadata JSONs only from $REPO → $DEST"
    python3.11 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='$REPO',
    repo_type='dataset',
    local_dir='$DEST',
    allow_patterns=['**/metadata_*.json'],
)
print('Done — metadata files downloaded to $DEST')
"
else
    echo "Downloading full Reduced-A11y-CUA dataset from $REPO → $DEST"
    echo "This is ~3.89 GB, may take a while..."
    python3.11 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='$REPO',
    repo_type='dataset',
    local_dir='$DEST',
)
print('Done — full dataset downloaded to $DEST')
"
fi

echo ""
echo "Dataset location: $DEST"
du -sh "$DEST" 2>/dev/null || true
