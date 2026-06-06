# Runbook — reproduce this workspace on any machine

The project spans three hosting locations. This runbook rebuilds the whole
workspace from them on a fresh machine.

| Layer | Where | Visibility | Size |
|---|---|---|--:|
| Code (this repo) | GitHub `Alex-jjh/ai-agent-accessibility` | **public** | ~35 MB |
| Paper (LaTeX) | GitHub `Alex-jjh/ai-accessibility-paper` | **private** | ~48 MB |
| Raw data (frozen) | HuggingFace dataset `alexjiang04/amt-accessibility-data` | **private** | ~12 GB |

## 1. Credentials you need (two)

Because the paper repo and the dataset are private, a new machine needs **two**
credentials. (The code repo is public — no credential needed for it.)

| Credential | For | How |
|---|---|---|
| **GitHub** | cloning the private *paper* repo | `gh auth login` (recommended), or an https Personal Access Token with `repo` scope, or an SSH key registered on GitHub |
| **HuggingFace** | downloading the private *data* | `hf auth login` — paste a token from <https://huggingface.co/settings/tokens> (read scope is enough) |

> When the paper repo and dataset are made public (on acceptance), **no
> credentials are required** — anyone can reproduce anonymously.

## 2. Where the data lands

The data does **not** live at a top-level path; it lands **inside the code
repo**, because `analysis/lib/load.py`, `make verify-all`, and the figure
generators all read from `data/` relative to the code-repo root:

```
<workspace>/                       # any empty dir you pick, e.g. ~/amt-workspace
├── ai-agent-accessibility/        # cloned from GitHub (public)
│   ├── data/                      # <-- DATA LANDS HERE (stage3-claude/, mode-a-*/, c2-*/, ...)
│   └── scan-a11y-audit/results/   # <-- ecological-audit JSON lands here
└── paper/                         # cloned from GitHub (private)
```

So the reproduce path is **`<workspace>/ai-agent-accessibility/data/`**, not a
root path.

Note: on HuggingFace the corpus dirs sit at the dataset *root* (no `data/`
prefix — an artifact of how the folder was uploaded). `setup-workspace.sh`
moves them into `data/` and routes `scan-a11y-audit/` into
`scan-a11y-audit/results/` for you.

## 3. One-command reproduce

```bash
# system prereqs: git, python3 (venv+pip), rsync, and zstd (to unpack the tarball)
#   Debian/Ubuntu: sudo apt-get install -y git python3 python3-venv python3-pip rsync zstd
#   macOS:         brew install zstd        (git/python3 usually present)

# install tooling + authenticate (the two credentials from step 1)
pip install -U huggingface_hub
hf auth login            # HuggingFace token (data)
gh auth login            # GitHub credential (private paper repo)

# clone the public code repo, then let it do the rest
git clone https://github.com/Alex-jjh/ai-agent-accessibility.git
cd ai-agent-accessibility
./setup-workspace.sh
```

`setup-workspace.sh` will:
1. clone the paper repo as a sibling (via `gh` if available, else `git`),
2. download the dataset from HuggingFace — by default the single
   **`amt-data.tar.zst`** (~1 GB; one file, no per-file 429 rate-limiting),
   falling back to per-file download only if the tarball is absent,
3. unpack and place the corpus into `data/` and the audit into
   `scan-a11y-audit/results/`,
4. verify integrity against `data/SHA256SUMS`,
5. build the analysis venv (`setup.sh`),
6. run `make verify-all` (expect **108/108 PASS**).

> Why a tarball: the corpus is ~77k small JSON files. A per-file `hf download`
> issues a HEAD per file and gets rate-limited (429) by HuggingFace, making it
> very slow. One ~1 GB tarball downloads at full bandwidth in minutes. zstd
> cross-file dedup compresses the 11 GB tree to ~1 GB because many Stage-4b
> screenshots are near-identical.

## 4. Verify it worked

```bash
cd ai-agent-accessibility
source analysis/.venv/bin/activate
make verify-all                                  # 108/108 PASS across 8 stages
python figures/generate_fig8_alignment_scatter.py # regenerate a data figure
cd ../paper && latexmk -pdf main.tex             # rebuild the PDF
```

## 5. What is / isn't reproduced

**Reproduced** (the analysis layer, from frozen data): `make verify-all`
re-derives every paper-critical number → `results/key-numbers.json`; the
`fig{3,7,8,9,10}` generators redraw the data figures; `latexmk` rebuilds the PDF.

**Not reproduced** (intentionally; data is frozen): the data-collection layer —
BrowserGym/Playwright agent runs, AWS Bedrock (CUA), the LiteLLM proxy. Those
produced the raw case JSONs now hosted on HuggingFace. No AWS/Bedrock/LiteLLM
credentials are needed to reproduce results.

**Manual**: the conceptual figures (`fig1` GPT-Image, `fig4`/`fig5`/`figA1`
hand-drawn) regenerate by hand — see `figures/README.md` for per-figure specs.

## 6. Troubleshooting

- **`hf: command not found`** — pip --user installs it off PATH (e.g.
  `~/Library/Python/3.9/bin/hf`). Use the full path or add that dir to PATH;
  `setup-workspace.sh` probes common locations automatically.
- **Paper clone fails / asks for password** — the paper repo is private:
  run `gh auth login` first, or clone with a token:
  `git clone https://<token>@github.com/Alex-jjh/ai-accessibility-paper.git`.
  The analysis layer runs fine without the paper repo.
- **`hf download` 401/403** — the dataset is private; `hf auth login` with a
  token that can read it.
- **`make verify-all` ≠ 108/108** — check `data/` actually populated
  (`find data -name '*.json' | wc -l` should be ~59k) and that the venv used the
  pinned `analysis/requirements.txt`.
- **SHA256 mismatch on README.md only** — harmless; the manifest tracks data
  files, and a stale local README can differ. Data-file mismatches are what matter.

## 7. Environment notes

- Pinned deps: `analysis/requirements.txt` (core, reproduces 108/108) and
  `analysis/requirements-optional.txt` (data-generation only).
- Python pinned to 3.11 via `.python-version` (3.9 also works in practice).
- `data.zip` is not hosted — the unpacked `data/` tree on HuggingFace is the
  source of truth.
