# docs/ — Documentation Index

## 🎯 Start here

- **`project-phases.md`** — **canonical 6-phase narrative** of the whole
  project, from March 2026 Pilot 1 through May 2026 Stage 3 task
  expansion. Single source of truth for "how did we get from X to Y"
  questions in the paper, in reviewer Q&A, or in future handoffs.

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

- `analysis/` — All experiment analysis reports (Mode A, C.2, expansion, etc.)
- `archive/` — Historical docs (Pilots 1-4, task expansion planning)
- `f-unk-review/` — Manual F_UNK case review (ongoing)

## Finding what you need

| I need to... | Go to |
|--------------|-------|
| Understand the AMT framework | `amt-operator-spec.md` |
| Verify a paper number | `audit-architecture.md` + `scripts/amt/audit-paper-numbers.py` |
| See Mode A findings | `analysis/mode-a-analysis.md` |
| See composition findings | `analysis/mode-a-C2-composition-analysis.md` |
| See signature alignment | `analysis/mode-a-D3-signature-alignment.md` |
| Deploy to new AWS account | `new-account-migration-guide.md` |
| Understand an operator | `amt-operator-spec.md` §7 or `src/variants/patches/operators/README.md` |
| Trace a historical bug | `platform-engineering-log.md` |
| Find a pilot result | `archive/` |
