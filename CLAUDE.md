# Project Context for Claude Code

> Auto-loaded at session start. Keep <200 lines. Detail lives in linked files
> and in `~/.claude/projects/.../memory/`.

## What this repo is

Empirical research platform for the CHI/ASSETS 2027 paper *"Same Barrier,
Different Signatures: How Web Accessibility Manipulation Reveals Agent
Adaptation and Structural Criticality"*. The paper repo is a sibling
directory at `../paper/`.

26 AMT operators (13 Low / 3 Midlow / 10 High) × 3 agent architectures
(text-only / SoM / CUA) × 2 model families (Claude Sonnet, Llama 4 Maverick).
N=14,768 total cases (1,040 composite + 4,056 Mode A + 2,184 C.2 + 7,488 Stage 3).
**Status (2026-05-15): all data collection
complete; paper writing + archival in progress.** Burner AWS accounts
expired 2026-05-12; everything is local-analysis from here.

## Authoritative sources (read on demand)

| Question | File |
|---|---|
| 6-phase project history | `docs/project-phases.md` |
| Frozen project narrative (2026-05-04) | `.kiro/steering/project-context.md` |
| AMT framework theory v8 (frozen) | `.kiro/steering/2026-04-27-chi2027-roadmap-v8.md` |
| Stage 3 / 4b execution roadmap (frozen 2026-05-10) | `.kiro/steering/2026-05-04-submission-roadmap.md` |
| Latest handoff | `docs/handoff-2026-05-11.md` |
| All 22 data dirs + paper § mapping | `docs/data-inventory.md` |
| CSV row schema | `docs/data-schema.md` |
| Engineering bug log | `docs/platform-engineering-log.md` |
| Operator spec (26 ops) | `docs/amt-operator-spec.md` |
| Statistical methods catalogue | `docs/statistical-analysis-plan.md`, `docs/statistical-methods-inventory.md` |
| 2026-05-02 root-dir cleanup (executed) | `docs/repo-cleanup-plan.md` |

## Workflow rules

- Paper at `../paper/` (sibling repo). Numbers there must trace back to
  `results/*.csv`; `analysis/verify_all_data_points.py` is the verifier.
- **Don't re-run experiments**; data is locked. See
  `.kiro/steering/2026-05-04-submission-roadmap.md` "what NOT to redo".
- **Don't modify `.kiro/` content** — frozen historical record.
- Burner AWS accounts have expired (2026-05-11 / 2026-05-12). Stage 4b
  has off-platform copies in Google Drive and inside `data.zip`; before
  any deletion under `data/stage4b-ssim-replay/` re-confirm both.
- `data.zip` (~2.9 GB at repo root, gitignored) is the user-verified
  full backup of `data/`. Do not delete without explicit confirmation.
- Use `Makefile` targets:
  - `make verify-all` — V&V all 7 stages (80/80 PASS as of 2026-05-15)
  - `make audit-<phase>` — single stage (e.g. `audit-stage3`)
  - `make export-data`, `make run-stats`, `make all`
  - `make verify-numbers` legacy alias (composite phase only)
- Per-stage docs in `docs/by-stage/{phase1..phase6_stage4b}.md`.
- Audit wrappers indexed at `scripts/audit/README.md`.

## Tech stack quickref

- **TS modules 1–5** (`src/{scanner,variants,runner,classifier,recorder,export}/`):
  vitest 334 tests, tsc strict.
- **Python module 6** (`analysis/`): venv at `.venv/`, deps in
  `requirements.txt`, pytest 67 tests.
- Playwright 1.49 + Chromium 131 + BrowserGym 0.13 + LiteLLM @ :4000
  (text-only/SoM agents) + AWS Bedrock Computer Use (CUA).
- Models: `us.anthropic.claude-sonnet-4-20250514-v1:0`,
  `us.meta.llama4-maverick-17b-instruct-v1:0`.
- Variant operators in `src/variants/patches/operators/{L1..L13,
  ML1..ML3, H1..H8, H5a/b/c}.js`. Composite scripts in
  `src/variants/patches/inject/apply-{low,medium-low,high,
  pure-semantic-low,all-individual,low-individual}.js`.
- Plan-D injection mechanism: `page.evaluate` + `page.on("load")` +
  `context.route("**/*")` (HTTP response interception). Survives
  agent-triggered `goto()` navigations.

## Filesystem after 2026-05-14 archival pass

- `~16.5 GB` total (was ~21 GB). Removed: `.terraform/`, `.venv/`,
  `node_modules/` (both), `<workspace>/.kiro/` mirror.
- All experiment data (`data/`) and `data.zip` retained intact.
- Rollback anchor: git tag `pre-archival-2026-05-14` in both repos.

## Caches (regenerable; gitignored)

- `analysis/.venv/` → `python3.11 -m venv analysis/.venv && pip install -r analysis/requirements.txt`
- `node_modules/` → `npm install`
- `scan-a11y-audit/node_modules/` → `cd scan-a11y-audit && npm install`
- `infra/.terraform/` → `cd infra && terraform init` (only if doing infra work)

## When in doubt

1. Read `docs/handoff-2026-05-11.md` for the most recent state.
2. Read `docs/project-phases.md` for how we got here.
3. Ask the user — don't assume.
