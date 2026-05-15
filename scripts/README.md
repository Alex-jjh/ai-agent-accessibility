# scripts/ — Directory Guide

Organized into 12 subdirectories by function. **For audit/V&V, start at
[`audit/README.md`](audit/README.md) — single discoverability point.**

```
scripts/
├── audit/          ★ V&V wrappers — start here for "how do I audit X"
├── maintenance/    Repo maintenance (archival check, etc.)
├── runners/        Experiment runners (core pipeline)
├── launchers/      nohup wrappers for EC2 (survive SSM disconnect)
├── infra/          AWS deployment & EC2 bootstrap
├── data-pipeline/  S3 upload/download for experiments & audits
├── amt/            AMT operator taxonomy + paper analysis (v8 paper core)
├── stage3/         Stage 3 audit + SSIM replay (Phase 6)
├── smoker/         Smoker analysis + filter (Phase 5)
├── a11y-cua/       A11y-CUA human baseline integration
├── visual-equiv/   13-task Phase 7 prototype (DEPRECATED — superseded by Stage 4b)
├── smoke/          Quick subsystem verification
├── analysis/       Pre-AMT analysis (historical) & task selection
└── ssm/            AWS SSM command documents (JSON)
```

---

## runners/ — Experiment Runners

All use `run-pilot3.ts` as the primary engine (accepts `--config` for any YAML).

| Script | Purpose |
|--------|---------|
| `run-pilot3.ts` | **Primary runner** — loads config YAML, runs Track A matrix, prints per-variant/task stats |
| `run-pilot.ts` | Original Pilot 1 runner (superseded by run-pilot3) |
| `run-regression.ts` | Targeted regression on 9 tasks to verify bug fixes |
| `screen-tasks.ts` | Sweep WebArena task IDs to find 30–70% success rate candidates |

## launchers/ — nohup Wrappers

| Script | Config | Cases |
|--------|--------|-------|
| `launch-pilot3.sh` | configs/archive/config-pilot3.yaml | 120 |
| `launch-pilot3b.sh` | configs/archive/config-pilot3b.yaml | 240 |
| `launch-pilot4.sh` | configs/archive/config-pilot4.yaml | 240 |
| `launch-pilot4-cua.sh` | configs/archive/config-pilot4-cua.yaml | 120 |

## infra/ — Deployment & Bootstrap

| Script | Runs on | Purpose |
|--------|---------|---------|
| `deploy-new-account.sh` | Local | One-command: terraform → SSM wait → print connection commands |
| `bootstrap-platform.sh` | Platform EC2 | Full bootstrap: Python 3.11, Node 20, Playwright, BrowserGym, LiteLLM |
| `bootstrap-visual-equivalence.sh` | Platform EC2 | Minimal bootstrap for URL-replay only (no Node/BrowserGym) |
| `ec2-setup.sh` | EC2 | Legacy setup (superseded by bootstrap-platform.sh) |

## data-pipeline/ — S3 Data Pipeline

| Script | Runs on | Purpose |
|--------|---------|---------|
| `experiment-upload.sh` | EC2 | Package → tar.gz + manifest → `s3://…/experiments/` |
| `experiment-download.sh` | Local | Download + extract. `--list`, `--latest`, specific names |
| `experiment-run-and-upload.sh` | EC2 | Run command then auto-upload on completion |
| `audit-upload.sh` | EC2 | Upload AMT audit runs to `s3://…/audits/` |
| `audit-download.sh` | Local | Download audit runs. `--list`, `--latest` |
| `sync-to-s3.sh` | EC2 | Simple `aws s3 sync` (older, less structured) |

## amt/ — AMT Operator Taxonomy + Analysis

| Script | Lang | Purpose |
|--------|------|---------|
| `build-operators.ts` | TS | Build `apply-all-individual.js` from 26 operator sources |
| `audit-operator.ts` | TS | 12-dim DOM signature audit per operator on a single URL |
| `audit-operator-batch.ts` | TS | Batch: 13 tasks × N reps × 26 operators → `dom_signatures.json` |
| `webarena_login.py` | Python | Shared auth helper — emits cookies as JSON on stdout |
| `amt-audit-fixture.html` | HTML | Static fixture exercising all 26 operators |
| `ground-truth-corrections.json` | JSON | GT corrections for Docker-drift tasks (41, 198, 293) |
| `amt-signature-analysis.py` | Python | D.1/D.2/D.3 — DOM + behavioral + alignment matrices |
| `audit-paper-numbers.py` | Python | Reproducibility audit — verifies every paper number from raw JSON |
| `analyze-mode-a.py` | Python | Mode A analysis (no GT corrections) — historical reference |
| `analyze-mode-a-corrected.py` | Python | Mode A analysis with GT corrections applied |
| `extract-l1-traces.py` | Python | Extract L1 operator traces for deep-dive analysis |

## a11y-cua/ — A11y-CUA Human Baseline Integration

| Script | Lang | Purpose |
|--------|------|---------|
| `download-a11y-cua.sh` | Bash | Download A11y-CUA dataset from HuggingFace to `data/a11y-cua/` |
| `analyze-a11y-cua-metadata.py` | Python | Parse A11y-CUA metadata JSONs → per-task summary stats |
| `analyze-a11y-cua-qwen.py` | Python | Extract Qwen baseline numbers for §5.5 comparison |

## visual-equiv/ — Visual Equivalence Validation

| Script | Lang | Purpose |
|--------|------|---------|
| `run-visual-equivalence.sh` | Bash | Orchestrator: Phase B + C + D → S3 upload |
| `extract_agent_urls.py` | Python | Walk traces → deduplicated URL CSV for replay |
| `replay-url-screenshots.py` | Python | Phase B: 137 URLs × {base, base2, low} |
| `replay-url-patch-ablation.py` | Python | Phase C: 13 patches individually on 15 URLs |
| `replay-url-click-probe.py` | Python | Phase D: click at same coords, base vs patch 11 |
| `patch-ablation-screenshots.py` | Python | Older ablation via BrowserGym bridge (superseded) |
| `smoke-visual-equivalence.py` | Python | Smoke: capture base+low via bridge captureMode |
| `audit-phase-b-admin.py` | Python | Data quality: detect admin login-page contamination |
| `audit-phase-b-all.py` | Python | Data quality: detect login contamination across all apps |

## smoke/ — Smoke Tests

| Script | What it verifies |
|--------|------------------|
| `smoke-variant-injection.ts` | Variant injection into BrowserGym (base vs low observations) |
| `smoke-cua-litellm.ts` | LiteLLM → Bedrock Computer Use tool forwarding |
| `smoke-cua-bedrock-direct.py` | Direct boto3 Bedrock Converse API for CUA |
| `smoke-psl-a11y-tree.py` | Pure-semantic-low ARIA in Chromium a11y tree |
| `smoke-replay-login.py` | Login cookie capture + auth verification for all 4 apps |

## analysis/ — Post-Experiment Analysis

| Script | Lang | Purpose |
|--------|------|---------|
| `analyze-regression.cjs` | CJS | Parse regression traces, per-task step analysis |
| `analyze-screening.cjs` | CJS | Parse ecommerce_admin screening traces |
| `analyze-screening-full.cjs` | CJS | Parse ecommerce + reddit screening traces |
| `verify_data.py` | Python | Sanity check: count case files in data dirs |
| `verify-scanner.ts` | TS | Scanner pipeline: scan 3 real websites with Tier 1+2 |
| `task-expansion-phase2-select.py` | Python | Template analysis for 6→13 task expansion |
| `task-expansion-phase2-verify.py` | Python | Verify candidate tasks (eval type, answers) |

## ssm/ — SSM Command Documents

13 JSON payloads for `aws ssm send-command`. Target Platform EC2 (AL2023) or WebArena EC2 (Ubuntu).

`ssm-bootstrap-platform`, `ssm-bootstrap-visual-equivalence`, `ssm-check-magento-config`,
`ssm-check-webarena`, `ssm-fix-magento-baseurl`, `ssm-fix-playwright-deps`,
`ssm-install-analysis-deps`, `ssm-install-requests`, `ssm-launch-visual-equivalence`,
`ssm-smoke-login`, `ssm-tail-run-log`, `ssm-test-wa-connectivity`, `ssm-verify-platform`
