# Repo Cleanup Plan — 2026-05-02

## Goals

1. **Reduce root directory clutter** — currently 29 config YAMLs + misc files
2. **Distinguish active vs historical artifacts** — archive old pilots, keep Mode A + C.2 prominent
3. **Align with current AMT paper narrative** — anything non-AMT should be demoted
4. **Preserve reproducibility** — don't break any working scripts or data paths

## Current Pain Points (surveyed 2026-05-02)

### Root directory (43 entries)
- **29 config YAMLs** mixing active (mode-a, c2, expansion) and historical (pilot, pilot2, pilot3, pilot3b, pilot4, psl, regression, task188, vision-smoke, reinject-smoke, b1-smoke, cua-smoke, gitlab-smoke, llama4-smoke)
- **2 large tarballs** at root: `data.tar` (630MB), `data.tar.gz` (27MB) — stale exports
- **Log file** at root: `terraform-apply.log` — should be gitignored, not committed
- **Test artifacts**: `.DS_Store`, `test-tmp/`, `.pytest_cache/`
- Build artifact: `dist/` — regenerable

### `scripts/` (mixed structure)
- 9 loose Python files at root mixed with 10 organized subdirectories
- Loose files: `amt-signature-analysis.py`, `audit-paper-numbers.py`, `extract-l1-traces.py`, `analyze-a11y-cua-*.py`, `analyze-mode-a-*.py`, `download-a11y-cua.sh`
- These are **current AMT analysis scripts** — they should live in `scripts/amt/` or a new `scripts/amt-analysis/`

### `docs/` (23 files at root)
- Mix of active (handoff, audit-architecture, amt-operator-spec) and historical (pilot-analysis, pilot2-findings, bugfix-2026-04-02)
- 2 dirs: `analysis/` (active), `f-unk-review/` (partial, active)

### `drafts/` — **EMPTY** (roadmap references `drafts/*.md` files but they don't exist)

### `paper/` — barely populated (`key-numbers.md` + empty `sections/`)

---

## Cleanup Plan (Phased, Reversible)

### Phase 1: Delete/gitignore stale artifacts (SAFE, no code impact)

```
rm .DS_Store
rm data.tar data.tar.gz        # 657MB freed; regenerable via S3 experiment-download.sh
rm terraform-apply.log          # already gitignored, shouldn't exist
rm -rf test-tmp/                # test artifact
rm -rf .pytest_cache/           # already gitignored
rm -rf dist/                    # build artifact, regenerable via tsc
```

**Verification**: `git status` should show 0 files changed (all already gitignored or untracked).

### Phase 2: Archive historical configs (REVERSIBLE, keeps git history)

Move obsolete config YAMLs to `configs/archive/`:

```
configs/
├── active/                           ← current AMT + C.2 experiments
│   ├── config-mode-a-shard-a.yaml
│   ├── config-mode-a-shard-b.yaml
│   ├── config-mode-a-llama4-textonly.yaml
│   ├── config-mode-a-cua-screenshots.yaml
│   ├── config-c2-composition-shard-a.yaml
│   ├── config-c2-composition-shard-b.yaml
│   └── config-b1-smoke.yaml
├── expansion/                        ← task expansion batch (Claude, Llama4, SoM, CUA)
│   ├── config-expansion-claude.yaml
│   ├── config-expansion-llama4.yaml
│   ├── config-expansion-som.yaml
│   ├── config-expansion-cua.yaml
│   ├── config-expansion-som-smoke.yaml
│   ├── config-expansion-cua-smoke.yaml
│   └── config-expansion-phase2-smoke.yaml
└── archive/                          ← historical pilots (retained for reproducibility)
    ├── config-pilot.yaml
    ├── config-pilot2.yaml
    ├── config-pilot3.yaml
    ├── config-pilot3b.yaml
    ├── config-pilot4.yaml
    ├── config-pilot4-cua.yaml
    ├── config-psl-smoke.yaml
    ├── config-psl-expanded-smoke.yaml
    ├── config-regression.yaml
    ├── config-reinject-smoke.yaml
    ├── config-task188-smoke.yaml
    ├── config-vision-smoke.yaml
    ├── config-cua-smoke.yaml
    ├── config-gitlab-smoke.yaml
    ├── config-llama4-smoke.yaml
    └── config.yaml                   ← generic default, keep
```

**Caveat**: Any launch script that references `config-pilot4.yaml` by path needs updating. 
Check: `grep -r "config-pilot" scripts/`

### Phase 3: Consolidate scripts/ (REVERSIBLE)

Move loose AMT analysis scripts into `scripts/amt/`:

```
scripts/
├── amt/                              ← AMT paper pipeline (all ops + audit here)
│   ├── amt-signature-analysis.py     ← was at scripts/ root
│   ├── audit-paper-numbers.py        ← was at scripts/ root
│   ├── analyze-mode-a.py             ← was at scripts/ root
│   ├── analyze-mode-a-corrected.py   ← was at scripts/ root
│   ├── extract-l1-traces.py          ← was at scripts/ root
│   ├── amt-audit-fixture.html        ← existing
│   ├── audit-operator.ts             ← existing
│   ├── audit-operator-batch.ts       ← existing
│   ├── build-operators.ts            ← existing
│   ├── ground-truth-corrections.json ← existing
│   └── webarena_login.py             ← existing
├── a11y-cua/                         ← NEW: A11y-CUA integration (will grow)
│   ├── download-a11y-cua.sh          ← was at scripts/ root
│   ├── analyze-a11y-cua-metadata.py  ← was at scripts/ root
│   └── analyze-a11y-cua-qwen.py      ← was at scripts/ root
├── analysis/                         ← pre-AMT historical analysis (keep)
├── data-pipeline/                    ← S3 upload/download (keep)
├── infra/                            ← terraform helpers (keep)
├── launchers/                        ← experiment launchers (keep)
├── runners/                          ← experiment runners (keep)
├── smoke/                            ← smoke tests (keep)
├── ssm/                              ← AWS SSM session helpers (keep)
└── visual-equiv/                     ← Phase 7 visual equivalence (keep)
```

**Impact check**: Any docs reference `scripts/amt-signature-analysis.py`? 
`grep -r "scripts/amt-signature-analysis.py" docs/`

### Phase 4: Organize docs/ (REVERSIBLE)

Separate active AMT paper docs from historical engineering docs:

```
docs/
├── README.md                         ← NEW: index + navigation guide
├── amt/                              ← NEW: AMT paper docs (active)
│   ├── operator-spec.md              ← was amt-operator-spec.md
│   ├── audit-architecture.md         ← already here
│   ├── audit-artifacts.md            ← was amt-audit-artifacts.md
│   ├── a11y-cua-mapping.md           ← was a11y-cua-to-webarena-mapping.md
│   └── handoff-2026-05-02.md         ← was at docs/ root
├── analysis/                         ← experiment analysis reports (keep)
├── archive/                          ← NEW: historical engineering docs
│   ├── pilot-analysis.md
│   ├── pilot2-findings.md
│   ├── pilot2-trace-deep-dive.md
│   ├── bugfix-2026-04-02-all.md
│   ├── screening-analysis.md
│   ├── task-expansion-phase2-candidates.md
│   ├── task-expansion-plan.md
│   ├── ma11y-operator-mapping.md
│   ├── aegis-taxonomy-comparison.md
│   └── browsergym-notes.md
├── platform/                         ← NEW: platform engineering (active references)
│   ├── deployment.md
│   ├── new-account-migration-guide.md
│   ├── platform-engineering-log.md
│   ├── design-variant-injection.md
│   ├── data-schema.md
│   └── repo-cleanup-plan.md          ← THIS FILE
├── paper/                            ← NEW: paper-specific docs
│   ├── paper-decisions.md
│   └── statistical-analysis-plan.md
└── f-unk-review/                     ← keep (partial, active)
```

**Impact check**: Steering file references many doc paths. Check:
`grep -rn "docs/" .kiro/steering/`

### Phase 5: Clean empty/unused dirs

- `drafts/` — empty. Either populate (roadmap expects `drafts/*.md`) or remove.
  - **Decision**: remove, and change roadmap references to `docs/drafts/` OR `docs/analysis/`
- `paper/` — has only `key-numbers.md`. Keep as-is for future use.

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Delete `data.tar` | Low — regenerable from S3 | S3 backup exists |
| Move configs to `configs/` | Medium — scripts hardcode paths | Use `git mv`, then grep + fix refs |
| Move scripts to subdirs | Medium — other scripts/docs reference | Use `git mv`, then grep + fix refs |
| Move docs to subdirs | Medium — steering/README references | Use `git mv`, then grep + fix refs |

## Execution Strategy

**DO NOT do it all at once.** Recommended order:

1. **Phase 1 first** (deletes only) — zero risk, immediate clutter reduction
2. **Test**: Run `python3.11 scripts/audit-paper-numbers.py` — confirm 28/28 pass
3. **Phase 5 next** (empty dirs) — low risk
4. **Phase 3** (scripts/) — use `git mv`, then grep + fix all references
5. **Test again**: run audit + regenerate F4-F9
6. **Phase 2** (configs/) — more invasive, but launch scripts rarely run from local
7. **Phase 4** (docs/) — last, highest churn but lowest operational risk

**After each phase:**
- Commit with clear message
- Run `python3.11 scripts/audit-paper-numbers.py`
- Run one figure regen (e.g., `python3.11 figures/generate_F4_behavioral_drop.py`)

## What NOT to Touch

- `data/` subdirectories (raw experiment data, gitignored)
- `src/` (active TypeScript codebase)
- `analysis/` (active Python analysis package)
- `infra/` (active Terraform)
- `scan-a11y-audit/` (separate sub-project, self-contained)
- `.kiro/` (steering and settings)
- `node_modules/`, `.git/` (managed automatically)
- `results/amt/` (regenerable but actively used by figure scripts)

## Estimated Impact

Before: 43 root entries, 29 config YAMLs at root, 9 loose scripts
After:  ~15 root entries, 0 config YAMLs at root, 0 loose scripts

Freed disk space: ~660MB (tarballs) + dist cache

## Rollback

Every `git mv` is reversible via `git mv` back. If a phase breaks something,
`git reset --hard HEAD~1` undoes it cleanly (these are local-only changes,
no force-push concern).


---

## Execution Log — 2026-05-02

All 5 phases executed in order. Each phase verified with
`python3.11 scripts/amt/audit-paper-numbers.py` before proceeding.

### Phase 1 (commit 54faad4) — Delete stale artifacts
- Removed `data.tar` (630MB), `data.tar.gz` (27MB) — regenerable from S3
- Removed `terraform-apply.log`, `.DS_Store`, `test-tmp/`, `dist/`, `.pytest_cache/`
- All were untracked or gitignored, no code impact
- Result: ~660MB freed

### Phase 5 (commit 54faad4) — Document drafts/
- `drafts/` kept with new README documenting its aspirational role
  (Phase C/D paper writing artifacts will land here)

### Phase 3 (commit d2de134) — Consolidate scripts/
- Moved 5 scripts from `scripts/` → `scripts/amt/`:
  amt-signature-analysis.py, audit-paper-numbers.py, analyze-mode-a{,-corrected}.py, extract-l1-traces.py
- Moved 3 scripts from `scripts/` → `scripts/a11y-cua/` (new dir):
  download-a11y-cua.sh, analyze-a11y-cua-metadata.py, analyze-a11y-cua-qwen.py
- Path fixes: `ROOT = parent.parent.parent` for moved scripts
- Updated 9 files with new paths (figures, docs, scripts, steering)

### Phase 2 (commit ae1bee7) — Archive configs
- Moved 16 historical config YAMLs to `configs/archive/`
- Root has 13 active configs (down from 29)
- Updated 10 scripts with `configs/archive/` fallback paths
- Added `configs/archive/README.md`

### Phase 4 (commit c9ed880) — Archive docs
- Moved 7 historical docs to `docs/archive/`:
  pilot-analysis, pilot2-findings, pilot2-trace-deep-dive,
  bugfix-2026-04-02-all, screening-analysis, task-expansion-{plan,phase2-candidates}
- Added `docs/README.md` as navigation index with lookup table
- Added `docs/archive/README.md`
- Conservative approach: kept 17 active docs at docs/ root
  (amt-*, audit-architecture, platform-*, deployment, etc.)
  to avoid breaking 20+ source code references

## Final State

| Location | Before | After |
|----------|--------|-------|
| Root entries | 43 | 34 |
| Root config YAMLs | 29 | 13 |
| Loose scripts at `scripts/` root | 9 | 0 |
| `docs/` root files | 23 | 17 |
| Stale artifacts | 660MB tarballs + test dirs | 0 |

All 5 commits verify: `python3.11 scripts/amt/audit-paper-numbers.py`
returns "28 passed, 0 failed" and figure regeneration works.


### Phase 6 (commit d969834) — Organize analysis/ package

**Context**: `analysis/` and `scripts/amt/` are complementary, not duplicate:
- `analysis/` = Python statistical package (CLMM, GEE, GLMM, visualization)
- `scripts/amt/` = AMT operator tooling + paper audit

**Moved** 9 historical pilot/expansion analysis scripts to `analysis/archive/`:
- `pilot3b_190_analysis.py`
- `pilot4_{analysis,cross_pilot_stats,deep_dives,token_analysis}.py`
- `expansion_{smoke_comparison,som_full_deep_dive,cua_full_deep_dive,cross_agent_comparison}.py`

These scripts produced final reports in `docs/analysis/` and are not part of
the active CHI 2027 AMT paper pipeline.

**Active scripts remain in `analysis/`** (18 files):
- Paper-wide stats: `run_statistics.py`, `compute_primary_stats.py`, `glmm_analysis.py`
- Cross-model: `breslow_day.py`, `bootstrap_decomposition.py`
- Sensitivity: `majority_vote_sensitivity.py`, `cua_failure_trace_validation.py`
- Data: `export_combined_data.py`, `verify_all_data_points.py`, `paper_consistency_audit.py`, `generate_results_tables.py`
- Metrics: `semantic_density.py` + test, `ssim_helper.py`
- Visual equiv: `visual_equivalence_analysis.py`, `visual_equivalence_gallery.py`
- Human baseline: `griffith_triangulation.py` + Griffith Excel
- Plus `models/` subdir (primary.py, secondary.py) and `viz/` subdir

Updated `analysis/README.md` with relationship table, active script taxonomy.
Added `analysis/archive/README.md`. Added `.pytest_cache/` to `.gitignore`.

## Updated Final State (after Phase 6)

| Location | Before | After |
|----------|--------|-------|
| Root entries | 43 | 34 |
| Root config YAMLs | 29 | 13 |
| Loose scripts at `scripts/` root | 9 | 0 |
| `docs/` root files | 23 | 17 |
| `analysis/` root files | 27 | 18 |
| Stale artifacts | 660MB tarballs + test dirs | 0 |

**Commit history**:
```
d969834  Phase 6: organize analysis/ (9 pilot/expansion → archive)
ee8f1f2  docs(cleanup): log actual execution
c9ed880  Phase 4: archive historical docs
ae1bee7  Phase 2: archive historical configs
d2de134  Phase 3: consolidate scripts/
54faad4  Phase 1+5: delete stale, document drafts/
```
