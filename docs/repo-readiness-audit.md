# Repo Readiness Audit — 2026-05-02

> **STATUS (2026-05-15)**: Frozen pre-Stage-3 audit. Numbers (e.g. "2,188 C.2
> cases") are the then-believed values; C.2 N has always been 2,184. The
> readiness conclusions still hold; only the case totals require the −4
> correction. For current state see `docs/data-inventory.md` and
> `docs/by-stage/`.

Comprehensive check: is everything we need tracked, and is everything we
shouldn't track properly ignored?

## TL;DR

✅ **Repo is ready.** All experiments, analysis, figures, and paper artifacts are git-tracked. Raw data (data/) correctly gitignored with S3 backup.

| Check | Status |
|-------|--------|
| Working tree clean | ✅ 0 uncommitted changes |
| Audit passes | ✅ 28/28 paper numbers verified |
| All scripts runnable | ✅ from scratch (raw JSON → figures) |
| Secrets scanning | ✅ no credentials in tracked files |
| Large files | ✅ all intentional (GPT figures, HTML snapshots) |
| .gitignore coverage | ✅ comprehensive |

## Tracked Files Summary

Total: **440 tracked files**

| Extension | Count | Purpose |
|-----------|-------|---------|
| `.md` | 97 | Documentation, analysis reports, roadmap |
| `.ts` | 77 | TypeScript source (modules 1-5) |
| `.py` | 73 | Python analysis + scripts |
| `.js` | 32 | Variant operators (26) + build outputs + apply-low.js legacy |
| `.yaml` | 31 | Experiment configs (13 active + 16 archived + 2 infra) |
| `.csv` | 26 | Analysis outputs (not data — those are in `data/`) |
| `.json` | 25 | Configs, test fixtures, GT corrections |
| `.html` | 22 | HTML snapshots for ecological audit |
| `.sh` | 17 | Launch / deploy / pipeline scripts |
| `.png` | 16 | Figures (F1-F9 + archived) |
| `.pdf` | 6 | Vector figure outputs |
| `.tf` | 3 | Terraform infrastructure |
| Other | 15 | package.json, Makefile, etc. |

## What's Git-Tracked (paper-critical)

### Source code (ready to run)
- `src/` — TypeScript modules 1-5 (scanner, variants, runner, classifier, recorder, config)
- `analysis/` — Python statistical package (18 active scripts + models/ + viz/)
- `scripts/` — launchers, runners, AMT tools, A11y-CUA integration
- `figures/` — 6 matplotlib generators + 3 GPT Image prompts + outputs
- `infra/` — Terraform for burner account deployment

### Research artifacts
- `test.raw.json` — WebArena 812 task definitions (reference data)
- `task-site-mapping.json` — task_id → site lookup
- `data/a11y-cua/BLVU/**/metadata_*.json` — A11y-CUA human baseline (tracked — small)
- `scripts/amt/ground-truth-corrections.json` — Docker drift corrections
- `scan-a11y-audit/html-snapshots/` — login-walled site HTML captures (audit evidence)
- `scan-a11y-audit/results/.gitkeep` — directory placeholder

### Documentation
- `docs/amt-operator-spec.md` — normative spec
- `docs/audit-architecture.md` — reproducibility framework
- `docs/analysis/*.md` — experiment analysis reports (all tracked)
- `docs/platform-engineering-log.md` — engineering history
- `.kiro/steering/*.md` — roadmap + project context
- `README.md`, `drafts/README.md`, `figures/README.md`, etc.

### Configs (experiment reproducibility)
- 13 active configs at root (AMT Mode A, C.2, expansion)
- 16 archived configs at `configs/archive/` (Pilots 1-4, pre-AMT smokes)

### Figure outputs (regenerable but tracked for paper submission)
- `figures/F4-F9.{png,pdf}` — data figures (regenerable from CSV)
- `figures/F1-F3_gpt_v1.png` — GPT Image 2 outputs (prompt-based)
- `figures/figure2_main_results.png` etc. — retained composite figures

## What's Correctly Gitignored

### Raw experimental data (S3-backed)
- `data/mode-a-shard-{a,b}/` — 3,042 Claude cases (~650 MB)
- `data/mode-a-llama4-textonly/` — 1,014 Llama 4 cases
- `data/c2-composition-shard-{a,b}/` — 2,188 C.2 cases
- `data/pilot4-full/`, `data/pilot4-cua/` — historical pilots
- `data/expansion-*/` — expansion batch data
- `data/visual-equivalence/` — URL replay captures
- `data/a11y-cua/BLVU/**/` except metadata (dataset too large, ~4 GB)

All recoverable via `bash scripts/data-pipeline/experiment-download.sh`.

### Build artifacts (regenerable)
- `node_modules/` (277 MB)
- `scan-a11y-audit/node_modules/` (55 MB)
- `dist/` — TypeScript compilation output
- `analysis/.venv/` — Python virtualenv
- `__pycache__/`, `.pytest_cache/`

### Secrets and state
- `*.tfstate`, `*.tfstate.backup`, `.terraform/`, `.terraform.lock.hcl`
- `infra/.terraform.*.bak/`, `infra/terraform.tfstate.*.bak`
- `terraform-apply.log`

### AMT audit outputs (regenerable, contain absolute paths)
- `results/amt/` — signature matrices, statistics reports
  - Absolute `file://` URLs in fixture outputs make these machine-specific
  - Regenerable via `python3.11 scripts/amt/amt-signature-analysis.py`

### Local tooling
- `.vscode/`, `.DS_Store`

## Key Observations

### 1. Two `node_modules/` — legitimate, not duplicate

| Location | Size | Purpose |
|----------|------|---------|
| `./node_modules/` | 277 MB | Main platform (BrowserGym, LiteLLM, Playwright, Lighthouse) |
| `./scan-a11y-audit/node_modules/` | 55 MB | Standalone axe-core scanner subproject |

**~33% dependency overlap** (Playwright, @axe-core/playwright, TypeScript, tsx).
**Not a bug** — these are two separate npm projects with their own `package.json`.

**Options if we want to dedupe (cost vs benefit):**

| Option | Savings | Complexity | Recommendation |
|--------|---------|------------|----------------|
| Do nothing | 0 MB | 0 | ✅ **Recommended** — works today, 332 MB is fine |
| npm workspaces | ~100 MB | medium | ⏸ skip — not worth the restructure during paper writing |
| Move scan-a11y-audit to separate repo | N/A | low | ⏸ consider post-CHI (it's already a standalone audit) |

**Decision**: Leave as-is. `node_modules/` is gitignored, so this doesn't affect the repo — only local disk. 332 MB is trivial compared to the 3.89 GB A11y-CUA dataset and 660+ MB experimental data.

### 2. All paper numbers reproducible

```bash
python3.11 scripts/amt/audit-paper-numbers.py  # 28/28 pass
python3.11 analysis/amt_statistics.py          # §5.1/§5.3/§5.4 tests
python3.11 scripts/amt/amt-signature-analysis.py  # D.1/D.2/D.3 matrices
python3.11 figures/generate_F4_behavioral_drop.py  # and F5-F9
```

Every figure and table in the paper can be regenerated from raw JSON
in `data/*/cases/*.json`. Nothing depends on CSV intermediates that
aren't also git-tracked or S3-backed.

### 3. Dependencies well-documented

- `package.json` — TypeScript deps
- `analysis/requirements.txt` — Python deps (statsmodels, pymer4, sklearn, shap, matplotlib, seaborn, scipy)
- `scan-a11y-audit/package.json` — axe-core scanner deps
- `docs/deployment.md` + `docs/new-account-migration-guide.md` — infra + bootstrap

### 4. Clean working tree

```
git status → nothing to commit, working tree clean
```

Last 15 commits all paper-related:
```
a312e28  docs(analysis): document amt_statistics.py
7130486  feat(analysis): add AMT paper statistical tests
7d70846  docs(cleanup): log Phase 6 analysis/ reorganization
d969834  chore(cleanup): Phase 6 — organize analysis/ package
ee8f1f2  docs(cleanup): log actual execution of 5-phase cleanup
c9ed880  Phase 4: archive historical docs
ae1bee7  Phase 2: archive historical configs
d2de134  Phase 3: consolidate scripts/
54faad4  Phase 1+5: delete stale, document drafts/
c912e17  docs: repo cleanup plan
38a7c36  Phase D complete — D.1/D.2/D.3/D.4 + audit
57f9a83  feat(audit): reproducibility verification
d2f137b  feat(figures): F8 + F9
234f72d  feat(figures): GPT Image 2 v1 conceptual figures
3d16ee1  feat(figures): F4-F7 data figures
```

## Risk Inventory

### Low risk — fully manageable
- **Burner account expiry**: Terraform + SSM fixed IPs, `deploy-new-account.sh` automates
- **S3 data loss**: experiment-upload.sh + manifest.txt provides checksums
- **Figure regeneration**: each script fully reproducible, docstrings explain rationale
- **Paper number discrepancies**: audit script catches all divergences

### Medium risk — monitored
- **Docker GT drift**: 3 tasks documented in `ground-truth-corrections.json`, verified
- **Cross-shard Magento state**: task 4 Shard A known stale, documented
- **Llama 4 baseline lower**: expected and accounted for in Breslow-Day tests

### No remaining risks
- Secret leakage: none found in 440 tracked files
- Broken imports: audit passes, figures regenerate
- Stale commits: all recent commits logically connected

## What We're Not Tracking (and Why)

| Item | Size | Why not tracked | Recovery |
|------|------|----------------|----------|
| Raw case JSON | ~650 MB | Too large, reproducible via S3 | `experiment-download.sh` |
| `node_modules/` | 332 MB | Derived from package.json | `npm install` |
| `analysis/.venv/` | ~500 MB | Derived from requirements.txt | `pip install -r` |
| A11y-CUA dataset | 3.89 GB | Third-party dataset | `download-a11y-cua.sh` |
| Terraform state | varies | Account-specific secrets | Terraform workspace |

## Conclusion

The repo is **publication-ready**. Every empirical claim in the CHI 2027
paper can be traced back to git-tracked source code and S3-backed raw data.
No dead code, no orphan files, no secrets, no missing dependencies.

Next step: focus on writing (Phase C narrative, 05-03 → 06-07).
