#!/usr/bin/env bash
# ============================================================
# setup-workspace.sh — reproduce the ENTIRE workspace on a new machine.
#
# One command that wires together the three hosting locations:
#   - GitHub : code  (this repo)  + paper repo
#   - HuggingFace : the 11 GB frozen data tree
# and then builds the analysis env and runs the verifier.
#
# Layout it produces (siblings under a parent workspace dir):
#   <workspace>/
#     ├── ai-agent-accessibility/   (code; this repo)
#     │     └── data/               (downloaded from HuggingFace)
#     └── paper/                    (LaTeX paper)
#
# Usage:
#   # from an empty workspace dir:
#   curl -sSL <raw-url>/setup-workspace.sh | bash
#   # or, if you already cloned this repo:
#   cd ai-agent-accessibility && ./setup-workspace.sh
#
# Prereqs: git, python3 (>=3.11 preferred), and the `hf` CLI
#   pip install -U huggingface_hub
#   hf auth login          # needed while the dataset is private
# ============================================================
set -euo pipefail

# --- config ---------------------------------------------------
GH_USER="Alex-jjh"
HF_USER="alexjiang04"
CODE_REPO="https://github.com/${GH_USER}/ai-agent-accessibility.git"
PAPER_REPO="https://github.com/${GH_USER}/ai-accessibility-paper.git"
HF_DATASET="${HF_USER}/amt-accessibility-data"

# Resolve a workspace root. If run from inside the code repo, use its parent;
# otherwise use the current directory.
if [ -d ".git" ] && [ -f "Makefile" ] && [ -d "analysis" ]; then
  CODE_DIR="$(pwd)"
  WORKSPACE="$(cd .. && pwd)"
else
  WORKSPACE="$(pwd)"
  CODE_DIR="${WORKSPACE}/ai-agent-accessibility"
fi
echo "Workspace root: ${WORKSPACE}"

# --- locate the hf CLI (it is often not on PATH after pip --user) ---
HF="$(command -v hf || true)"
if [ -z "$HF" ]; then
  for cand in "$HOME/Library/Python/3.9/bin/hf" "$HOME/.local/bin/hf"; do
    [ -x "$cand" ] && HF="$cand" && break
  done
fi
if [ -z "$HF" ]; then
  echo "ERROR: 'hf' CLI not found. Install with: pip install -U huggingface_hub" >&2
  exit 1
fi
echo "Using hf CLI: $HF"

# --- 1. clone the two code repos ------------------------------
# The code repo is PUBLIC (anonymous clone OK). The paper repo is PRIVATE, so
# it needs a GitHub credential: either `gh auth login`, or an https token, or
# SSH. We try gh first (most robust), then plain git, then warn (the paper is
# not required to run the analysis).
cd "$WORKSPACE"
[ -d "$CODE_DIR/.git" ] || git clone "$CODE_REPO" "$CODE_DIR"

if [ ! -d "${WORKSPACE}/paper/.git" ]; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo clone "${GH_USER}/ai-accessibility-paper" "${WORKSPACE}/paper" || true
  fi
  if [ ! -d "${WORKSPACE}/paper/.git" ]; then
    git clone "$PAPER_REPO" "${WORKSPACE}/paper" || {
      echo "WARNING: could not clone the PRIVATE paper repo. Authenticate first" >&2
      echo "  (gh auth login, or a GitHub token), then re-run. The analysis" >&2
      echo "  layer below does not need the paper repo." >&2
    }
  fi
fi

# --- 2. download the data from HuggingFace --------------------
# Dataset layout: the case-corpus directories (stage3-claude/, mode-a-*/,
# c2-*/, pilot4-*/, expansion-*/, smoker-*/, stage4b-ssim-replay/, a11y-cua/,
# amt-audit-batch/, archive/, visual-equivalence/) plus README/SHA256SUMS sit
# at the dataset ROOT and map to <code>/data/. The one exception is
# scan-a11y-audit/, which maps to <code>/scan-a11y-audit/results/.
# Stage to a temp dir, then place each part.
STAGE="${CODE_DIR}/.hf-stage"
echo "Downloading data from HuggingFace (${HF_DATASET}) ..."
"$HF" download "$HF_DATASET" --repo-type dataset --local-dir "$STAGE"

echo "Placing data/ and scan-a11y-audit/ ..."
mkdir -p "${CODE_DIR}/data" "${CODE_DIR}/scan-a11y-audit/results"
# Move the ecological audit out first, then everything else becomes data/.
if [ -d "${STAGE}/scan-a11y-audit" ]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "${STAGE}/scan-a11y-audit/" "${CODE_DIR}/scan-a11y-audit/results/"
  else
    cp -R "${STAGE}/scan-a11y-audit/." "${CODE_DIR}/scan-a11y-audit/results/"
  fi
  rm -rf "${STAGE}/scan-a11y-audit"
fi
# Remaining staged content is the data corpus.
if command -v rsync >/dev/null 2>&1; then
  rsync -a "${STAGE}/" "${CODE_DIR}/data/"
else
  cp -R "${STAGE}/." "${CODE_DIR}/data/"
fi
rm -rf "$STAGE"

# --- 3. verify data integrity ---------------------------------
if [ -f "${CODE_DIR}/data/SHA256SUMS" ]; then
  echo "Verifying data integrity (SHA256SUMS) ..."
  ( cd "${CODE_DIR}/data" && shasum -c SHA256SUMS | grep -v ': OK$' || echo "  all files OK" )
else
  echo "WARNING: no SHA256SUMS found in data/; skipping integrity check." >&2
fi

# --- 4. build the analysis environment ------------------------
cd "$CODE_DIR"
./setup.sh

# --- 5. run the verifier --------------------------------------
echo
echo "Running verify-all ..."
analysis/.venv/bin/python -m analysis.verify_all | tail -12

cat <<MSG

============================================================
Workspace ready.
  code  : ${CODE_DIR}
  paper : ${WORKSPACE}/paper
  data  : ${CODE_DIR}/data  (from HuggingFace)

Next:
  cd ${CODE_DIR} && source analysis/.venv/bin/activate
  make verify-all                      # 108/108 PASS
  python figures/generate_fig8_alignment_scatter.py   # regen a figure
  cd ${WORKSPACE}/paper && latexmk -pdf main.tex       # build the paper
============================================================
MSG
