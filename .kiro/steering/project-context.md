# AI Agent Accessibility Platform — Project Steering

## Project Overview

Empirical research platform studying web accessibility vs AI agent task success.
Dual-track: Track A (WebArena controlled experiments), Track B (HAR replay ecological survey).
Six modules: Scanner, Variants, Runner, Classifier, Recorder, Analysis (Python).

## Current Status

Tasks 1–22 complete (all 6 modules implemented, 318 TS + 56 Python tests passing).
Scanner verified on real websites (EC2 + local). LiteLLM → Bedrock verified.
Infrastructure: private subnet + SSM (no public access, burner account compliant).
Next: Task 23 (Pilot Study) — deploy to new burner account and run full pilot.

## Deployment Rules (CRITICAL)

- Burner accounts auto-close if EC2 has public access (0.0.0.0/0 inbound SG)
- ALWAYS use private subnet + SSM Session Manager (no SSH, no public IP)
- Use `terraform apply` from infra/ — it handles all security correctly
- NEVER manually create EC2 via AWS console
- Connect via: `aws ssm start-session --target <instance-id>`
- See docs/deployment.md for full guide including all known issues

## Architecture Rules

- TypeScript (ES2022, strict mode) for modules 1–5; Python for module 6
- Modules communicate via TypeScript interfaces and JSON files, no runtime RPC
- Experiment matrix scheduler (Module 3) orchestrates sequential execution
- Python Analysis Engine consumes CSV exports only
- Always read before you edit if the file exists
- Commit when a feature is completed

## Coding Standards

- All metric values must be 0.0–1.0 inclusive (use `isValidMetricValue`)
- Use `.js` extensions in all TypeScript imports (ESM)
- Prefer `Promise.allSettled()` for parallel operations that should not fail together
- Log errors and continue — never crash the pipeline on a single URL/tool failure
- Every module exports from its `index.ts` barrel file
- Tests use vitest; run with `npx vitest --run`
- Type check with `npx tsc --noEmit`

## Key Design Decisions

- Composite Score is supplementary — primary analysis uses criterion-level feature vectors
- Vision agent is a control condition (expected weak/null a11y gradient)
- Variant levels: low (0.0–0.25), medium-low (0.25–0.50), base (0.40–0.70), high (0.75–1.0)
- Medium-Low variant models real-world pseudo-compliance (ARIA present, handlers missing)
- A11y Tree stability: poll at 2s intervals, SHA-256 hash comparison, 30s timeout
- Config: only `webarena.apps` is required; all other fields have documented defaults
- Failure taxonomy: 11 types across 4 domains (accessibility, model, environmental, task)

## File Structure

```
src/scanner/     — Tier 1 (axe-core + Lighthouse) + Tier 2 (CDP metrics)
src/variants/    — DOM patch engine for 4 accessibility variant levels
src/runner/      — Agent executor, LLM backend, experiment matrix scheduler
src/classifier/  — Auto-classifier (11 failure types) + manual review
src/recorder/    — HAR capture and replay for Track B
src/config/      — YAML/JSON config loader with validation and defaults
src/export/      — Manifest, CSV export, JSON store
analysis/        — Python: CLMM, GEE, Random Forest + SHAP (future)
```

## Spec Reference

Full requirements, design, and tasks at:
#[[file:.kiro/specs/ai-agent-accessibility-platform/requirements.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/design.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/tasks.md]]
