# Reproducing this workspace on any machine

This project is split across three hosting locations so it can be rebuilt
anywhere. Code and paper are small and live on GitHub; the 11 GB frozen data
tree lives on HuggingFace.

| Layer | Where | Size |
|---|---|--:|
| Code (this repo) | GitHub `Alex-jjh/ai-agent-accessibility` | ~35 MB |
| Paper (LaTeX) | GitHub `Alex-jjh/ai-accessibility-paper` | ~48 MB |
| Raw data (frozen) | HuggingFace dataset `alexjiang04/amt-accessibility-data` | ~11 GB |

## One-command reproduce

```bash
# prereqs: git, python3 (>=3.11 preferred), and the hf CLI
pip install -U huggingface_hub
hf auth login            # needed while the dataset is private

# from an empty workspace directory:
mkdir amt-workspace && cd amt-workspace
git clone https://github.com/Alex-jjh/ai-agent-accessibility.git
cd ai-agent-accessibility
./setup-workspace.sh     # clones paper, downloads data from HF, builds env, verifies
```

`setup-workspace.sh` will:
1. clone the code + paper repos as siblings,
2. `hf download` the data tree into `ai-agent-accessibility/data/`,
3. verify integrity against `data/SHA256SUMS` (78,424 files),
4. build the analysis venv (`setup.sh`),
5. run `make verify-all` (expect **108/108 PASS**).

## What is and isn't reproduced

**Reproduced** — the analysis layer, from the frozen data:
- `make verify-all` → re-derives every paper-critical number → `results/key-numbers.json`
- `python figures/generate_fig{3,7,8,9,10}.py` → regenerate the data figures
- `latexmk -pdf main.tex` (in the paper repo) → rebuild the PDF

**Not reproduced** — the data-collection layer (intentionally; data is frozen):
- BrowserGym / Playwright agent runs, AWS Bedrock (CUA), the LiteLLM proxy.
  Those produced the raw case JSONs that now live on HuggingFace.

## Manual steps

- **Conceptual figures** (`fig1`, `fig4`, `fig5`, `figA1`) are GPT-Image or
  hand-drawn and regenerate manually — see `figures/README.md` for the
  per-figure specs and the corrected numbers each must show.
- **Data integrity**: after any data download, `cd data && shasum -c SHA256SUMS`.

## Reproducing just the environment (data already present)

```bash
./setup.sh               # venv + pinned core deps + data presence check
source analysis/.venv/bin/activate
make verify-all
```

## Notes

- Pinned dependency set is in `analysis/requirements.txt` (core, reproduces
  108/108) and `analysis/requirements-optional.txt` (data-generation only).
- Python is pinned to 3.11 via `.python-version` (3.9 also works; the pins
  were verified on the version that produced 108/108).
- The HuggingFace dataset is **private** during double-blind review; it will
  be made public on acceptance. While private, `hf download` needs your token.
- `data.zip` (a local 2.9 GB backup of `data/`) is intentionally **not**
  uploaded — the unpacked `data/` tree on HuggingFace is the source of truth.
