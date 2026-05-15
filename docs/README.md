# docs/ — Documentation Index

## 🎯 Start here

- **`by-stage/`** ★ — **per-stage doc** (one file per phase): design matrix,
  on-disk paths, audit one-liner, paper § refs, caveats. Start here when
  you need to understand or audit a single phase.
- **`project-phases.md`** — canonical 6-phase narrative connecting all
  phases. Use when you need the cross-phase story.
- **`data-inventory.md`** — every `data/` directory mapped to its phase, N,
  and paper §.

## Active documents (current work)

### AMT Paper (CHI 2027)
- `amt-operator-spec.md` — **Normative spec** for 26 AMT operators
- `amt-audit-artifacts.md` — AMT DOM audit artefact layout
- `audit-architecture.md` — Reproducibility audit 4-layer chain
- `analysis/task-selection-methodology.md` — **Phase 6 pre-registration**: Stage 3 gate + paper drop-in
- `handoff-2026-05-02.md` — Session handoff notes
- `paper-decisions.md` — Paper-level decisions log
- `statistical-analysis-plan.md` — Stats methodology

### Platform & Operations
- `platform-engineering-log.md` — Full bug/fix/regression history (active)
- `deployment.md` — Infrastructure deployment guide
- `new-account-migration-guide.md` — Burner account rotation workflow
- `data-schema.md` — Schema for case JSON + trace outputs
- `design-variant-injection.md` — Plan D injection mechanism design

### Integration & Comparisons
- `a11y-cua-to-webarena-mapping.md` — A11y-CUA human baseline mapping
- `ma11y-operator-mapping.md` — Ma11y [ISSTA 2024] operator audit
- `aegis-taxonomy-comparison.md` — Aegis failure taxonomy comparison
- `browsergym-notes.md` — BrowserGym integration notes

### Repository
- `repo-cleanup-plan.md` — 5-phase cleanup plan

## Subdirectories

- `by-stage/` ★ — per-phase doc (start here for any single-stage question)
- `analysis/` — pre-Stage-3 deep-dive analysis reports (Mode A, C.2, expansion, etc.)
  Mode A files are frozen historical snapshots (banner-marked); active analysis
  lives in `by-stage/`.
- `archive/` — Historical docs (Pilots 1–4, task expansion planning)
- `f-unk-review/` — Manual F_UNK case review (ongoing)

## Finding what you need

| I need to... | Go to |
|--------------|-------|
| Understand a phase end-to-end | `by-stage/<phase>.md` |
| Run the V&V suite | `make verify-all` (writes `results/key-numbers.json`) |
| Audit a single phase | `make audit-<phase>` or `scripts/audit/audit-<phase>.sh` |
| Understand the AMT framework | `amt-operator-spec.md` |
| Verify a paper number | `audit-architecture.md` + `scripts/audit/audit-paper-numbers.sh` |
| See Mode A trace narratives | `analysis/mode-a-*.md` (frozen pre-Stage-3) |
| Deploy to new AWS account | `new-account-migration-guide.md` |
| Understand an operator | `amt-operator-spec.md` §7 or `src/variants/patches/operators/README.md` |
| Trace a historical bug | `platform-engineering-log.md` |
| Find a pilot result | `archive/` |
