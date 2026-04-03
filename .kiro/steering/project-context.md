# AI Agent Accessibility Platform — Project Steering

## Project Overview

Empirical research platform studying web accessibility vs AI agent task success.
Dual-track: Track A (WebArena controlled experiments), Track B (HAR replay ecological survey).
Six modules: Scanner, Variants, Runner, Classifier, Recorder, Analysis (Python).

## Current Status

Tasks 1–22 complete (all 6 modules implemented, 318 TS + 56 Python tests passing).
Scanner verified on real websites (EC2 + local). LiteLLM → Bedrock verified.
Infrastructure: private subnet + SSM (no public access, burner account compliant).
Pilot 1 completed 2026-04-01 — 54 cases, 4 successes (7.4% raw / 66.7% effective).
Root cause analysis identified 5 failure categories; 3 P0 code fixes applied and pushed.
Round 5 regression (2026-04-02): task ID mapping corrected from test.raw.json,
BrowserGym 500ms→3000ms timeout fixed, wikipedia excluded (map dependency),
agent prompt tuned for concise answers, send_msg_to_user sanitized.

Screening completed (2026-04-03):
- ecommerce_admin: 2/12 success (16.7%) — tasks 4, 14. Admin routing fixed (/admin path).
- ecommerce storefront: 3/10 success (30%) — tasks 23, 24, 26 (review search type).
- reddit: 4/9 success (44%) — tasks 27, 29, 30, 67 (forum navigation type).
- Regression v5: 3/9 (33%) — platform stable, zero crashes/timeouts/ValueError.

Shopping login fix completed (2026-04-04):
- Root cause: BrowserGym hooks ALL Playwright navigation after env.reset() +
  Magento regenerates PHPSESSID on login + Docker URL misconfiguration.
- Fix: HTTP login via Python requests (bypasses browser entirely), cookie injection
  via context.add_cookies(), reload via env.step(goto(start_url)).
- Verified: Task 47 agent sees "Sign Out", navigates to My Account, sees order history.
- Tasks 47-50 now viable for Pilot 2.

Open issues:
- Initial observation empty: BrowserGym returns axtree_object (dict) but not axtree_txt.
  Bridge now flattens axtree_object explicitly. Step 1 still empty due to timing;
  subsequent steps have full content.

Next: Re-screen tasks 47-50 with maxSteps=30, then prepare Pilot 2 config.
See docs/platform-engineering-log.md and docs/screening-analysis.md for details.

## WebArena Task ID Mapping (CRITICAL)

Task IDs are interleaved across sites in webarena/test.raw.json — NOT contiguous ranges.
Each task_id maps to exactly one site. Using wrong IDs = silent misrouting.

```
shopping_admin (Magento backend :7780):  182 tasks, first: 0,1,2,3,4,5,6,11,12,13
shopping       (Magento storefront :7770): 192 tasks, first: 21,22,23,24,25,26,47,48
reddit         (Postmill :9999):         114 tasks, first: 27,28,29,30,31,66,67,68
gitlab         (:8023):                  196 tasks, first: 44,45,46,102,103,104,105
wikipedia      (Kiwix :8888):             16 tasks, first: 265,266,267,268,424,425
map            (:3000):                  128 tasks — NOT DEPLOYED, excluded
```

NEVER assume contiguous ranges (e.g. "reddit=100-199" is WRONG).
Always use explicit tasksPerApp in YAML config, or verify against test.raw.json.

## Deployment Rules (CRITICAL)

- Burner accounts auto-close if EC2 has public access (0.0.0.0/0 inbound SG)
- ALWAYS use private subnet + SSM Session Manager (no SSH, no public IP)
- Use `terraform apply` from infra/ — it handles all security correctly
- NEVER manually create EC2 via AWS console
- Connect via: `aws ssm start-session --target <instance-id>`
- Platform EC2 (runs code): `i-0288f77960077b755`
- WebArena EC2 (runs Docker): `i-0c916d784df56d796`
- See docs/deployment.md for full guide including all known issues

## EC2 Reproducibility Rules (CRITICAL)

- NEVER make manual edits on EC2 that aren't tracked in the repo
- All config, scripts, and code changes MUST go through git (edit locally → push → pull on EC2)
- EC2 instances are ephemeral — may be redeployed on different machines at any time
- The only exception is one-time env setup (BrowserGym timeout sed patch, pip installs)
  which MUST be documented in scripts/ec2-setup.sh so they can be re-applied
- Data files (experiment results, screening data) are synced via S3, not stored only on EC2
- `task-site-mapping.json` (repo root) is committed — do NOT regenerate on EC2 unless
  the webarena package version changes

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

## Key Reference Files (repo root)

- `test.raw.json` — WebArena's 812 task definitions (from `webarena` Python package).
  Contains task_id, sites, start_url, intent, eval config, and ground truth for each task.
  Eval types: `string_match` (substring), `url_match`, `program_html` (DOM check),
  `llm_eval` (GPT-4 judge — requires OPENAI_API_KEY via LiteLLM proxy).
- `task-site-mapping.json` — Derived lookup: task_id → site name. Used by screen-tasks
  to filter tasks by app. Regenerate only if webarena package version changes.

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
