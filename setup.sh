#!/usr/bin/env bash
# ============================================================
# setup.sh — reproduce the analysis environment for this repo.
#
# Creates a Python venv, installs the pinned core analysis deps, and
# checks that the (large, externally-hosted) data/ tree is present.
# After this, `make verify-all` should report 108/108 PASS.
#
# This sets up the ANALYSIS layer only (the frozen-data reproduce path:
# verify-all, figures, stats). The data-COLLECTION layer (BrowserGym,
# AWS Bedrock, LiteLLM) is not reproduced — that data is frozen.
#
# Usage:  ./setup.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

# 1. Pick a Python interpreter (prefer 3.11, fall back to python3)
PY=""
for cand in python3.11 python3.12 python3; do
  if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "ERROR: no python3 found on PATH." >&2; exit 1
fi
echo "Using interpreter: $PY ($($PY --version 2>&1))"

# 2. Create venv + install pinned core deps
if [ ! -d analysis/.venv ]; then
  echo "Creating venv at analysis/.venv ..."
  "$PY" -m venv analysis/.venv
fi
analysis/.venv/bin/python -m pip install --quiet --upgrade pip
echo "Installing core analysis dependencies ..."
analysis/.venv/bin/pip install --quiet -r analysis/requirements.txt
echo "Core dependencies installed."

# 3. Check the data/ tree is present (it lives on HuggingFace, not git)
if [ ! -d data/stage3-claude/. ] || [ -z "$(find data -name '*.json' 2>/dev/null | head -1)" ]; then
  cat >&2 <<'MSG'

WARNING: data/ looks empty or missing. The 11 GB case-data tree is hosted on
HuggingFace, not in git. Fetch it before running verify-all:

    pip install huggingface_hub
    hf download Alex-jjh/amt-accessibility-data --repo-type dataset \
        --local-dir data

Then optionally verify integrity:  shasum -c data/SHA256SUMS

MSG
else
  echo "data/ present ($(find data -name '*.json' 2>/dev/null | wc -l | tr -d ' ') JSON files found)."
fi

echo
echo "Setup complete. Next:"
echo "    source analysis/.venv/bin/activate"
echo "    make verify-all      # expect 108/108 PASS"
